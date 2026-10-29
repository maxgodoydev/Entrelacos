"""Catálogo: lê data/catalogo.csv (fonte da verdade), valida e gera site/products.json e site/config.json."""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

GENEROS = ("ela", "ele")
LIMITE_ATE100 = 100.0     # categoria "ate100" é derivada do preço, não digitada
LIMITE_PREMIUM = 200.0    # categoria "premium" também
COLUNAS = ("id", "nome", "linha", "preco", "preco_antigo", "imagem", "largura", "altura",
           "selo", "generos", "tags", "detalhes", "disponivel")
PLACEHOLDER_WHATSAPP = "55XXXXXXXXXXX"
_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_WHATSAPP = re.compile(r"^55\d{10,11}$")


class ErroCatalogo(Exception):
    """Catálogo ou configuração inválidos."""


def _dividir(texto: str, sep: str) -> list[str]:
    return [p.strip() for p in (texto or "").split(sep) if p.strip()]


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        faltando = [c for c in COLUNAS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise ErroCatalogo(f"colunas ausentes no CSV: {', '.join(faltando)}")
        return list(leitor)


def _numero(texto: str):
    try:
        return float(str(texto).strip().replace(",", "."))
    except ValueError:
        return None


def validar(linhas: list[dict], pasta_site: Path | None = None) -> list[str]:
    """Devolve a lista de erros (vazia = catálogo válido). Linha 1 do CSV é o cabeçalho."""
    erros: list[str] = []
    vistos: set[str] = set()
    for i, l in enumerate(linhas, start=2):
        ref = f"linha {i} ({l.get('id') or '?'})"
        pid = (l.get("id") or "").strip()
        if not _ID.match(pid):
            erros.append(f"{ref}: id inválido (use minúsculas, números e hífen)")
        elif pid in vistos:
            erros.append(f"{ref}: id duplicado")
        vistos.add(pid)
        for campo in ("nome", "linha", "selo"):
            if not (l.get(campo) or "").strip():
                erros.append(f"{ref}: '{campo}' vazio")
        preco = _numero(l.get("preco", ""))
        if preco is None or preco <= 0:
            erros.append(f"{ref}: preço inválido")
        antigo_txt = (l.get("preco_antigo") or "").strip()
        if antigo_txt:
            antigo = _numero(antigo_txt)
            if antigo is None:
                erros.append(f"{ref}: preço antigo inválido")
            elif preco is not None and antigo <= preco:
                erros.append(f"{ref}: preço antigo ({antigo:.2f}) precisa ser maior que o atual ({preco:.2f})")
        for campo in ("largura", "altura"):
            if not (l.get(campo) or "").strip().isdigit() or int(l[campo]) <= 0:
                erros.append(f"{ref}: '{campo}' deve ser inteiro positivo")
        generos = _dividir(l.get("generos", ""), ";")
        if not generos or any(g not in GENEROS for g in generos):
            erros.append(f"{ref}: generos deve usar apenas {', '.join(GENEROS)} separados por ';'")
        if not _dividir(l.get("tags", ""), ";"):
            erros.append(f"{ref}: informe ao menos uma tag")
        for par in _dividir(l.get("detalhes", ""), "|"):
            rotulo, _, valor = par.partition("=")
            if not rotulo.strip() or not valor.strip():
                erros.append(f"{ref}: detalhe mal formado '{par}' (use rótulo=valor)")
        if not _dividir(l.get("detalhes", ""), "|"):
            erros.append(f"{ref}: informe ao menos um detalhe")
        if (l.get("disponivel") or "").strip() not in ("sim", "nao"):
            erros.append(f"{ref}: 'disponivel' deve ser sim ou nao")
        imagem = (l.get("imagem") or "").strip()
        if pasta_site is not None and not (pasta_site / imagem).is_file():
            erros.append(f"{ref}: imagem não encontrada em site/{imagem}")
    return erros


def categorias(generos: list[str], preco: float) -> list[str]:
    cats = ["todos", *generos]
    if preco <= LIMITE_ATE100:
        cats.append("ate100")
    if preco >= LIMITE_PREMIUM:
        cats.append("premium")
    return cats


def para_produtos(linhas: list[dict]) -> list[dict]:
    """Converte as linhas (já validadas) no formato lido pelo site. Itens indisponíveis ficam de fora."""
    produtos = []
    for l in linhas:
        if l["disponivel"].strip() != "sim":
            continue
        preco = round(_numero(l["preco"]), 2)
        p = {
            "id": l["id"].strip(), "name": l["nome"].strip(), "line": l["linha"].strip(), "price": preco,
        }
        if l["preco_antigo"].strip():
            p["oldPrice"] = round(_numero(l["preco_antigo"]), 2)
        p.update({
            "image": l["imagem"].strip(), "imageWidth": int(l["largura"]), "imageHeight": int(l["altura"]),
            "badge": l["selo"].strip(),
            "categories": categorias(_dividir(l["generos"], ";"), preco),
            "tags": _dividir(l["tags"], ";"),
            "details": [[r.strip(), v.strip()] for r, _, v in (x.partition("=") for x in _dividir(l["detalhes"], "|"))],
        })
        produtos.append(p)
    return produtos


def montar_config(raiz: Path, env=os.environ) -> dict:
    base = json.loads((raiz / "data" / "config.json").read_text(encoding="utf-8"))
    return {"whatsapp": env.get("WHATSAPP_NUMBER", base["whatsapp"]).strip(),
            "vendedor": env.get("SELLER_NAME", base.get("vendedor", "")).strip()}


def avisos_config(config: dict) -> list[str]:
    zap = config["whatsapp"]
    if zap == PLACEHOLDER_WHATSAPP:
        return ["WhatsApp é o marcador: defina WHATSAPP_NUMBER (ex.: 5511999999999) antes de publicar"]
    if not _WHATSAPP.match(zap):
        return [f"WhatsApp '{zap}' fora do formato 55 + DDD + número, só dígitos"]
    return []


def carregar_validado(raiz: Path) -> list[dict]:
    linhas = ler_csv(raiz / "data" / "catalogo.csv")
    erros = validar(linhas, raiz / "site")
    if erros:
        raise ErroCatalogo("catálogo inválido:\n - " + "\n - ".join(erros))
    return linhas


def construir(raiz: Path, env=os.environ) -> int:
    """Valida o CSV e escreve site/products.json e site/config.json. Devolve o nº de produtos publicados."""
    produtos = para_produtos(carregar_validado(raiz))
    site = raiz / "site"
    (site / "products.json").write_text(json.dumps(produtos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (site / "config.json").write_text(json.dumps(montar_config(raiz, env), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(produtos)

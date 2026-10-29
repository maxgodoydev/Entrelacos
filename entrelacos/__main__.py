"""CLI: python -m entrelacos {validar|build|demo|analisar|tudo}"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import catalogo, metricas, qualidade, relatorio, simulacao

RAIZ = Path(__file__).resolve().parents[1]
EVENTOS, VENDAS = RAIZ / "data" / "eventos_demo.csv", RAIZ / "data" / "vendas_demo.csv"


def _escrever(caminho: Path, colunas, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        w.writeheader(); w.writerows(linhas)


def cmd_validar() -> int:
    linhas = catalogo.ler_csv(RAIZ / "data" / "catalogo.csv")
    erros = catalogo.validar(linhas, RAIZ / "site")
    for a in catalogo.avisos_config(catalogo.montar_config(RAIZ)):
        print("aviso:", a)
    if erros:
        print("Catálogo INVÁLIDO:"); [print(" -", e) for e in erros]
        return 1
    print(f"Catálogo válido: {len(linhas)} produto(s).")
    return 0


def cmd_build() -> int:
    n = catalogo.construir(RAIZ)
    print(f"site/products.json e site/config.json gerados ({n} produto(s)).")
    return 0


def cmd_demo() -> int:
    produtos = catalogo.para_produtos(catalogo.carregar_validado(RAIZ))
    ev, vd = simulacao.gerar(produtos)
    _escrever(EVENTOS, simulacao.COLUNAS_EVENTOS, ev); _escrever(VENDAS, simulacao.COLUNAS_VENDAS, vd)
    print(f"Dados simulados: {len(ev)} eventos, {len(vd)} vendas.")
    return 0


def cmd_analisar() -> int:
    produtos = catalogo.para_produtos(catalogo.carregar_validado(RAIZ))
    ev, vd = qualidade.carregar(EVENTOS, VENDAS)
    problemas = qualidade.verificar(ev, vd, [p["id"] for p in produtos])
    relatorio.gerar(ev, vd, produtos, problemas, RAIZ / "reports")
    f = metricas.funil(ev, vd)
    print(f"Relatório em reports/: {f['sessoes']} sessões, {f['pediram']} pedidos, {f['vendas_atribuidas']} vendas atribuídas.")
    for m in problemas:
        print("qualidade:", m)
    return 1 if problemas else 0


COMANDOS = {"validar": [cmd_validar], "build": [cmd_build], "demo": [cmd_demo], "analisar": [cmd_analisar],
            "tudo": [cmd_validar, cmd_build, cmd_demo, cmd_analisar]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="entrelacos")
    ap.add_argument("comando", choices=COMANDOS)
    for fn in COMANDOS[ap.parse_args(argv).comando]:
        try:
            rc = fn()
        except catalogo.ErroCatalogo as e:
            print(e); return 1
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())

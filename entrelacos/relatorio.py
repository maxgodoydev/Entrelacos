"""Gera reports/relatorio.md e gráficos PNG a partir das métricas."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import metricas  # noqa: E402

ROXO, ROSA = "#7b3fa0", "#c23b87"


def _brl(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%".replace(".", ",")


def tabela_md(df) -> str:
    cab = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    corpo = ["| " + " | ".join(_fmt(v) for v in linha) + " |" for linha in df.itertuples(index=False)]
    return "\n".join([cab, sep, *corpo])


def _fmt(v) -> str:
    return f"{v:.2f}".replace(".", ",") if isinstance(v, float) else str(v)


def _grafico_funil(f: dict, destino: Path):
    etapas = ["Sessões", "Abriram detalhes", "Clicaram em Pedir", "Vendas atribuídas"]
    vals = [f["sessoes"], f["abriram_detalhes"], f["pediram"], f["vendas_atribuidas"]]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.barh(etapas[::-1], vals[::-1], color=[ROSA, ROXO, ROXO, ROXO])
    for i, v in enumerate(vals[::-1]):
        ax.text(v, i, f" {v}", va="center")
    ax.set_title("Funil da vitrine (dados simulados)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(destino, dpi=110); plt.close(fig)


def _grafico_receita(df, destino: Path):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    d = df.sort_values("receita_atribuida")
    ax.barh(d["produto"], d["receita_atribuida"], color=ROXO)
    ax.set_title("Receita atribuída por produto, R$ (dados simulados)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(destino, dpi=110); plt.close(fig)


def _grafico_hora(s, destino: Path):
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(s.index, s.values, color=ROSA)
    ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("hora do dia"); ax.set_title("Sessões por hora (dados simulados)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(destino, dpi=110); plt.close(fig)


def gerar(ev, vd, produtos, problemas: list[str], pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    f = metricas.funil(ev, vd)
    prod, orig = metricas.por_produto(ev, vd, produtos), metricas.por_origem(ev, vd)
    hora, dia = metricas.sessoes_por_hora(ev), metricas.sessoes_por_dia_semana(ev)
    _grafico_funil(f, pasta / "funil.png"); _grafico_receita(prod, pasta / "receita_produto.png"); _grafico_hora(hora, pasta / "sessoes_hora.png")
    funil_tab = [("Sessões", f["sessoes"], ""), ("Abriram detalhes", f["abriram_detalhes"], _pct(f["taxa_detalhes"]) + " das sessões"),
                 ("Clicaram em Pedir", f["pediram"], _pct(f["taxa_pedir"]) + " das sessões"),
                 ("Vendas atribuídas (código casou com clique)", f["vendas_atribuidas"], _pct(f["taxa_venda_por_pedido"]) + " dos cliques"),
                 ("Vendas sem código / sem clique", f["vendas_sem_codigo"], "não atribuíveis")]
    import pandas as pd
    ft = pd.DataFrame(funil_tab, columns=["etapa", "quantidade", "taxa"])
    q = "Nenhum problema encontrado." if not problemas else "\n".join(f"- {m}" for m in problemas)
    md = f"""# Relatório da vitrine EntreLaços

> **DADOS SIMULADOS.** Gerados por `entrelacos/simulacao.py` com semente fixa. Os números abaixo refletem as
> premissas do simulador e **não** são resultado de mercado. O objetivo é demonstrar o pipeline (qualidade,
> atribuição, métricas e relatório), não tirar conclusões sobre vendas reais.

## Funil

{tabela_md(ft)}

- Receita total registrada: **{_brl(f['receita_total'])}**; atribuída a um clique: **{_brl(f['receita_atribuida'])}**
  (cobertura de **{_pct(f['cobertura_receita'])}**). O restante não tem como ser ligado a um clique.

![funil](funil.png)

## Por produto

{tabela_md(prod)}

![receita](receita_produto.png)

## Por origem do tráfego

{tabela_md(orig)}

## Quando as pessoas visitam

Sessões por dia da semana: {", ".join(f"{k} {v}" for k, v in dia.items())}.

![hora](sessoes_hora.png)

## Qualidade dos dados

{q}

## Como ler

- Venda atribuída exige que o vendedor registre o `codigo_pedido` (EL-XXXX) enviado na mensagem do WhatsApp.
- Amostra pequena: poucas dezenas de vendas não sustentam testes estatísticos entre produtos.
"""
    (pasta / "relatorio.md").write_text(md, encoding="utf-8")

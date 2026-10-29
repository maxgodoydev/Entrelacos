"""Checagens de qualidade dos dados de eventos e vendas. Devolve mensagens; lista vazia = dados consistentes."""
from __future__ import annotations

import pandas as pd

TIPOS = ("visita", "filtro", "abrir_detalhes", "clicar_pedir")
COM_PRODUTO = ("abrir_detalhes", "clicar_pedir")
FILTROS = ("ela", "ele", "ate100", "premium")


def carregar(eventos_csv, vendas_csv):
    ev = pd.read_csv(eventos_csv, dtype=str, keep_default_na=False)
    vd = pd.read_csv(vendas_csv, dtype=str, keep_default_na=False)
    ev["ts"] = pd.to_datetime(ev["ts"], errors="coerce")
    vd["data"] = pd.to_datetime(vd["data"], errors="coerce")
    vd["valor"] = pd.to_numeric(vd["valor"], errors="coerce")
    return ev, vd


def verificar(ev: pd.DataFrame, vd: pd.DataFrame, ids_produtos) -> list[str]:
    ids = set(ids_produtos)
    p: list[str] = []

    def achou(n, msg):
        if n:
            p.append(f"{n} {msg}")

    achou(int(ev["evento_id"].duplicated().sum()), "evento(s) com evento_id duplicado")
    achou(int((~ev["tipo"].isin(TIPOS)).sum()), "evento(s) com tipo inválido")
    achou(int(ev["ts"].isna().sum()), "evento(s) com data/hora inválida")
    com_prod = ev[ev["tipo"].isin(COM_PRODUTO)]
    achou(int((~com_prod["produto_id"].isin(ids)).sum()), "evento(s) de produto com produto_id ausente/desconhecido")
    achou(int((ev[ev["tipo"] == "filtro"]["filtro"].isin(FILTROS) == False).sum()), "evento(s) de filtro com filtro inválido")  # noqa: E712
    achou(len(set(ev["sessao_id"]) - set(ev.loc[ev["tipo"] == "visita", "sessao_id"])), "sessão(ões) sem evento 'visita'")
    cliques = ev[ev["tipo"] == "clicar_pedir"]
    achou(int((cliques["codigo_pedido"] == "").sum()), "clique(s) em pedir sem codigo_pedido")
    achou(int(cliques["codigo_pedido"].replace("", pd.NA).dropna().duplicated().sum()), "codigo_pedido duplicado entre cliques")

    achou(int(vd["venda_id"].duplicated().sum()), "venda(s) com venda_id duplicado")
    achou(int((~(vd["valor"] > 0)).sum()), "venda(s) com valor inválido")
    achou(int(vd["data"].isna().sum()), "venda(s) com data inválida")
    achou(int((~vd["produto_id"].isin(ids)).sum()), "venda(s) com produto desconhecido")
    com_codigo = vd[vd["codigo_pedido"] != ""]
    achou(int(com_codigo["codigo_pedido"].duplicated().sum()), "codigo_pedido usado em mais de uma venda")
    achou(int((~com_codigo["codigo_pedido"].isin(set(cliques["codigo_pedido"]))).sum()),
          "venda(s) com codigo_pedido sem clique correspondente (órfã)")
    cruz = com_codigo.merge(cliques, on="codigo_pedido", suffixes=("_v", "_c"))
    achou(int((cruz["produto_id_v"] != cruz["produto_id_c"]).sum()), "venda(s) com produto diferente do clique")
    achou(int((cruz["data"] < cruz["ts"].dt.normalize()).sum()), "venda(s) anterior(es) ao clique")
    return p

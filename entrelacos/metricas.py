"""Métricas de funil, produto, origem e horário. Venda atribuída = venda cujo codigo_pedido casa com um clique."""
from __future__ import annotations

import pandas as pd

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _atribuidas(ev: pd.DataFrame, vd: pd.DataFrame) -> pd.DataFrame:
    cliques = ev[ev["tipo"] == "clicar_pedir"][["codigo_pedido", "sessao_id", "origem"]]
    return vd[vd["codigo_pedido"] != ""].merge(cliques, on="codigo_pedido", how="inner")


def funil(ev: pd.DataFrame, vd: pd.DataFrame) -> dict:
    sessoes = set(ev.loc[ev["tipo"] == "visita", "sessao_id"])
    abriram = set(ev.loc[ev["tipo"] == "abrir_detalhes", "sessao_id"]) & sessoes
    cliques = ev[ev["tipo"] == "clicar_pedir"]
    pediram = set(cliques["sessao_id"]) & sessoes
    atrib = _atribuidas(ev, vd)
    receita_total = float(vd["valor"].sum())
    receita_atrib = float(atrib["valor"].sum())
    return {
        "sessoes": len(sessoes), "abriram_detalhes": len(abriram), "pediram": len(pediram),
        "pedidos": len(cliques), "vendas_total": len(vd), "vendas_atribuidas": len(atrib),
        "vendas_sem_codigo": len(vd) - len(atrib), "receita_total": receita_total,
        "receita_atribuida": receita_atrib,
        "cobertura_receita": receita_atrib / receita_total if receita_total else 0.0,
        "taxa_detalhes": len(abriram) / len(sessoes) if sessoes else 0.0,
        "taxa_pedir": len(pediram) / len(sessoes) if sessoes else 0.0,
        "taxa_venda_por_pedido": len(atrib) / len(cliques) if len(cliques) else 0.0,
    }


def por_produto(ev: pd.DataFrame, vd: pd.DataFrame, produtos: list[dict]) -> pd.DataFrame:
    atrib = _atribuidas(ev, vd)
    linhas = []
    for p in produtos:
        pid = p["id"]
        abriram = set(ev.loc[(ev["tipo"] == "abrir_detalhes") & (ev["produto_id"] == pid), "sessao_id"])
        pediram = set(ev.loc[(ev["tipo"] == "clicar_pedir") & (ev["produto_id"] == pid), "sessao_id"])
        a = atrib[atrib["produto_id"] == pid]
        desc = round((1 - p["price"] / p["oldPrice"]) * 100, 1) if p.get("oldPrice") else 0.0
        linhas.append({"produto": p["name"], "preco": p["price"], "desconto_pct": desc,
                       "sessoes_abriram": len(abriram), "sessoes_pediram": len(pediram),
                       "taxa_pedido_pct": round(len(abriram & pediram) / len(abriram) * 100, 1) if abriram else 0.0,
                       "vendas_atribuidas": len(a), "receita_atribuida": round(float(a["valor"].sum()), 2)})
    return pd.DataFrame(linhas).sort_values(["receita_atribuida", "sessoes_pediram"], ascending=False).reset_index(drop=True)


def por_origem(ev: pd.DataFrame, vd: pd.DataFrame) -> pd.DataFrame:
    visitas = ev[ev["tipo"] == "visita"].groupby("origem")["sessao_id"].nunique().rename("sessoes")
    pedidos = ev[ev["tipo"] == "clicar_pedir"].groupby("origem")["sessao_id"].nunique().rename("sessoes_pediram")
    atrib = _atribuidas(ev, vd).groupby("origem").agg(vendas_atribuidas=("valor", "size"), receita_atribuida=("valor", "sum"))
    df = pd.concat([visitas, pedidos, atrib], axis=1).fillna(0).reset_index().rename(columns={"index": "origem"})
    df["taxa_pedir_pct"] = (df["sessoes_pediram"] / df["sessoes"] * 100).round(1)
    for c in ("sessoes", "sessoes_pediram", "vendas_atribuidas"):
        df[c] = df[c].astype(int)
    df["receita_atribuida"] = df["receita_atribuida"].round(2)
    return df.sort_values("sessoes", ascending=False).reset_index(drop=True)


def sessoes_por_hora(ev: pd.DataFrame) -> pd.Series:
    v = ev[ev["tipo"] == "visita"]
    return v.groupby(v["ts"].dt.hour)["sessao_id"].nunique().reindex(range(24), fill_value=0)


def sessoes_por_dia_semana(ev: pd.DataFrame) -> pd.Series:
    v = ev[ev["tipo"] == "visita"]
    s = v.groupby(v["ts"].dt.dayofweek)["sessao_id"].nunique().reindex(range(7), fill_value=0)
    s.index = DIAS
    return s

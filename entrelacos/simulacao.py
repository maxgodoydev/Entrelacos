"""Simulador de eventos e vendas da vitrine (DADOS FICTÍCIOS, reprodutíveis pela semente).

O site não coleta eventos hoje. Este módulo produz dados sintéticos no esquema que uma coleta real teria
(ver docs/esquema-de-eventos.md) para exercitar o pipeline. Os parâmetros abaixo são premissas do simulador:
os números do relatório refletem essas premissas e NÃO são resultado de mercado.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

COLUNAS_EVENTOS = ("evento_id", "sessao_id", "ts", "tipo", "produto_id", "filtro", "origem", "dispositivo", "codigo_pedido")
COLUNAS_VENDAS = ("venda_id", "data", "produto_id", "valor", "codigo_pedido", "pagamento")

ORIGENS = (("instagram", 0.45), ("whatsapp_status", 0.25), ("indicacao", 0.15), ("direto", 0.15))
FATOR_ORIGEM = {"instagram": 1.0, "whatsapp_status": 1.2, "indicacao": 1.5, "direto": 0.8}
ATRATIVIDADE = {"kit-para-seu-amor": 1.3, "mimo-romantico": 1.0, "carinho-em-presente": 1.1,
                "essencial-classico": 0.8, "essencial-safran": 0.7, "essencial-atrai": 0.9}
PESO_HORA = [1, 1, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 5, 4, 4, 5, 7, 9, 10, 9, 6, 3]
FILTROS = ("ela", "ele", "ate100", "premium")
PAGAMENTOS = (("pix", 0.6), ("cartao", 0.3), ("dinheiro", 0.1))
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
P_FILTRO, P_PEDIR_BASE, P_PEDIR_DIRETO = 0.40, 0.12, 0.03
P_VENDA_APOS_PEDIDO, P_CODIGO_ANOTADO, P_VENDA_SEM_CLIQUE = 0.22, 0.70, 0.06


def _codigo(rng: random.Random, usados: set[str]) -> str:
    while True:
        c = "EL-" + "".join(rng.choice(ALFABETO) for _ in range(4))
        if c not in usados:
            usados.add(c)
            return c


def gerar(produtos: list[dict], seed: int = 42, dias: int = 60, ancora: date = date(2026, 10, 28)):
    """Devolve (eventos, vendas) como listas de dicts, ordenados no tempo."""
    rng = random.Random(seed)
    ids = [p["id"] for p in produtos]
    preco = {p["id"]: p["price"] for p in produtos}
    usados: set[str] = set()
    eventos, vendas_brutas, n_sess = [], [], 0

    for d in range(dias):
        dia = ancora - timedelta(days=dias - 1 - d)
        n_sessoes = rng.randint(10, 20) + (6 if dia.weekday() >= 4 else 0)
        for _ in range(n_sessoes):
            n_sess += 1
            hora = rng.choices(range(24), PESO_HORA)[0]
            t = datetime(dia.year, dia.month, dia.day, hora, rng.randint(0, 59), rng.randint(0, 59))
            origem = rng.choices([o for o, _ in ORIGENS], [w for _, w in ORIGENS])[0]
            disp = "mobile" if rng.random() < 0.82 else "desktop"
            sessao = []  # (ts, tipo, produto, filtro, codigo)
            sessao.append((t, "visita", "", "", ""))
            t += timedelta(seconds=rng.randint(5, 40))
            if rng.random() < P_FILTRO:
                sessao.append((t, "filtro", "", rng.choice(FILTROS), ""))
                t += timedelta(seconds=rng.randint(5, 30))
            candidatos = ids[:]
            abertos = []
            for _k in range(rng.choices([0, 1, 2, 3], [0.35, 0.35, 0.20, 0.10])[0]):
                pid = rng.choices(candidatos, [ATRATIVIDADE.get(c, 1.0) for c in candidatos])[0]
                candidatos.remove(pid)
                abertos.append(pid)
            pediu = None
            for pid in abertos:
                t += timedelta(seconds=rng.randint(8, 60))
                sessao.append((t, "abrir_detalhes", pid, "", ""))
                if rng.random() < min(0.6, P_PEDIR_BASE * ATRATIVIDADE.get(pid, 1.0) * FATOR_ORIGEM[origem]):
                    t += timedelta(seconds=rng.randint(5, 30))
                    pediu = (t, pid, _codigo(rng, usados))
                    sessao.append((t, "clicar_pedir", pid, "", pediu[2]))
                    break
            if pediu is None and rng.random() < P_PEDIR_DIRETO:
                t += timedelta(seconds=rng.randint(5, 30))
                pediu = (t, rng.choice(ids), _codigo(rng, usados))
                sessao.append((t, "clicar_pedir", pediu[1], "", pediu[2]))
            for ts, tipo, pid, filtro, cod in sessao:
                eventos.append({"_sess": n_sess, "ts": ts, "tipo": tipo, "produto_id": pid, "filtro": filtro,
                                "origem": origem, "dispositivo": disp, "codigo_pedido": cod})
            if pediu:
                if rng.random() < P_VENDA_APOS_PEDIDO:
                    quando = min(pediu[0].date() + timedelta(days=rng.randint(0, 2)), ancora)
                    vendas_brutas.append((quando, pediu[1], pediu[2] if rng.random() < P_CODIGO_ANOTADO else ""))

    # vendas sem clique (outro canal / cliente que apagou o código)
    for _ in range(max(1, round(P_VENDA_SEM_CLIQUE * len(vendas_brutas)))):
        vendas_brutas.append((ancora - timedelta(days=rng.randint(0, dias - 1)), rng.choice(ids), ""))

    # ids sequenciais e estáveis, após ordenar no tempo
    eventos.sort(key=lambda e: (e["ts"], e["_sess"], e["tipo"]))
    saida = []
    for n, e in enumerate(eventos, start=1):
        saida.append({"evento_id": f"E{n:06d}", "sessao_id": f"S{e['_sess']:05d}", "ts": e["ts"].isoformat(timespec="seconds"),
                      "tipo": e["tipo"], "produto_id": e["produto_id"], "filtro": e["filtro"], "origem": e["origem"],
                      "dispositivo": e["dispositivo"], "codigo_pedido": e["codigo_pedido"]})
    vendas = []
    for n, (quando, pid, cod) in enumerate(sorted(vendas_brutas, key=lambda v: (v[0], v[1], v[2])), start=1):
        pag = rng.choices([p for p, _ in PAGAMENTOS], [w for _, w in PAGAMENTOS])[0]
        vendas.append({"venda_id": f"V{n:04d}", "data": quando.isoformat(), "produto_id": pid,
                       "valor": f"{preco[pid]:.2f}", "codigo_pedido": cod, "pagamento": pag})
    return saida, vendas

import io
import unittest

import pandas as pd

from entrelacos import metricas, qualidade

EV = """evento_id,sessao_id,ts,tipo,produto_id,filtro,origem,dispositivo,codigo_pedido
E1,S1,2026-10-01T10:00:00,visita,,,instagram,mobile,
E2,S1,2026-10-01T10:01:00,abrir_detalhes,a,,instagram,mobile,
E3,S1,2026-10-01T10:02:00,clicar_pedir,a,,instagram,mobile,EL-AAAA
E4,S2,2026-10-01T11:00:00,visita,,,direto,desktop,
E5,S2,2026-10-01T11:01:00,abrir_detalhes,b,,direto,desktop,
E6,S3,2026-10-02T12:00:00,visita,,,instagram,mobile,
E7,S3,2026-10-02T12:01:00,abrir_detalhes,a,,instagram,mobile,
E8,S3,2026-10-02T12:02:00,clicar_pedir,a,,instagram,mobile,EL-BBBB
E9,S4,2026-10-02T13:00:00,visita,,,direto,mobile,
E10,S4,2026-10-02T13:01:00,filtro,,ele,direto,mobile,
"""
VD = """venda_id,data,produto_id,valor,codigo_pedido,pagamento
V1,2026-10-01,a,100.00,EL-AAAA,pix
V2,2026-10-03,a,100.00,,pix
V3,2026-10-03,b,50.00,,cartao
"""
PRODUTOS = [{"id": "a", "name": "A", "price": 100.0, "oldPrice": 125.0}, {"id": "b", "name": "B", "price": 50.0}]


def carregar(ev=EV, vd=VD):
    e = pd.read_csv(io.StringIO(ev), dtype=str, keep_default_na=False)
    v = pd.read_csv(io.StringIO(vd), dtype=str, keep_default_na=False)
    e["ts"] = pd.to_datetime(e["ts"], errors="coerce")
    v["data"] = pd.to_datetime(v["data"], errors="coerce")
    v["valor"] = pd.to_numeric(v["valor"], errors="coerce")
    return e, v


class MetricasTest(unittest.TestCase):
    def test_funil_com_numeros_conferidos_a_mao(self):
        f = metricas.funil(*carregar())
        self.assertEqual((f["sessoes"], f["abriram_detalhes"], f["pediram"], f["pedidos"]), (4, 3, 2, 2))
        self.assertEqual((f["vendas_total"], f["vendas_atribuidas"], f["vendas_sem_codigo"]), (3, 1, 2))
        self.assertAlmostEqual(f["receita_total"], 250.0)
        self.assertAlmostEqual(f["receita_atribuida"], 100.0)
        self.assertAlmostEqual(f["cobertura_receita"], 0.4)
        self.assertAlmostEqual(f["taxa_pedir"], 0.5)
        self.assertAlmostEqual(f["taxa_venda_por_pedido"], 0.5)

    def test_venda_com_codigo_sem_clique_nao_e_atribuida(self):
        ev, vd = carregar(vd=VD + "V4,2026-10-03,b,50.00,EL-ZZZZ,pix\n")
        f = metricas.funil(ev, vd)
        self.assertEqual((f["vendas_total"], f["vendas_atribuidas"]), (4, 1))
        self.assertAlmostEqual(f["receita_atribuida"], 100.0)

    def test_por_produto(self):
        df = metricas.por_produto(*carregar(), PRODUTOS).set_index("produto")
        self.assertEqual(df.loc["A", "sessoes_abriram"], 2)
        self.assertEqual(df.loc["A", "sessoes_pediram"], 2)
        self.assertEqual(df.loc["A", "taxa_pedido_pct"], 100.0)
        self.assertEqual(df.loc["A", "desconto_pct"], 20.0)
        self.assertEqual(df.loc["A", "receita_atribuida"], 100.0)
        self.assertEqual(df.loc["B", "sessoes_abriram"], 1)
        self.assertEqual(df.loc["B", "taxa_pedido_pct"], 0.0)

    def test_por_origem_e_hora(self):
        o = metricas.por_origem(*carregar()).set_index("origem")
        self.assertEqual(o.loc["instagram", "sessoes"], 2)
        self.assertEqual(o.loc["instagram", "sessoes_pediram"], 2)
        self.assertEqual(o.loc["instagram", "vendas_atribuidas"], 1)
        self.assertEqual(o.loc["direto", "sessoes_pediram"], 0)
        h = metricas.sessoes_por_hora(carregar()[0])
        self.assertEqual((h[10], h[11], h[12], h[13], h[0]), (1, 1, 1, 1, 0))


class QualidadeTest(unittest.TestCase):
    def test_dados_consistentes(self):
        self.assertEqual(qualidade.verificar(*carregar(), ["a", "b"]), [])

    def test_detecta_problemas(self):
        ev = EV.replace("E2,S1,2026-10-01T10:01:00,abrir_detalhes,a", "E2,S1,2026-10-01T10:01:00,abrir_detalhes,zzz")
        ev = ev.replace("E10,S4", "E1,S9")  # evento_id duplicado e sessão sem visita
        vd = VD + "V4,2026-10-01,a,-5,EL-ZZZZ,pix\nV5,2026-09-30,a,100.00,EL-BBBB,pix\n"
        msgs = " | ".join(qualidade.verificar(*carregar(ev, vd), ["a", "b"]))
        for esperado in ("evento_id duplicado", "produto_id ausente/desconhecido", "sem evento 'visita'",
                         "valor inválido", "órfã", "anterior"):
            self.assertIn(esperado, msgs)


if __name__ == "__main__":
    unittest.main()

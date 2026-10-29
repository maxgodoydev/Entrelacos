import re
import unittest
from pathlib import Path

from entrelacos import catalogo, metricas, qualidade, simulacao

RAIZ = Path(__file__).resolve().parents[1]
PRODUTOS = catalogo.para_produtos(catalogo.carregar_validado(RAIZ))


class SimulacaoTest(unittest.TestCase):
    def test_reprodutivel_pela_semente(self):
        self.assertEqual(simulacao.gerar(PRODUTOS, seed=7), simulacao.gerar(PRODUTOS, seed=7))
        self.assertNotEqual(simulacao.gerar(PRODUTOS, seed=7), simulacao.gerar(PRODUTOS, seed=8))

    def test_dados_gerados_passam_na_qualidade(self):
        ev, vd = simulacao.gerar(PRODUTOS, seed=3, dias=20)
        import pandas as pd
        e, v = pd.DataFrame(ev), pd.DataFrame(vd)
        e["ts"] = pd.to_datetime(e["ts"]); v["data"] = pd.to_datetime(v["data"]); v["valor"] = pd.to_numeric(v["valor"])
        self.assertEqual(qualidade.verificar(e, v, [p["id"] for p in PRODUTOS]), [])
        f = metricas.funil(e, v)
        self.assertLessEqual(f["vendas_atribuidas"], f["pedidos"])
        self.assertTrue(0 <= f["cobertura_receita"] <= 1)

    def test_arquivos_versionados_batem_com_a_semente_padrao(self):
        ev, vd = simulacao.gerar(PRODUTOS)
        linhas = (RAIZ / "data" / "eventos_demo.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(linhas) - 1, len(ev))
        self.assertEqual(len((RAIZ / "data" / "vendas_demo.csv").read_text(encoding="utf-8").splitlines()) - 1, len(vd))


class SiteTest(unittest.TestCase):
    def test_sem_handlers_inline_nem_dependencias_externas(self):
        for nome in ("index.html", "script.js"):
            txt = (RAIZ / "site" / nome).read_text(encoding="utf-8")
            self.assertNotIn("onerror=", txt, nome)
            self.assertNotIn("jsdelivr", txt, nome)
            self.assertNotIn("fallbackProducts", txt, nome)

    def test_recursos_referenciados_existem(self):
        html = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")
        css = (RAIZ / "site" / "styles.css").read_text(encoding="utf-8")
        for ref in set(re.findall(r'(?:src|href)="((?!https?:|#|mailto:|tel:)[^"]+)"', html)):
            self.assertTrue((RAIZ / "site" / ref.split("?")[0]).exists(), f"index.html referencia {ref}")
        for ref in set(re.findall(r"url\(['\"]?(assets/[^'\")]+)", css)):
            self.assertTrue((RAIZ / "site" / ref).exists(), f"styles.css referencia {ref}")

    def test_sem_numero_real_no_repositorio(self):
        self.assertEqual(catalogo.montar_config(RAIZ, {})["whatsapp"], catalogo.PLACEHOLDER_WHATSAPP)


if __name__ == "__main__":
    unittest.main()

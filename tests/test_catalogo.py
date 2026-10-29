import json
import tempfile
import unittest
from pathlib import Path

from entrelacos import catalogo

RAIZ = Path(__file__).resolve().parents[1]


def linha(**kw):
    base = {"id": "kit-a", "nome": "Kit A", "linha": "Linha", "preco": "90.00", "preco_antigo": "100.00",
            "imagem": "assets/images/x.webp", "largura": "10", "altura": "20", "selo": "Novo", "generos": "ela",
            "tags": "Doce", "detalhes": "Fixação=6h", "disponivel": "sim"}
    base.update(kw)
    return base


class ValidacaoTest(unittest.TestCase):
    def erros(self, *linhas, site=None):
        return catalogo.validar(list(linhas), site)

    def test_linha_valida(self):
        self.assertEqual(self.erros(linha()), [])

    def test_id_duplicado_e_invalido(self):
        self.assertTrue(any("duplicado" in e for e in self.erros(linha(), linha())))
        self.assertTrue(any("id inválido" in e for e in self.erros(linha(id="Kit A"))))

    def test_precos(self):
        self.assertTrue(any("preço inválido" in e for e in self.erros(linha(preco="0"))))
        self.assertTrue(any("preço inválido" in e for e in self.erros(linha(preco="abc"))))
        self.assertTrue(any("precisa ser maior" in e for e in self.erros(linha(preco="100", preco_antigo="90"))))
        self.assertTrue(any("precisa ser maior" in e for e in self.erros(linha(preco="100", preco_antigo="100"))))
        self.assertEqual(self.erros(linha(preco_antigo="")), [])  # preço antigo é opcional

    def test_campos_estruturados(self):
        self.assertTrue(any("generos" in e for e in self.erros(linha(generos="ela;todos"))))
        self.assertTrue(any("mal formado" in e for e in self.erros(linha(detalhes="semvalor"))))
        self.assertTrue(any("disponivel" in e for e in self.erros(linha(disponivel="talvez"))))
        self.assertTrue(any("largura" in e for e in self.erros(linha(largura="-1"))))

    def test_imagem_inexistente(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any("imagem não encontrada" in e for e in self.erros(linha(), site=Path(d))))


class ConversaoTest(unittest.TestCase):
    def test_categorias_derivadas_do_preco(self):
        self.assertEqual(catalogo.categorias(["ela"], 99.99), ["todos", "ela", "ate100"])
        self.assertEqual(catalogo.categorias(["ela"], 100.0), ["todos", "ela", "ate100"])
        self.assertEqual(catalogo.categorias(["ele"], 150.0), ["todos", "ele"])
        self.assertEqual(catalogo.categorias(["ele", "ela"], 200.0), ["todos", "ele", "ela", "premium"])

    def test_indisponivel_fica_fora_e_sem_preco_antigo(self):
        out = catalogo.para_produtos([linha(), linha(id="kit-b", disponivel="nao"), linha(id="kit-c", preco_antigo="")])
        self.assertEqual([p["id"] for p in out], ["kit-a", "kit-c"])
        self.assertNotIn("oldPrice", out[1])
        self.assertEqual(out[0]["details"], [["Fixação", "6h"]])

    def test_config_via_ambiente(self):
        c = catalogo.montar_config(RAIZ, {"WHATSAPP_NUMBER": " 5511999999999 ", "SELLER_NAME": "Ana"})
        self.assertEqual(c, {"whatsapp": "5511999999999", "vendedor": "Ana"})
        self.assertEqual(catalogo.avisos_config(c), [])
        self.assertTrue(catalogo.avisos_config({"whatsapp": "123", "vendedor": ""}))
        self.assertTrue(catalogo.avisos_config({"whatsapp": catalogo.PLACEHOLDER_WHATSAPP, "vendedor": ""}))


class RepositorioTest(unittest.TestCase):
    def test_catalogo_real_valido(self):
        self.assertEqual(catalogo.validar(catalogo.ler_csv(RAIZ / "data" / "catalogo.csv"), RAIZ / "site"), [])

    def test_products_json_em_sincronia_com_o_csv(self):
        esperado = catalogo.para_produtos(catalogo.carregar_validado(RAIZ))
        publicado = json.loads((RAIZ / "site" / "products.json").read_text(encoding="utf-8"))
        self.assertEqual(publicado, esperado, "rode: python -m entrelacos build")


if __name__ == "__main__":
    unittest.main()

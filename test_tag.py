"""python3 -m unittest test_tag.py"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tag

BASE = """<html><head><script>
(function(w,d,i){w.dataLayer=w.dataLayer||[];var s=d.createElement('script');
s.src='https://www.googletagmanager.com/gtm.js?id='+i;})(window,document,'GTM-XXXX');
document.addEventListener('click',function(e){var el=e.target.closest('button, a');
dataLayer.push({event:'click_botao',button_id:el.id,button_class:'',button_text:''});},true);
</script></head><body>
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXX"></iframe></noscript>
{corpo}
</body></html>"""

BOM = """
<a id="cta-hero-contato" class="btn-conversao px-4">Fale conosco</a>
<a id="nav-sobre" class="btn-nav">Sobre</a>
<button id="ui-menu" class="btn-ui" aria-label="Abrir menu"><svg></svg></button>
"""


CLIENTE = ["--cliente", "Padaria São João", "--ga4", "G-ABC1234567", "--pixel", "123456789012345",
           "--ads-id", "AW-9876543210", "--ads-label", "AbCdEfGh123"]


def executar(pasta, *extra):
    """Roda a corrente inteira com a janela simulada escolhendo <pasta>; devolve (código de saída, stdout).
    Sem ERRO o container vai para <pasta>/c.json."""
    out = io.StringIO()
    code = 0

    def escolher(app):
        app.pasta = str(pasta)

    def preencher(app):  # janela simulada: clica em Gerar com os campos preenchidos pelas flags
        erros = app.conferir_valores({flag: getattr(app.argumentos, flag) or "" for flag in ["cliente", "ga4", "pixel", "ads_id", "ads_label"]})
        if erros:
            sys.exit("; ".join(erros))

    with contextlib.redirect_stdout(out), mock.patch.object(tag.Tagueamento, "selecionar_projeto", escolher), \
            mock.patch.object(tag.Tagueamento, "pedir_valores", preencher):
        try:
            tag.executa_codigo([*CLIENTE, "--saida", str(Path(pasta) / "c.json"), *extra])
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


def rodar(html, arquivo="index.html"):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / arquivo).write_text(html, encoding="utf-8")
        return executar(d)


class Validar(unittest.TestCase):
    def test_site_no_padrao_passa(self):
        code, out = rodar(BASE.replace("{corpo}", BOM))
        self.assertEqual(code, 0, out)

    def test_jsx_com_arrow_e_template(self):
        jsx = """export const X = () => (<>
  <Link href="/a" id={`card-case-${c.slug}`} className="btn-nav block" onClick={() => a > b}>{c.title}</Link>
  <button id="ui-tema" className={cn("btn-ui", x && "p-2")} aria-label="Tema" />
</>);"""
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "index.html").write_text(BASE.replace("{corpo}", ""), encoding="utf-8")
            (Path(d) / "X.tsx").write_text(jsx, encoding="utf-8")
            code, out = executar(d)
        self.assertEqual(code, 0, out)

    def test_cada_erro_plantado_e_apontado(self):
        casos = {
            '<a class="btn-nav">Sem id</a>': "sem id",
            '<a id="nav-x">Sem classe</a>': "sem classe btn-*",
            '<a id="nav-x" class="btn-botao">X</a>': 'classe "btn-botao" não é do padrão',
            '<a id="cta-x" class="btn-cta btn-conversao">X</a>': "btn-conversao precisa ser a primeira",
            '<button id="ui-x" class="btn-ui"><svg></svg></button>': "sem texto visível e sem aria-label",
            '<a id="nav-x" class="btn-nav">A</a><a id="nav-x" class="btn-nav">B</a>': 'id "nav-x" repetido',
            "<script>gtag('config','G-1')</script>": "gtag()",
            "<script>fbq('init','1')</script>": "fbq()",
            '<script src="https://connect.facebook.net/en_US/fbevents.js"></script>': "pixel da Meta",
            '<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>': "gtag.js",
            '<form id="f"><button id="form-f-enviar" class="btn-submit">Enviar</button></form>': "envio_formulario",
        }
        for corpo, esperado in casos.items():
            with self.subTest(corpo=corpo):
                code, out = rodar(BASE.replace("{corpo}", corpo))
                self.assertEqual(code, 1, out)
                self.assertIn(esperado, out)

    def test_so_componente_dentro_e_aviso(self):
        code, out = rodar(BASE.replace("{corpo}", BOM + '<a id="nav-logo" class="btn-nav"><Logo /></a>'))
        self.assertEqual(code, 0, out)
        self.assertIn("só com componente dentro", out)

    def test_sem_btn_conversao_e_aviso(self):
        code, out = rodar(BASE.replace("{corpo}", '<a id="nav-x" class="btn-nav">X</a>'))
        self.assertEqual(code, 0, out)
        self.assertIn("nenhum btn-conversao", out)

    def test_prefixo_fora_do_padrao_e_so_aviso(self):
        code, out = rodar(BASE.replace("{corpo}", '<a id="botao1" class="btn-nav">X</a>'))
        self.assertEqual(code, 0, out)
        self.assertIn("AVISO", out)

    def test_sem_gtm_sem_listener(self):
        code, out = rodar("<html><body></body></html>")
        self.assertEqual(code, 1)
        for esperado in ("gtm.js", "ns.html", "click_botao"):
            self.assertIn(esperado, out)

    def test_listener_sem_button_class(self):
        code, out = rodar(BASE.replace("button_class:'',", "").replace("{corpo}", BOM))
        self.assertEqual(code, 1)
        self.assertIn("não envia button_class", out)


class Gerar(unittest.TestCase):
    def test_gera_container_do_cliente(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "index.html").write_text(BASE.replace("{corpo}", BOM), encoding="utf-8")
            code, out = executar(d)
            self.assertEqual(code, 0, out)
            d = json.loads((Path(d) / "c.json").read_text(encoding="utf-8"))
        cv = d["containerVersion"]
        consts = {v["name"]: v["parameter"][0]["value"] for v in cv["variable"] if v["type"] == "c"}
        self.assertEqual(consts["GA4 ID"], "G-ABC1234567")
        self.assertEqual(consts["Meta Pixel ID"], "123456789012345")
        self.assertEqual(consts["Cliente - Google Ads ID"], "9876543210")
        self.assertEqual(consts["Cliente - Google Ads Label"], "AbCdEfGh123")
        self.assertEqual(cv["container"]["name"], "Padaria São João - Site/LP")
        texto = json.dumps(d, ensure_ascii=False)
        for ph in [campo["placeholder"] for campo in tag.Tagueamento().campos_do_cliente]:
            self.assertNotIn(ph, texto)
        (trig,) = [t for t in cv["trigger"] if t["name"] == "click_botao_conversao"]
        self.assertEqual(trig["filter"][0]["parameter"][1]["value"], "btn-conversao")

    def test_recusa_id_invalido(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "index.html").write_text(BASE.replace("{corpo}", BOM), encoding="utf-8")
            code, out = executar(d, "--ga4", "UA-123")
            self.assertIn("GA4 ID (G-...): formato inválido", str(code))
            self.assertFalse((Path(d) / "c.json").exists())

    def test_seletor_cancelado_encerra(self):
        with mock.patch("tag.ctk"):  # mainloop simulado volta na hora, como se a janela fosse fechada no X
            with self.assertRaises(SystemExit) as e:
                tag.executa_codigo(CLIENTE)
        self.assertIn("nenhuma pasta selecionada", str(e.exception.code))

    def test_janela_do_cliente_fechada_encerra(self):
        app = tag.Tagueamento()
        app.ler_argumentos([])
        with mock.patch("tag.ctk"):  # mainloop simulado volta na hora, como se a janela fosse fechada no X
            with self.assertRaises(SystemExit) as e:
                app.pedir_valores()
        self.assertIn("geração cancelada", str(e.exception.code))

    def test_conferir_valores_lista_cada_campo_invalido(self):
        app = tag.Tagueamento()
        erros = app.conferir_valores({"cliente": " ", "ga4": "UA-1", "pixel": "abc", "ads_id": "AW-12", "ads_label": "x"})
        self.assertEqual(len(erros), 5, erros)
        self.assertIsNone(app.nome_do_cliente)

    def test_com_erro_nao_gera(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "index.html").write_text(BASE.replace("{corpo}", '<a class="btn-nav">Sem id</a>'), encoding="utf-8")
            code, out = executar(d)
            self.assertEqual(code, 1, out)
            self.assertFalse((Path(d) / "c.json").exists())


if __name__ == "__main__":
    unittest.main()

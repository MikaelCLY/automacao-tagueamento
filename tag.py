#!/usr/bin/env python3
"""Tagueamento padrão site/LP.

  python3 tag.py [--cliente ... ]   abre uma janela para selecionar o projeto, valida a aplicação
                                    e, sem erro, abre a janela dos dados do cliente (as flags só
                                    preenchem os campos) e gera container-<cliente>.json

Stdlib + customtkinter (janela). As regras ficam aqui — o script não depende de nenhum .md.
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk


class Tagueamento:
    def __init__(self):
        self.extensoes_com_botoes = {".html", ".htm", ".tsx", ".jsx", ".vue", ".astro", ".php"}
        self.extensoes_de_script = {".ts", ".js", ".mjs"}
        self.extensoes_html = {".html", ".htm"}
        self.pastas_ignoradas = {"node_modules", ".git", ".vercel", ".turbo", "coverage"}
        self.pastas_de_build = {".next", "dist", "build", "out"}

        self.classes_btn_do_padrao = ["btn-conversao", "btn-cta", "btn-nav", "btn-submit", "btn-ui"]
        self.prefixos_de_id = ["cta-", "nav-m-", "nav-", "lp-nav-", "form-", "card-", "footer-", "faq-", "ui-"]

        self.tags_fixas_proibidas = [
            (re.compile(r"\bgtag\s*\("), "gtag() no código — tags vivem no GTM"),
            (re.compile(r"\bfbq\s*\("), "fbq() no código — tags vivem no GTM"),
            (re.compile(r"connect\.facebook\.net"), "script do pixel da Meta no código — tags vivem no GTM"),
            (re.compile(r"googletagmanager\.com/gtag/js"), "gtag.js no código — tags vivem no GTM"),
        ]

        padrao_valor_do_atributo = r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*[`"']([^`"']*)[`"']\s*\}|(\{))"""
        self.regex_abertura_de_botao = re.compile(r"<(button|a|Link)(?=[\s>/])")
        self.regex_atributo_id = re.compile(r"(?<![\w:-])id" + padrao_valor_do_atributo)
        self.regex_atributo_class = re.compile(r"(?<![\w-])(?:class|className|:class)" + padrao_valor_do_atributo)
        self.regex_aria_label = re.compile(r"(?<![\w-])aria-label\s*=")
        self.regex_spread = re.compile(r"\{\s*\.\.\.")
        self.regex_classe_btn = re.compile(r"(?<![\w-])btn-[a-z0-9-]+")

        self.caminho_container_padrao = Path(__file__).with_name("container-padrao.json")
        self.campos_do_cliente = [
            {"flag": "ga4", "variavel_do_gtm": "GA4 ID", "placeholder": "G-XXXXXXXXXX",
             "formato": r"G-[A-Z0-9]{4,}", "rotulo": "GA4 ID (G-...)"},
            {"flag": "pixel", "variavel_do_gtm": "Meta Pixel ID", "placeholder": "000000000000000",
             "formato": r"\d{6,}", "rotulo": "Meta Pixel ID (só dígitos)"},
            {"flag": "ads_id", "variavel_do_gtm": "Cliente - Google Ads ID", "placeholder": "00000000000",
             "formato": r"\d{6,}", "rotulo": "Google Ads ID (só dígitos, sem AW-)"},
            {"flag": "ads_label", "variavel_do_gtm": "Cliente - Google Ads Label", "placeholder": "XXXXXXXXXXXXXXXXXXXX",
             "formato": r"[A-Za-z0-9_-]{6,}", "rotulo": "Google Ads Label (rótulo da conversão)"},
        ]

        self.pasta = None
        self.argumentos = None
        self.arquivos_fonte = []
        self.paginas_html = []
        self.problemas = []
        self.nome_do_cliente = None
        self.valores_do_gtm = {}
        self.container_json = None

    def selecionar_projeto(self):
        janela = ctk.CTk()
        janela.title("Tagueamento — selecionar projeto")
        janela.resizable(False, False)

        ctk.CTkLabel(janela, text="Pasta do projeto").grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 4), sticky="w")
        campo_da_pasta = ctk.CTkEntry(janela, width=360, placeholder_text="/caminho/do/projeto")
        campo_da_pasta.grid(row=1, column=0, padx=(16, 8))
        mensagem_de_erro = ctk.CTkLabel(janela, text="", text_color="#e5484d")
        mensagem_de_erro.grid(row=2, column=0, columnspan=2, padx=16, sticky="w")

        def abrir_seletor_de_pasta():
            pasta_escolhida = filedialog.askdirectory(parent=janela, title="Selecione a pasta do projeto")
            if pasta_escolhida:
                campo_da_pasta.delete(0, "end")
                campo_da_pasta.insert(0, pasta_escolhida)

        def confirmar_pasta():
            texto_digitado = campo_da_pasta.get().strip()
            pasta_digitada = Path(texto_digitado).expanduser()
            if not texto_digitado:
                mensagem_de_erro.configure(text="selecione uma pasta")
            elif not pasta_digitada.is_dir():
                mensagem_de_erro.configure(text=f"pasta não encontrada: {pasta_digitada}")
            else:
                self.pasta = str(pasta_digitada)
                janela.destroy()

        ctk.CTkButton(janela, text="Selecionar", width=110, command=abrir_seletor_de_pasta).grid(row=1, column=1, padx=(0, 16))
        ctk.CTkButton(janela, text="Continuar", command=confirmar_pasta).grid(row=3, column=1, padx=16, pady=(4, 16), sticky="e")
        janela.bind("<Return>", lambda _evento: confirmar_pasta())
        janela.mainloop()
        if not self.pasta:
            sys.exit("nenhuma pasta selecionada")

    def numero_da_linha(self, texto, posicao):
        return texto.count("\n", 0, posicao) + 1

    def encontrar_fim_da_tag(self, texto, inicio):
        profundidade_chaves, aspas_abertas = 0, None
        for posicao in range(inicio, len(texto)):
            caractere = texto[posicao]
            if aspas_abertas:
                aspas_abertas = None if caractere == aspas_abertas else aspas_abertas
            elif caractere in "\"'`":
                aspas_abertas = caractere
            elif caractere == "{":
                profundidade_chaves += 1
            elif caractere == "}":
                profundidade_chaves -= 1
            elif caractere == ">" and profundidade_chaves == 0:
                return posicao
        return -1

    def ler_valor_do_atributo(self, correspondencia):
        grupos_literais = correspondencia.groups()[:3] if correspondencia else ()
        return next((grupo for grupo in grupos_literais if grupo is not None), None)

    def verificar_texto_visivel(self, texto, tag, fim_da_abertura):
        posicao_do_fechamento = texto.find(f"</{tag}>", fim_da_abertura)
        if posicao_do_fechamento < 0:
            return True
        conteudo = re.sub(r"\{\s*/\*.*?\*/\s*\}", "", texto[fim_da_abertura + 1:posicao_do_fechamento], flags=re.S)
        if re.sub(r"<[^>]*>", "", conteudo).strip():
            return True
        return None if re.search(r"<[A-Z]", conteudo) else False

    def listar_botoes_e_links(self, texto):
        for correspondencia in self.regex_abertura_de_botao.finditer(texto):
            fim_da_abertura = self.encontrar_fim_da_tag(texto, correspondencia.end())
            if fim_da_abertura < 0:
                continue
            tag = correspondencia.group(1)
            atributos = texto[correspondencia.end():fim_da_abertura]
            fecha_sozinha = atributos.rstrip().endswith("/")
            tem_texto_visivel = not fecha_sozinha and self.verificar_texto_visivel(texto, tag, fim_da_abertura)
            yield self.numero_da_linha(texto, correspondencia.start()), tag, atributos, tem_texto_visivel

    def checar_id(self, rotulo, atributos, tem_spread):
        busca_id = self.regex_atributo_id.search(atributos)
        if not busca_id:
            return [("AVISO", f"{rotulo} sem id (pode vir do {{...spread}})")] if tem_spread else [("ERRO", f"{rotulo} sem id")]
        valor_do_id = self.ler_valor_do_atributo(busca_id)
        if valor_do_id is None:
            return []
        if not valor_do_id.strip():
            return [("ERRO", f"{rotulo} com id vazio")]
        if valor_do_id.startswith(("${", *self.prefixos_de_id)):
            return []
        return [("AVISO", f'id "{valor_do_id}" fora dos prefixos ({", ".join(self.prefixos_de_id)})')]

    def ler_classes_btn(self, atributos):
        busca_classe = self.regex_atributo_class.search(atributos)
        if not busca_classe:
            return []
        valor_da_classe = self.ler_valor_do_atributo(busca_classe)
        trecho_com_classes = atributos[busca_classe.start():] if valor_da_classe is None else valor_da_classe
        return self.regex_classe_btn.findall(trecho_com_classes)

    def checar_classes(self, rotulo, atributos, tem_spread):
        classes_padrao = " | ".join(self.classes_btn_do_padrao)
        classes_btn_encontradas = self.ler_classes_btn(atributos)
        if not classes_btn_encontradas:
            return [("AVISO" if tem_spread else "ERRO", f"{rotulo} sem classe btn-* ({classes_padrao})")]
        primeira_classe = classes_btn_encontradas[0]
        verificacoes = [
            (primeira_classe not in self.classes_btn_do_padrao,
             f'classe "{primeira_classe}" não é do padrão ({classes_padrao})'),
            ("btn-conversao" in classes_btn_encontradas[1:],
             f'btn-conversao precisa ser a primeira classe btn-* (hoje a primeira é "{primeira_classe}") — senão o GTM não conta a conversão'),
        ]
        return [("ERRO", mensagem) for falhou, mensagem in verificacoes if falhou]

    def checar_texto_visivel(self, rotulo, atributos, tem_texto_visivel):
        if tem_texto_visivel or self.regex_aria_label.search(atributos):
            return []
        problema_por_situacao = {
            None: ("AVISO", f"{rotulo} só com componente dentro e sem aria-label — confira se o componente renderiza texto"),
            False: ("ERRO", f"{rotulo} sem texto visível e sem aria-label"),
        }
        return [problema_por_situacao[tem_texto_visivel]]

    def checar_elemento(self, tag, atributos, tem_texto_visivel):
        rotulo = f"<{tag}>"
        tem_spread = bool(self.regex_spread.search(atributos))
        return (self.checar_id(rotulo, atributos, tem_spread)
                + self.checar_classes(rotulo, atributos, tem_spread)
                + self.checar_texto_visivel(rotulo, atributos, tem_texto_visivel))

    def esta_em_pasta_de_build(self, partes_do_caminho):
        return any(parte in self.pastas_de_build for parte in partes_do_caminho[:-1])

    def arquivo_relevante(self, caminho, raiz):
        partes_do_caminho = caminho.relative_to(raiz).parts
        em_build = self.esta_em_pasta_de_build(partes_do_caminho)
        extensoes_aceitas = self.extensoes_html if em_build else self.extensoes_com_botoes | self.extensoes_de_script
        return (caminho.is_file()
                and not any(parte in self.pastas_ignoradas for parte in partes_do_caminho)
                and caminho.suffix in extensoes_aceitas)

    def gerar_slug(self, texto):
        texto_sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", "-", texto_sem_acentos.lower()).strip("-")

    def conferir_valores(self, dados_digitados):
        nome_do_cliente = dados_digitados["cliente"].strip()
        valores_digitados = {campo["flag"]: dados_digitados[campo["flag"]].strip() for campo in self.campos_do_cliente}
        valores_digitados["ads_id"] = valores_digitados["ads_id"].removeprefix("AW-")

        erros = [] if re.fullmatch(r".*\w.*", nome_do_cliente) else ["Nome do cliente: obrigatório"]
        erros += [f"{campo['rotulo']}: formato inválido" for campo in self.campos_do_cliente
                  if not re.fullmatch(campo["formato"], valores_digitados[campo["flag"]])]
        if erros:
            return erros

        self.nome_do_cliente = nome_do_cliente
        self.valores_do_gtm = {campo["variavel_do_gtm"]: valores_digitados[campo["flag"]] for campo in self.campos_do_cliente}
        return []

    def ler_argumentos(self, argv):
        leitor_de_argumentos = argparse.ArgumentParser(description="Tagueamento padrão site/LP: valida a aplicação e, sem erro, gera o container do cliente")
        leitor_de_argumentos.add_argument("--cliente")
        leitor_de_argumentos.add_argument("--ga4")
        leitor_de_argumentos.add_argument("--pixel")
        leitor_de_argumentos.add_argument("--ads-id", dest="ads_id")
        leitor_de_argumentos.add_argument("--ads-label", dest="ads_label")
        leitor_de_argumentos.add_argument("--saida", help="caminho do JSON (padrão: container-<cliente>.json)")
        self.argumentos = leitor_de_argumentos.parse_args(argv)

    def listar_arquivos(self):
        raiz = Path(self.pasta).resolve()
        if not raiz.is_dir():
            sys.exit(f"pasta não encontrada: {raiz}")
        caminhos = sorted(caminho for caminho in raiz.rglob("*") if self.arquivo_relevante(caminho, raiz))
        arquivos = [(caminho.relative_to(raiz),
                     caminho.suffix,
                     caminho.read_text(encoding="utf-8", errors="replace"),
                     self.esta_em_pasta_de_build(caminho.relative_to(raiz).parts))
                    for caminho in caminhos]
        self.paginas_html = [(caminho_relativo, texto) for caminho_relativo, extensao, texto, em_build in arquivos
                             if em_build or extensao in self.extensoes_html]
        self.arquivos_fonte = [(caminho_relativo, extensao, texto) for caminho_relativo, extensao, texto, em_build in arquivos
                               if not em_build]

    def checar_ids_repetidos(self):
        for caminho_relativo, texto in self.paginas_html:
            linhas_por_id = defaultdict(list)
            for linha, _tag, atributos, _texto_visivel in self.listar_botoes_e_links(texto):
                valor_do_id = self.ler_valor_do_atributo(self.regex_atributo_id.search(atributos))
                if valor_do_id:
                    linhas_por_id[valor_do_id].append(linha)
            self.problemas += [(f"{caminho_relativo}:{linhas[1]}", "ERRO",
                                f'id "{valor_do_id}" repetido na página (linhas {", ".join(map(str, linhas))})')
                               for valor_do_id, linhas in linhas_por_id.items() if len(linhas) > 1]

    def checar_tags_fixas(self):
        for caminho_relativo, _extensao, texto in self.arquivos_fonte:
            for regex_proibida, mensagem in self.tags_fixas_proibidas:
                self.problemas += [(f"{caminho_relativo}:{self.numero_da_linha(texto, ocorrencia.start())}", "ERRO", mensagem)
                                   for ocorrencia in regex_proibida.finditer(texto)]

    def checar_botoes(self):
        arquivos_com_botoes = [(caminho_relativo, texto) for caminho_relativo, extensao, texto in self.arquivos_fonte
                               if extensao in self.extensoes_com_botoes]
        for caminho_relativo, texto in arquivos_com_botoes:
            for linha, tag, atributos, tem_texto_visivel in self.listar_botoes_e_links(texto):
                self.problemas += [(f"{caminho_relativo}:{linha}", nivel, mensagem)
                                   for nivel, mensagem in self.checar_elemento(tag, atributos, tem_texto_visivel)]

    def checar_projeto(self):
        codigo_do_projeto = "\n".join(texto for _caminho, _extensao, texto in self.arquivos_fonte)
        projeto_tem_formulario = any(extensao in self.extensoes_com_botoes and re.search(r"<form[\s>]", texto)
                                     for _caminho, extensao, texto in self.arquivos_fonte)
        verificacoes = [
            ("googletagmanager.com/gtm.js" not in codigo_do_projeto, "ERRO",
             "loader do GTM não encontrado (googletagmanager.com/gtm.js)"),
            ("googletagmanager.com/ns.html" not in codigo_do_projeto, "ERRO",
             "<noscript> do GTM não encontrado (googletagmanager.com/ns.html)"),
            ("click_botao" not in codigo_do_projeto, "ERRO",
             "listener global de clique não encontrado (push de click_botao)"),
            ("click_botao" in codigo_do_projeto and "button_class" not in codigo_do_projeto, "ERRO",
             "listener de clique não envia button_class — a conversão (btn-conversao) depende dele"),
            ("btn-conversao" not in codigo_do_projeto, "AVISO",
             "nenhum btn-conversao no projeto — nenhum clique conta como conversão no GTM"),
            (projeto_tem_formulario and "envio_formulario" not in codigo_do_projeto, "ERRO",
             "há <form> mas nenhum push de envio_formulario"),
        ]
        self.problemas += [(".", nivel, mensagem) for falhou, nivel, mensagem in verificacoes if falhou]

    def imprimir_resultado(self):
        for local, nivel, mensagem in self.problemas:
            print(f"{local}  {nivel}  {mensagem}")
        total_de_erros = sum(nivel == "ERRO" for _local, nivel, _mensagem in self.problemas)
        total_de_avisos = len(self.problemas) - total_de_erros
        print(f"\n{total_de_erros} erro(s), {total_de_avisos} aviso(s)" if self.problemas else "OK — tagueamento no padrão")
        if total_de_erros:
            sys.exit(1)

    def pedir_valores(self):
        janela = ctk.CTk()
        janela.title("Tagueamento — dados do cliente")
        janela.resizable(False, False)

        rotulos_por_flag = [("cliente", "Nome do cliente")] + [(campo["flag"], campo["rotulo"]) for campo in self.campos_do_cliente]
        campos_digitaveis = {}
        for numero_da_linha, (flag, rotulo) in enumerate(rotulos_por_flag):
            espaco_acima = 16 if numero_da_linha == 0 else 4
            ctk.CTkLabel(janela, text=rotulo).grid(row=numero_da_linha, column=0, padx=(16, 8), pady=(espaco_acima, 4), sticky="w")
            campo_digitavel = ctk.CTkEntry(janela, width=300)
            campo_digitavel.insert(0, getattr(self.argumentos, flag) or "")
            campo_digitavel.grid(row=numero_da_linha, column=1, padx=(0, 16), pady=(espaco_acima, 4))
            campos_digitaveis[flag] = campo_digitavel
        mensagem_de_erro = ctk.CTkLabel(janela, text="", text_color="#e5484d", justify="left")
        mensagem_de_erro.grid(row=len(rotulos_por_flag), column=0, columnspan=2, padx=16, sticky="w")

        def confirmar_dados():
            erros = self.conferir_valores({flag: campo.get() for flag, campo in campos_digitaveis.items()})
            if erros:
                mensagem_de_erro.configure(text="\n".join(erros))
            else:
                janela.destroy()

        ctk.CTkButton(janela, text="Gerar", command=confirmar_dados).grid(row=len(rotulos_por_flag) + 1, column=1, padx=16, pady=(4, 16), sticky="e")
        janela.bind("<Return>", lambda _evento: confirmar_dados())
        janela.mainloop()
        if self.nome_do_cliente is None:
            sys.exit("geração cancelada")

    def montar_container(self):
        container = json.loads(self.caminho_container_padrao.read_text(encoding="utf-8"))
        versao_do_container = container["containerVersion"]
        versao_do_container["container"]["name"] = f"{self.nome_do_cliente} - Site/LP"

        variaveis_do_cliente = [variavel for variavel in versao_do_container["variable"]
                                if variavel["name"] in self.valores_do_gtm]
        for variavel in variaveis_do_cliente:
            variavel["parameter"][0]["value"] = self.valores_do_gtm[variavel["name"]]
        nomes_encontrados = {variavel["name"] for variavel in variaveis_do_cliente}
        variaveis_nao_encontradas = [nome for nome in self.valores_do_gtm if nome not in nomes_encontrados]
        if variaveis_nao_encontradas:
            sys.exit(f"variáveis não encontradas no container-padrao.json: {', '.join(variaveis_nao_encontradas)}")

        self.container_json = json.dumps(container, ensure_ascii=False, indent=2)
        placeholders_restantes = [campo["placeholder"] for campo in self.campos_do_cliente
                                  if campo["placeholder"] in self.container_json]
        if placeholders_restantes:
            sys.exit(f"placeholder não substituído: {', '.join(placeholders_restantes)}")

    def salvar_container(self):
        destino = Path(self.argumentos.saida or f"container-{self.gerar_slug(self.nome_do_cliente)}.json")
        destino.write_text(self.container_json + "\n", encoding="utf-8")
        print(f"{destino} gerado — importar em GTM → Admin → Importar contêiner")


def executa_codigo(argv=None):
    app = Tagueamento()
    app.selecionar_projeto()
    app.ler_argumentos(argv)
    app.listar_arquivos()
    app.checar_ids_repetidos()
    app.checar_tags_fixas()
    app.checar_botoes()
    app.checar_projeto()
    app.imprimir_resultado()
    app.pedir_valores()
    app.montar_container()
    app.salvar_container()


if __name__ == "__main__":
    executa_codigo()

# Container GTM padrão — site institucional / LP

| Arquivo | O que é |
|---|---|
| `container-padrao.json` | **container neutro (IDs em placeholder) — base de todo cliente** |
| `tag.py` | valida a aplicação e, sem erro, gera o container do cliente (Python 3.9+, `python3-tk` e `customtkinter`) |
| `docs/tagueamento.md` | regras de botões/links/formulários — **copiar para `docs/` de cada projeto** |
| `test_tag.py` | testes do `tag.py` (`python3 -m unittest test_tag.py`) |
| `GTM-KC29HTCG_workspace7-corrigido.json` | container da M2Z ("M2Z Creative Web"), do qual o padrão foi derivado |
| `GTM-KC29HTCG_workspace7.json` | export original da M2Z (com os problemas da seção 7) — histórico |

Projeto de referência: `M2Z-site-institucional` (Next.js 16) — segue o container próprio da M2Z (conversão por `^cta-.*diagnostico$`), não o padrão.

Este documento explica **como o container funciona**, **o que o site precisa enviar para ele** e **como aplicar o padrão em qualquer projeto novo**.

## Fluxo rápido

```bash
# 0. uma vez por máquina: dependências da janela
sudo apt install python3-tk
python3 -m pip install --user --break-system-packages customtkinter

# 1. no projeto: copiar as regras
cp <pasta-do-padrao>/docs/tagueamento.md docs/

# 2. validar e gerar o container do cliente: abre uma janela para escolher a pasta do projeto;
#    sem ERRO, abre a janela dos dados do cliente (as flags abaixo são opcionais e só preenchem os campos)
python3 <pasta-do-padrao>/tag.py --cliente "Cliente X" \
  --ga4 G-XXXXXXX --pixel 123456789012345 --ads-id 1234567890 --ads-label AbCdEf123
# com ERRO: lista os problemas e sai com código 1, sem gerar — corrigir e rodar de novo
# sem ERRO: → container-cliente-x.json

# 3. GTM → Admin → Importar contêiner → container-cliente-x.json (seção 6.2)
# 4. Visualizar / Tag Assistant (seção 6.3)
```

## Como funciona o `tag.py`

O `tag.py` faz duas coisas em sequência: **valida** se o projeto segue o padrão de tagueamento e, **só se não houver ERRO**, **gera** o container do cliente a partir do `container-padrao.json`.

### Instalação (uma vez por máquina)

```bash
sudo apt install python3-tk                                            # tkinter do sistema
python3 -m pip install --user --break-system-packages customtkinter    # janelas
```

O resto é biblioteca padrão do Python (3.9+).

### Uso

```bash
python3 tag.py [--cliente "Nome"] [--ga4 G-...] [--pixel 123...] [--ads-id 123...] [--ads-label Abc...] [--saida caminho.json]
```

| Flag | O que é | Formato aceito | Vira no GTM | Onde achar |
|---|---|---|---|---|
| `--cliente` | nome do cliente | qualquer texto | nome do container (`Nome - Site/LP`) e do arquivo | — |
| `--ga4` | ID de medição do GA4 | `G-` + letras/números | `GA4 ID` | GA4 → Administrador → Fluxos de dados |
| `--pixel` | ID do Pixel da Meta | só dígitos | `Meta Pixel ID` | Meta → Gerenciador de Eventos |
| `--ads-id` | ID de conversão do Google Ads | só dígitos (`AW-` é retirado) | `Cliente - Google Ads ID` | Google Ads → Metas → Conversões → configuração da tag |
| `--ads-label` | rótulo da conversão | letras, números, `_`, `-` (6+) | `Cliente - Google Ads Label` | mesma tela, depois da `/` em `AW-.../rótulo` |
| `--saida` | onde salvar o JSON | caminho | — | padrão: `container-<cliente>.json` na pasta atual |

Todas as flags são opcionais: elas só **preenchem** os campos da janela do cliente.

### Passo a passo da execução

A função `executa_codigo`, no fim do arquivo, chama as etapas nesta ordem:

| # | Etapa | O que faz | Se der errado |
|---|---|---|---|
| 1 | `selecionar_projeto` | janela para escolher a pasta do projeto (digitar ou **Selecionar**) | pasta vazia/inexistente: aviso na janela; fechar no X: encerra com `nenhuma pasta selecionada` |
| 2 | `ler_argumentos` | lê as flags da linha de comando | — |
| 3 | `listar_arquivos` | lê os arquivos relevantes do projeto (ver abaixo) | — |
| 4 | `checar_ids_repetidos` | `id` repetido na mesma página HTML | ERRO |
| 5 | `checar_tags_fixas` | tag escrita direto no código | ERRO |
| 6 | `checar_botoes` | `id`, classe `btn-*` e texto de cada `<button>`, `<a>`, `<Link>` | ERRO ou AVISO |
| 7 | `checar_projeto` | loader do GTM, listener de clique, formulários | ERRO ou AVISO |
| 8 | `imprimir_resultado` | imprime `arquivo:linha  ERRO\|AVISO  mensagem` e o total | **com ERRO: sai com código 1 e para aqui** |
| 9 | `pedir_valores` | janela com os dados do cliente, já preenchida pelas flags | campo inválido: aviso na janela; fechar no X: encerra com `geração cancelada` |
| 10 | `montar_container` | copia o `container-padrao.json` e troca nome + 4 variáveis | variável ou placeholder sobrando: encerra sem gerar |
| 11 | `salvar_container` | grava o JSON e mostra o caminho | — |

AVISO não bloqueia a geração; ERRO bloqueia.

### Arquivos lidos

- **Código-fonte:** `.html`, `.htm`, `.tsx`, `.jsx`, `.vue`, `.astro`, `.php` (onde há botões) e `.ts`, `.js`, `.mjs` (onde costumam ficar o loader e o listener).
- **Build:** em `.next`, `dist`, `build` e `out`, só o HTML gerado, e só para a checagem de `id` repetido.
- **Ignorados:** `node_modules`, `.git`, `.vercel`, `.turbo`, `coverage`.

### O que é verificado

| Onde | Regra | Nível |
|---|---|---|
| botão/link | sem `id` | ERRO (AVISO se houver `{...spread}`) |
| botão/link | `id` vazio | ERRO |
| botão/link | `id` fora dos prefixos (`cta-`, `nav-`, `nav-m-`, `lp-nav-`, `form-`, `card-`, `footer-`, `faq-`, `ui-`) | AVISO |
| botão/link | sem classe `btn-*` | ERRO (AVISO se houver `{...spread}`) |
| botão/link | primeira `btn-*` fora do padrão (`btn-conversao`, `btn-cta`, `btn-nav`, `btn-submit`, `btn-ui`) | ERRO |
| botão/link | `btn-conversao` presente mas não é a primeira `btn-*` | ERRO |
| botão/link | sem texto visível e sem `aria-label` | ERRO |
| botão/link | só um componente dentro (`<Logo />`) e sem `aria-label` | AVISO |
| página HTML | `id` repetido | ERRO |
| arquivo | `gtag()`, `fbq()`, `connect.facebook.net` ou `gtag/js` no código | ERRO |
| projeto | sem `googletagmanager.com/gtm.js` (loader) | ERRO |
| projeto | sem `googletagmanager.com/ns.html` (`<noscript>`) | ERRO |
| projeto | sem push de `click_botao` | ERRO |
| projeto | `click_botao` sem `button_class` | ERRO |
| projeto | nenhum `btn-conversao` | AVISO |
| projeto | tem `<form>` e nenhum push de `envio_formulario` | ERRO |

**Limite:** a leitura é feita por regex, não por um parser de HTML/JSX. Por isso, `id` e classe que vêm de `{...props}` viram aviso, e um componente dentro do botão vira aviso para conferir à mão.

### Organização do código

Tudo fica na classe `Tagueamento`:

- **`__init__`:** as regras (extensões, pastas, classes `btn-*`, prefixos de `id`, tags proibidas, regex) e o estado compartilhado entre as etapas (`self.pasta`, `self.problemas`, `self.valores_do_gtm`…).
- **Métodos auxiliares:** usados por dentro das etapas, uma vez por arquivo ou por botão, por exemplo `encontrar_fim_da_tag`, `listar_botoes_e_links`, `checar_id`, `checar_classes`, `conferir_valores`.
- **Etapas:** os métodos da tabela acima, cada um guardando o resultado em `self` para a próxima etapa.
- **`executa_codigo`:** a ordem de execução.

Para mudar uma regra:

- **Novo prefixo de `id` ou nova classe `btn-*`:** editar `self.prefixos_de_id` ou `self.classes_btn_do_padrao` no `__init__`.
- **Nova tag proibida:** acrescentar `(regex, mensagem)` em `self.tags_fixas_proibidas`.
- **Nova checagem de projeto:** acrescentar `(condição, nível, mensagem)` na lista `verificacoes` de `checar_projeto`.
- **Novo campo do cliente:** acrescentar um item em `self.campos_do_cliente`. A variável precisa existir no `container-padrao.json` com o placeholder indicado.

### Testes

```bash
python3 -m unittest test_tag.py
```

As janelas são simuladas nos testes, então eles rodam sem tela. Os testes cobrem o site no padrão, cada erro plantado, os avisos, a geração do JSON, a recusa de dados inválidos e o fechamento das janelas sem confirmar.

### Limitações

- **Precisa de tela:** as janelas sempre abrem, então o script não roda em CI, em servidor ou por SSH sem tela.
- **Não há modo "só validar":** com o projeto sem ERRO, a janela do cliente abre; fechá-la encerra sem gerar.

---

## 1. Princípio

> **O site só faz `dataLayer.push`. Toda tag (GA4, Google Ads, Meta) vive no GTM.**

- Nenhum pixel, `gtag()` ou `fbq()` escrito direto no código do site.
- O site publica **3 coisas**: contexto da página/UTMs, cliques (`click_botao`) e conversões de formulário (`envio_formulario`).
- O GTM decide o que vira conversão. Trocar um CTA de conversão, criar um evento novo ou plugar outra plataforma é feito **no GTM, sem deploy**.
- Para isso funcionar, **todo botão e link precisa ser identificável**: `id` único, `class` de tipo (`btn-*`) e texto legível.

```
 Site (código)                         GTM                           Plataformas
 ─────────────                         ───                           ───────────
 loader ──► m2z_attribution  ─┐
        └─► m2z_page_context ─┤
 clique  ──► click_botao ─────┼──► Acionadores (filtram por  ──► GA4, Google Ads,
 form    ──► envio_formulario ┘     evento + button_id)            Meta Pixel / CAPI
```

---

## 2. Contrato do dataLayer

É isso que **todo projeto** precisa enviar. Nomes de evento e de chave são fixos — o container lê exatamente estes nomes.

### 2.1 `click_botao` — todo clique em `<button>` ou `<a>`

| Chave          | Origem no HTML                                             | Exemplo                  | Variável GTM          |
|----------------|------------------------------------------------------------|--------------------------|-----------------------|
| `event`        | fixo                                                       | `click_botao`            | `{{Event}}`           |
| `button_id`    | atributo `id` do elemento                                  | `cta-nav-diagnostico`    | `DLV - button_id`     |
| `button_class` | **primeira** classe que começa com `btn-`                  | `btn-cta`                | `DLV - button_class`  |
| `button_text`  | `aria-label` ou, se não houver, o texto visível (≤ 100 car.) | `Solicite diagnóstico` | `DLV - button_text`   |
| `page_path`    | `location.pathname + location.search`                      | `/lp/captura?utm_source=x` | `DLV - page_path`   |
| `page_location`| `location.href`                                            | `https://…`              | —                     |

### 2.2 `envio_formulario` — submit válido de formulário de lead

| Chave                     | Valor                                      | Variável GTM                    | Usado em                     |
|---------------------------|--------------------------------------------|---------------------------------|------------------------------|
| `event`                   | `envio_formulario`                         | —                               | acionador `envio_formulario` |
| `form_name`               | identificador do formulário (`diagnostico`, `captura`…) | `DLV - form_name`  | GA4                          |
| `event_category`          | `form_submit`                              | `DLV - event_category`          | GA4                          |
| `event_label`             | nome legível do formulário                 | `DLV - event_label`             | GA4                          |
| `element_type`            | `form`                                     | `DLV - element_type`            | GA4                          |
| `area`                    | região da página (`hero`, `final`…)        | `DLV - area`                    | GA4                          |
| `form_type`               | `lead`                                     | —                               | —                            |
| `event_id`                | UUID único por envio                       | `DLV - event_id`                | Order ID do Google Ads + Event ID do `Lead` na Meta |
| `user_data.email`         | e-mail em minúsculas, sem espaços          | `DLV - user_data.email`         | Google Ads (dados do usuário)|
| `user_data.phone_number`  | telefone em **E.164** (`+5541999999999`)   | `DLV - user_data.phone_number`  | Google Ads (dados do usuário)|
| `page_path`, `page_location` | igual ao clique                         | `DLV - page_path`               | GA4                          |

Regras:
- Dispara **no submit válido** (validação do front passou), antes da resposta da API — a conversão não pode depender do backend.
- **Não** travar por visitante (cada envio é uma conversão; o `event_id` deduplica).
- `user_data` só entra se o dado for válido. Se o e-mail for inválido, a chave é omitida, não enviada vazia.

### 2.3 Eventos de contexto (no carregamento, antes do `gtm.js`)

| Evento              | Chaves                                                                 |
|---------------------|------------------------------------------------------------------------|
| `m2z_attribution`   | `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid`, `fbclid`, `keyword` (só as presentes na URL) |
| `m2z_page_context`  | `page_location`, `page_path`, `page_title`, `page_referrer`            |

Hoje nenhuma tag lê esses eventos diretamente — eles deixam UTMs e contexto disponíveis no dataLayer para tags futuras. Para outro cliente, o prefixo `m2z_` pode ser mantido (o container não filtra por ele).

---

## 3. Padrão de identificação de botões (id, class, text)

**Regra: todo `<button>` e todo `<a>` tem `id`, uma classe `btn-*` e texto ou `aria-label`.** Sem exceção — inclusive botão de menu mobile, ícone, link do rodapé, link dentro de tela de sucesso.

### 3.1 `id` — único na página, kebab-case, sem acento

Formato: `<prefixo>-<onde>-<o-que>`

| Prefixo   | Uso                                         | Exemplos (do projeto de referência)                         |
|-----------|---------------------------------------------|-------------------------------------------------------------|
| `cta-`    | chamadas para ação                          | `cta-nav-diagnostico`, `cta-hero-diagnostico`, `cta-final-formulario`, `cta-planos-orcamento` |
| `nav-`    | menu principal (desktop)                    | `nav-logo`, `nav-solucoes`, `nav-sub-solucoes-<slug>`, `nav-busca`, `nav-tema` |
| `nav-m-`  | menu mobile                                 | `nav-m-abrir-menu`, `nav-m-inicio`, `nav-m-sub-solucoes-<slug>` |
| `lp-nav-` | menu das landing pages                      | `lp-nav-logo`, `lp-nav-tema`, `cta-lp-nav`                   |
| `form-`   | botões/links dentro de formulários          | `form-<form_name>-enviar`, `form-<form_name>-whatsapp`, `form-<form_name>-privacidade` |
| `card-`   | cards clicáveis                             | `card-case-<slug>`, `card-solucao-<slug>`, `card-portfolio-<slug>` |
| `footer-` | rodapé                                      | `footer-<label>`, `footer-copiar-email`                      |
| `faq-`    | FAQ                                         | `faq-pergunta-<n>`, `faq-limpar`                             |
| `ui-`     | controles de interface sem navegação        | `ui-voltar-topo`, `ui-pular-conteudo`, `ui-busca-resultado-<n>` |

Regras:
- **Único na página.** O mesmo CTA repetido em lugares diferentes ganha `id` diferente (`cta-hero-diagnostico` ≠ `cta-final-diagnostico`). Se repetir, o GTM não distingue de onde veio a conversão.
- **Estável.** Não usar índice de array ou valor aleatório quando existe um slug. Mudar um `id` quebra o acionador no GTM — avise quem cuida do GTM antes de renomear.
- **Gerados em lista:** derivar do dado (`card-case-${item.slug}`), nunca do índice quando houver identificador.
- **Componentes reutilizados** (ex.: o mesmo formulário em duas seções): receber o `id`/área por prop e compor (`form-diagnostico-hero-enviar`).
- Componente de botão próprio (ex.: `CTAButton`): **`id` como prop obrigatória** no tipo, para o TypeScript barrar o esquecimento.

### 3.2 `class` — tipo do botão (`btn-*`)

Só a **primeira** classe `btn-*` vai para o `button_class`. Ela deve vir **antes** das classes utilitárias (Tailwind etc.).

| Classe          | Quando usar                                      |
|-----------------|--------------------------------------------------|
| `btn-conversao` | clique que **é conversão** — é o que o acionador `click_botao_conversao` filtra |
| `btn-cta`       | chamada para ação que não é conversão            |
| `btn-nav`    | navegação: menu, cards, links de texto, rodapé   |
| `btn-submit` | botão de envio de formulário                     |
| `btn-ui`     | controle de interface (tema, busca, voltar ao topo, abrir menu, carrossel) |

```html
<a id="cta-hero-orcamento" class="btn-conversao rounded-full px-6 …">Peça um orçamento</a>
```

### 3.3 Texto — o que aparece no relatório

- O `button_text` vem do `aria-label` (se existir) ou do texto visível, com espaços normalizados e cortado em 100 caracteres (limite de parâmetro do GA4).
- **Botão só com ícone precisa de `aria-label`** — senão chega vazio. Ex.: `<button id="nav-busca" class="btn-ui" aria-label="Buscar no site">`.
- Se o botão tiver texto dinâmico (contador, saudação), prefira um `aria-label` fixo.

---

## 4. Preparando um projeto (passo a passo)

### Checklist

- [ ] Loader do GTM no `<head>`/início do `<body>`, **antes** da hidratação do app, com os pushes de contexto.
- [ ] `<noscript>` do GTM logo após abrir o `<body>`.
- [ ] Listener global de clique (fase de captura) enviando `click_botao`.
- [ ] `trackFormSubmit` chamado em todo formulário de lead, no submit válido.
- [ ] Todo `<button>`/`<a>` com `id` único + classe `btn-*` + texto/`aria-label`.
- [ ] Nenhum `gtag`, `fbq` ou script de pixel fixo no código.
- [ ] `docs/tagueamento.md` copiado para o projeto e citado no `CLAUDE.md` dele.
- [ ] `python3 tag.py` saindo sem erro (seção 6.3).
- [ ] Lista dos botões `btn-conversao` (id + texto) entregue para quem configura o GTM.

### 4.1 Loader do GTM

Trocar `GTM-XXXXXXX` pelo ID do container do cliente. Mesmo código do `buildGtmLoaderScript` do projeto de referência:

```html
<script>
(function(w,d,i,keys){
  w.dataLayer=w.dataLayer||[];
  try{
    var p=new URLSearchParams(location.search),a={event:'m2z_attribution'};
    keys.forEach(function(k){var v=p.get(k);if(v)a[k]=v;});
    w.dataLayer.push(a);
    w.dataLayer.push({event:'m2z_page_context',page_location:location.href,
      page_path:location.pathname+location.search,page_title:d.title||'',page_referrer:d.referrer||''});
  }catch(e){}
  if(w.__m2zGtmLoaded)return; w.__m2zGtmLoaded=1;
  w.dataLayer.push({'gtm.start':Date.now(),event:'gtm.js'});
  var s=d.createElement('script');s.async=1;
  s.src='https://www.googletagmanager.com/gtm.js?id='+i;d.head.appendChild(s);
})(window,document,'GTM-XXXXXXX',
  ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid','keyword']);
</script>
```

Logo após `<body>`:

```html
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXXX"
  height="0" width="0" style="display:none;visibility:hidden" title="Google Tag Manager"></iframe></noscript>
```

**Next.js (App Router):** `next/script` com `strategy="beforeInteractive"` no `layout.tsx` — ver `src/components/analytics/AnalyticsScripts.tsx` e `src/lib/analytics.ts` do projeto de referência. O guard `__m2zGtmLoaded` impede carregar o `gtm.js` duas vezes.

### 4.2 Rastreamento de cliques (um listener para o site inteiro)

Não colocar `onClick` de tracking em cada botão. Um listener global cobre tudo, inclusive elementos que aparecem depois (menu mobile, modal):

```js
function pushTrackingEvent(event, payload) {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push(Object.assign({
    event: event,
    page_path: location.pathname + location.search,
    page_location: location.href,
  }, payload || {}));
}

document.addEventListener("click", function (e) {
  var el = e.target && e.target.closest && e.target.closest("button, a");
  if (!el) return;
  pushTrackingEvent("click_botao", {
    button_id: el.id,
    button_class: Array.from(el.classList).find(function (c) { return c.indexOf("btn-") === 0; }) || "",
    button_text: (el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 100),
  });
}, true); // captura: um stopPropagation num componente não esconde o clique
```

Em React/Next: registrar em um `useEffect` de um componente client montado no layout (ver `useClickTracking` em `src/components/ui/ClientExtras.tsx`).

### 4.3 Conversão de formulário

```js
function toE164Phone(phone) {
  var d = (phone || "").replace(/\D/g, "");
  if (d.indexOf("55") === 0 && d.length >= 12) return "+" + d;
  if (d.length >= 10) return "+55" + d;
}

function trackFormSubmit(o) {
  var user_data = {};
  var email = (o.email || "").trim().toLowerCase();
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) user_data.email = email;
  var phone = toE164Phone(o.phone);
  if (phone) user_data.phone_number = phone;

  pushTrackingEvent("envio_formulario", Object.assign({
    form_name: o.formName,
    event_category: "form_submit",
    event_label: o.formLabel || o.formName,
    element_type: "form",
    area: o.area || "formulario",
    form_type: "lead",
    event_id: crypto.randomUUID ? crypto.randomUUID() : "lead_" + Date.now(),
  }, Object.keys(user_data).length ? { user_data: user_data } : {}));
}

// no submit, depois da validação do front e ANTES do fetch:
trackFormSubmit({ formName: "diagnostico", formLabel: "Diagnóstico", area: "hero",
                  email: form.email.value, phone: form.whatsapp.value });
```

- `form_name`: curto, snake_case, fixo por formulário (`diagnostico`, `captura`, `site_institucional`…). No projeto de referência a lista mora em `src/lib/schema.ts` (`FORMS`).
- Telefone assume Brasil (+55) quando vem sem DDI.

---

## 5. O que tem no container

### 5.1 Variáveis constantes — **trocar por cliente**

| Variável                        | Placeholder no padrão | O que é                        |
|---------------------------------|----------------------|---------------------------------|
| `GA4 ID`                        | `G-XXXXXXXXXX`       | ID de medição GA4               |
| `Meta Pixel ID`                 | `000000000000000`    | ID do pixel da Meta             |
| `Cliente - Google Ads ID`       | `00000000000`        | ID de conversão (sem `AW-`)     |
| `Cliente - Google Ads Label`    | `XXXXXXXXXXXXXXXXXXXX` | rótulo da conversão de formulário |

Nenhuma tag tem ID escrito direto: trocar estas 4 constantes basta — é o que o `tag.py` faz depois de validar.

### 5.2 Acionadores

| Acionador                              | Dispara quando                                                          |
|----------------------------------------|-------------------------------------------------------------------------|
| `click_botao_conversao`                | evento `click_botao` **e** `DLV - button_class` igual a `btn-conversao` |
| `envio_formulario`                     | evento `envio_formulario`                                               |
| (nativos) All Pages / Initialization   | toda página                                                             |

A conversão é marcada no botão, não no GTM: **todo clique com `btn-conversao` como primeira classe `btn-*` conta**, qualquer que seja o `id`. Botão novo de conversão entra sozinho; o container é o mesmo para todo cliente.

### 5.3 Tags

| Tag                                                  | Tipo                    | Acionador                         | Faz                                                 |
|------------------------------------------------------|-------------------------|-----------------------------------|-----------------------------------------------------|
| `GA4 - Config`                                       | Google Tag              | All Pages                         | carrega o GA4 (`{{GA4 ID}}`) + page_view            |
| `GA4 - Click Botao`                                  | Evento GA4              | `click_botao_conversao`           | envia `clique_conversao`                            |
| `GA4 - Envio Formulario`                             | Evento GA4              | `envio_formulario`                | envia `envio_formulario` + `form_name`, `event_category`, `event_label`, `element_type`, `area`, `page_path` |
| `ADS - Config`                                       | Google Tag              | Initialization                    | carrega `AW-{{Cliente - Google Ads ID}}`            |
| `ADS - Vinculador de Conversão`                      | Conversion Linker       | Initialization                    | grava gclid (URL passthrough ligado)                |
| `ADS - Envio de Formulário`                          | Conversão Google Ads    | `envio_formulario`                | conversão, valor 0 BRL, Order ID = `event_id`       |
| `Google Ads - User-Provided Data - Envio Formulario` | Dados do usuário Ads    | `envio_formulario`                | conversões otimizadas (e-mail + telefone)           |
| `Meta - Pixel Base`                                  | Template Meta Pixel     | All Pages                         | `PageView` — único carregamento do pixel            |
| `Meta - Click Conversao`                             | Template Meta Pixel     | `click_botao_conversao`           | evento custom `Clique Conversão`                    |
| `Meta - Lead`                                        | Template Meta Pixel     | `envio_formulario`                | evento padrão `Lead`, Event ID = `{{DLV - event_id}}` |

### 5.4 Variáveis nativas ativas

`Page URL`, `Page Hostname`, `Page Path`, `Referrer`, `Event`, `Click Element/Classes/ID/Target/URL/Text`, `Form Element/Classes/ID/Target/URL/Text`, `Container ID`.
As variáveis `Click *` nativas **não** são usadas pelas tags — o padrão é ler `button_*` do dataLayer.

---

## 6. Aplicando o container em um projeto novo

### 6.1 No código
Seguir a seção 4 inteira. Entregar ao responsável pelo GTM: ID do container, lista de `form_name`s e lista dos botões `btn-conversao` (id + texto).

### 6.2 No GTM

1. Gerar o JSON do cliente: `python3 tag.py` (Fluxo rápido). **Admin → Importar contêiner** → `container-<cliente>.json`.
   - Container novo e vazio: **Substituir**.
   - Container que já tem coisas: **Mesclar → Renomear itens conflitantes** e revisar duplicatas.
2. Conferir as 4 constantes da seção 5.1 (o `tag.py` já preencheu).
3. **Template Meta Pixel** (`cvt_5RM3Q`) vem junto na importação — conferir em *Modelos* que ele está lá.
4. **CTA de conversão:** nada a fazer — o acionador `click_botao_conversao` lê a classe `btn-conversao`.
5. Eventos voltados ao cliente: `clique_conversao` (GA4) e `Clique Conversão` (Meta). Renomear só se o cliente pedir — e marcar `clique_conversao` como evento-chave no GA4.
6. Criar a conversão de formulário no Google Ads do cliente e colar o rótulo em `Cliente - Google Ads Label`.

### 6.3 Validação

1. **Visualizar (Tag Assistant)** no GTM, abrir o site:
   - na carga: `m2z_attribution`, `m2z_page_context`, `gtm.js` → `GA4 - Config`, `ADS - Config`, `Meta - Pixel Base` disparam.
   - clicar no CTA de conversão → `click_botao` com `button_id` correto → `GA4 - Click Botao` e `Meta - Click Conversao` disparam. Clique em botão sem `btn-conversao` → só o `click_botao`, nenhuma tag.
   - enviar um formulário → `envio_formulario` com `event_id` e `user_data` → disparam `GA4 - Envio Formulario`, `ADS - Envio de Formulário`, `Google Ads - User-Provided Data - …` e `Meta - Lead`.
   - em nenhum momento deve aparecer tag disparando em `m2z_attribution` / `m2z_page_context`, nem `PageView` da Meta mais de uma vez.
2. **Console do navegador:** `dataLayer.filter(e => e.event === "click_botao")` para conferir id/class/text de cada clique.
3. **Validador** — depois do build, escolhendo a raiz do projeto na janela (para checar `id` repetido no HTML gerado):
   ```
   npm run build && python3 <pasta-do-padrao>/tag.py
   ```
   Sai com código 1 se houver erro. Sem erro, abre a janela dos dados do cliente para gerar o container.
4. GA4 → **DebugView** e Meta → **Testar eventos** para confirmar a chegada.

---

## 7. Correções aplicadas no container M2Z (workspace7 → workspace7-corrigido)

Problemas encontrados no export original e o que foi feito:

| # | Problema no original | Correção |
|---|----------------------|----------|
| 1 | `PageView` da Meta disparava 3× por página (tag HTML, `Meta - Pixel Base` e `FB_CONVERSIONS_API-…-Pixel_Template`) | Removidas a tag HTML `Meta Pixel ID 1113534230087761` e a integração `FB_CONVERSIONS_API-*`; fica só `Meta - Pixel Base` |
| 2 | page_view do GA4 em dobro (`GA4 - Config` + `FB_CONVERSIONS_API-…-GA4_Config`) | Integração removida; fica só `GA4 - Config` |
| 3 | Acionador `FB_CONVERSIONS_API-…-Custom_Event` mandava `m2z_attribution`, `m2z_page_context` e todo `click_botao` para GA4 e Meta | Integração removida |
| 4 | Clique no CTA chegava 2× na Meta | Integração removida |
| 5 | Formulário não gerava `Lead` na Meta | Nova tag `Meta - Lead` em `envio_formulario` |
| 6 | `event_id` do site não era usado na Meta | `Meta - Lead` usa `{{DLV - event_id}}` como Event ID (mesmo ID do Order ID do Google Ads) |
| 7 | Só `cta-nav-diagnostico` contava | Acionador passou para regex `^cta-.*diagnostico$` |
| 8 | Pixel e GA4 escritos direto em tags | Não sobrou nenhum; só as constantes da seção 5.1 |
| — | Comentário em `src/lib/analytics.ts` do site citava `GTM-TNT5CJJP` | Corrigido para `GTM-KC29HTCG` |

Sobre a integração `FB_CONVERSIONS_API-*` (3 tags, 2 acionadores, 11 variáveis): o `transport_url` estava vazio, ou seja, nenhum servidor de CAPI recebia os dados — as tags só duplicavam o que as tags principais já enviam. **Se um dia houver GTM server-side / CAPI Gateway, a CAPI deve ser configurada de novo, reaproveitando `{{DLV - event_id}}` como Event ID para deduplicar com o Pixel.**

Mantido de propósito:
- **Consentimento** `NOT_SET` em todas as tags — configurar quando o projeto tiver banner de cookies (CMP) com Consent Mode.
- Evento GA4 **`solicite_orçamento`** com `ç` — mantido para não quebrar o histórico/evento-chave no GA4.

### Do corrigido (M2Z) para o `container-padrao.json`

- IDs da M2Z → placeholders (seção 5.1); nome `Container Padrão - Site/LP`.
- Acionador `click_botao_solicite_diagnostico` (regex no `button_id`) → `click_botao_conversao` (`button_class` = `btn-conversao`).
- Eventos: `solicite_orçamento` → `clique_conversao` (GA4); `Botão Diagnóstico` → `Clique Conversão` (Meta); tag `Meta - Click Botao Diagnostico` → `Meta - Click Conversao`. Sem histórico a preservar num cliente novo.
- Resto idêntico: 10 tags, 2 acionadores, 17 variáveis, template Meta Pixel, `Meta - Lead` com `{{DLV - event_id}}`, consentimento `NOT_SET`.
# automacao-tagueamento

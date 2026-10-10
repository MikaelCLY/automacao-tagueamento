# Tagueamento — padrão de botões, links e formulários

> Copiar este arquivo para `docs/tagueamento.md` de cada projeto e apontar para ele no `CLAUDE.md` do projeto:
> `Antes de criar ou alterar botão, link ou formulário, seguir docs/tagueamento.md.`
>
> Validador: `python3 <pasta-do-padrao>/tag.py` (abre uma janela para escolher o projeto) — sai com código 1 se houver erro; sem erro, gera o container do cliente.

## Princípio

**O site só faz `dataLayer.push`. Toda tag (GA4, Google Ads, Meta) vive no GTM.**
O que é conversão é decidido por uma classe no botão (`btn-conversao`) — o container é o mesmo para todo cliente.

## Regras

1. **Todo `<button>`, `<a>` e `<Link>` tem:**
   - `id` único na página;
   - **uma** classe de tipo `btn-*`, antes das classes utilitárias;
   - texto visível ou `aria-label`.

   Sem exceção — inclusive ícone, menu mobile, link de rodapé, botão de tela de sucesso.

2. **Classe de tipo** — só a **primeira** classe `btn-*` chega ao GTM (`button_class`):

   | Classe          | Quando usar                                                  | No GTM |
   |-----------------|--------------------------------------------------------------|--------|
   | `btn-conversao` | clique que **é conversão** (pedir orçamento, falar com vendas, WhatsApp de lead) | dispara `clique_conversao` (GA4) e `Clique Conversão` (Meta) |
   | `btn-cta`       | chamada para ação que **não** é conversão (ver portfólio, saiba mais) | só `click_botao` no dataLayer |
   | `btn-nav`       | navegação: menu, cards, links de texto, rodapé               | idem |
   | `btn-submit`    | botão de envio de formulário (a conversão é o `envio_formulario`) | idem |
   | `btn-ui`        | controle de interface: tema, busca, abrir menu, carrossel, voltar ao topo | idem |

   - `btn-conversao` **substitui** `btn-cta`, nunca se soma: `class="btn-cta btn-conversao"` não conta como conversão.
   - Na dúvida se um clique é conversão, **pergunte** — é o que entra nos relatórios e no lance das campanhas.

3. **`id`** — kebab-case, sem acento, `<prefixo>-<onde>-<o-que>`:

   | Prefixo   | Uso                          | Exemplo                                |
   |-----------|------------------------------|----------------------------------------|
   | `cta-`    | chamadas para ação           | `cta-hero-orcamento`, `cta-final-whatsapp` |
   | `nav-`    | menu principal               | `nav-logo`, `nav-sobre`                |
   | `nav-m-`  | menu mobile                  | `nav-m-abrir-menu`                     |
   | `lp-nav-` | menu de landing page         | `lp-nav-logo`                          |
   | `form-`   | dentro de formulário         | `form-<form_name>-enviar`              |
   | `card-`   | cards clicáveis              | `card-case-<slug>`                     |
   | `footer-` | rodapé                       | `footer-instagram`                     |
   | `faq-`    | FAQ                          | `faq-pergunta-<n>`                     |
   | `ui-`     | controles de interface       | `ui-voltar-topo`, `ui-tema`            |

   - **Único na página:** o mesmo CTA em dois lugares ganha dois `id`s (`cta-hero-orcamento` ≠ `cta-final-orcamento`).
   - **Estável:** em listas, derivar do dado (`card-case-${item.slug}`), nunca de índice ou valor aleatório.
   - Componente de botão próprio: `id` como **prop obrigatória** no tipo.

4. **Texto:** botão só com ícone leva `aria-label` (`<button id="ui-busca" class="btn-ui" aria-label="Buscar">`). Texto dinâmico → `aria-label` fixo.

5. **Proibido:**
   - `gtag()`, `fbq()`, script do pixel da Meta ou `gtag/js` no código;
   - `onClick` de tracking por botão — o listener global já cobre todos.

6. **Formulário de lead novo:** chamar `trackFormSubmit` no submit **válido**, **antes** do `fetch`, com `form_name` fixo (snake_case).

7. **Renomear `id` ou trocar a classe de um botão de conversão:** avisar quem cuida do GTM/relatórios antes.

8. **Ao terminar:** rodar o validador até sair sem erro e listar os botões `btn-conversao` (id + texto) para quem configura o GTM.

```html
<a id="cta-hero-orcamento" class="btn-conversao rounded-full px-6">Peça um orçamento</a>
<a id="cta-hero-portfolio" class="btn-cta rounded-full px-6">Ver portfólio</a>
<button id="ui-abrir-menu" class="btn-ui p-2" aria-label="Abrir menu"><svg …/></button>
```

## Contrato do dataLayer

Nomes fixos — o container lê exatamente estes.

**`click_botao`** — todo clique em `<button>`/`<a>`:

| Chave           | Valor                                                     |
|-----------------|-----------------------------------------------------------|
| `button_id`     | `id` do elemento                                          |
| `button_class`  | **primeira** classe que começa com `btn-`                 |
| `button_text`   | `aria-label` ou texto visível (espaços normalizados, ≤ 100 caracteres) |
| `page_path`     | `location.pathname + location.search`                     |
| `page_location` | `location.href`                                           |

**`envio_formulario`** — submit válido de formulário de lead:

| Chave                    | Valor                                                    |
|--------------------------|----------------------------------------------------------|
| `form_name`              | identificador fixo do formulário (`contato`, `orcamento`) |
| `event_category`         | `form_submit`                                            |
| `event_label`            | nome legível do formulário                               |
| `element_type`           | `form`                                                   |
| `area`                   | região da página (`hero`, `final`…)                      |
| `form_type`              | `lead`                                                   |
| `event_id`               | UUID por envio (deduplica Google Ads e Meta)             |
| `user_data.email`        | e-mail minúsculo, só se válido (senão omitir a chave)    |
| `user_data.phone_number` | telefone E.164 (`+5541999999999`), só se válido          |
| `page_path`, `page_location` | igual ao clique                                      |

## Implementação de referência

**Loader** — no `<head>`, antes da hidratação (Next.js: `next/script` com `strategy="beforeInteractive"` no layout). Trocar `GTM-XXXXXXX`:

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

Logo após abrir o `<body>`:

```html
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXXX"
  height="0" width="0" style="display:none;visibility:hidden" title="Google Tag Manager"></iframe></noscript>
```

**Listener global de clique** (em React: num `useEffect` de componente client montado no layout):

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

**Formulário:**

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
trackFormSubmit({ formName: "contato", formLabel: "Contato", area: "hero",
                  email: form.email.value, phone: form.whatsapp.value });
```

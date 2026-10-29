# Design system

O design system é feito **inteiramente com TailwindCSS dentro do DTL**:

- O tema (`tailwind.config`) e as classes de componentes (`@layer components` com `@apply`) ficam em `templates/base.html`;
- Os componentes estruturais são partials em `templates/components/`;
- Todas as telas herdam de `base.html` e usam **somente** essas classes e partials.

## Princípios

- **Dark first**: fundo escuro em todas as telas.
- **Gradiente como identidade**: violeta → índigo → ciano em botões primários, logo e destaques.
- **Cores semânticas**: verde-esmeralda para entradas, rosa para saídas, âmbar para alertas.
- **Consistência**: mesmos raios, espaçamentos, sombras e tipografia.
- **Mobile first**: layout funcional a partir de 360px; grids viram uma coluna em telas pequenas.

## Cores

| Token | Uso | Tailwind | Hex |
|---|---|---|---|
| `bg-base` | Fundo da página | `bg-slate-950` | `#020617` |
| `bg-surface` | Cards, sidebar, modais | `bg-slate-900/70` | `#0F172A` |
| `bg-elevated` | Inputs, hovers, linhas | `bg-slate-800/60` | `#1E293B` |
| `border` | Bordas | `border-slate-800` | `#1E293B` |
| `border-focus` | Foco | `border-violet-500` | `#8B5CF6` |
| `text-primary` | Texto principal | `text-slate-100` | `#F1F5F9` |
| `text-secondary` | Texto de apoio | `text-slate-400` | `#94A3B8` |
| `text-muted` | Placeholders | `text-slate-500` | `#64748B` |
| `primary` | Primária | `violet-600` | `#7C3AED` |
| `primary-2` | Gradiente | `indigo-600` | `#4F46E5` |
| `accent` | Destaques | `cyan-400` | `#22D3EE` |
| `success` | Entradas | `emerald-400` | `#34D399` |
| `danger` | Saídas, exclusões | `rose-500` | `#F43F5E` |
| `warning` | Avisos | `amber-400` | `#FBBF24` |
| `info` | Informações | `sky-400` | `#38BDF8` |

### Gradientes

| Nome | Classes |
|---|---|
| Botão primário | `bg-gradient-to-r from-violet-600 to-indigo-600` |
| Botão primário (hover) | `hover:from-violet-500 hover:to-indigo-500` |
| Texto (títulos/logo) | `bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 bg-clip-text text-transparent` |
| Glow de fundo (landing) | `bg-[radial-gradient(ellipse_at_top,_rgba(124,58,237,0.25),_transparent_60%)]` |
| Card de saldo | `bg-gradient-to-br from-violet-600/30 via-indigo-600/20 to-cyan-500/10` |

## Tipografia

Fonte **Inter** (pesos 400, 500, 600 e 700), configurada como `fontFamily.sans`. Valores monetários usam `tabular-nums`.

| Elemento | Classes |
|---|---|
| Display (hero) | `text-4xl md:text-6xl font-bold tracking-tight` |
| H1 | `text-2xl md:text-3xl font-semibold text-slate-100` |
| H2 | `text-lg font-semibold text-slate-100` |
| Corpo | `text-sm md:text-base text-slate-300` |
| Legenda / label | `text-xs font-medium uppercase tracking-wide text-slate-400` |
| Valor de destaque | `text-2xl md:text-3xl font-bold tabular-nums` |

## Classes de componentes

| Grupo | Classes |
|---|---|
| Botões | `btn`, `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger`, `btn-sm` |
| Formulários | `form-label`, `form-input`, `form-field`, `form-help`, `form-error` |
| Superfícies | `card`, `card-highlight` |
| Badges | `badge`, `badge-income`, `badge-expense`, `badge-neutral` |
| Tabelas | `table` |
| Navegação | `nav-link`, `nav-link-active` |
| Links de texto | `link` |
| Texto | `text-gradient`, `amount-income`, `amount-expense` |

A definição completa de cada classe (`@apply`) está na seção 9.4 do [PRD.md](../PRD.md). Ajustes da Sprint 8 (refinamento de acessibilidade), já aplicados em `templates/base.html`:

- `nav-link` (e, por herança, `nav-link-active`) ganhou foco visível: `focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950`. No item ativo, o anel de foco (2px sólido, afastado por 2px) substitui o `ring-1 ring-violet-500/30` do estado ativo e é distinguível dele.
- Nova classe `link`, para links dentro de texto: `rounded font-semibold text-violet-400 transition hover:text-violet-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950`.

## Links de texto

- Links no meio de um parágrafo (ex.: "Não tem conta? Cadastre-se") usam `link`.
- Dentro de alertas coloridos, mantenha a cor do alerta e sublinhe: `link font-medium text-current underline underline-offset-4 hover:text-amber-200` (o foco visível vem de `link`).
- Ações (Salvar, Cancelar, Editar...) continuam com as classes de botão.

## Botões

| Variante | Classe | Uso |
|---|---|---|
| Primário | `btn-primary` | Ação principal (Salvar, Entrar, Nova transação) |
| Secundário | `btn-secondary` | Alternativas (Cancelar, Voltar, Filtrar) |
| Ghost | `btn-ghost` | Ações discretas (Limpar filtros, navegação) |
| Perigo | `btn-danger` | Exclusões |
| Pequeno | `btn-primary btn-sm` | Ações em linhas de tabela |

- No máximo **um** `btn-primary` por bloco.
- Botões de formulário alinhados à direita no desktop e com largura total no mobile (`w-full sm:w-auto`).

## Formulários

- Todo campo é renderizado por `components/_form_field.html`, dentro de `div.form-field`:

```html
<div class="form-field">
  <label for="{{ field.id_for_label }}" class="form-label">{{ field.label }}</label>
  {{ field }}
  {% if field.help_text %}<p class="form-help">{{ field.help_text }}</p>{% endif %}
  {% for error in field.errors %}<p class="form-error">{{ error }}</p>{% endfor %}
</div>
```

- `components/_form.html` inclui o `csrf_token`, os `non_field_errors` em um alerta rosa e os campos. Parâmetros opcionais: `submit_label`, `cancel_url`, `single_column` (coluna única, para login/cadastro em card `max-w-md`) e `submit_full` (botão de envio com `w-full`).
- O help text é renderizado em `div.form-help` (não `<p>`), pois pode conter listas HTML (ex.: regras de senha).
- Formulários ficam dentro de `card`, com `max-w-2xl`.
- Grid de campos: `grid grid-cols-1 gap-5 md:grid-cols-2`; campos longos com `md:col-span-2`.

## Layout

| Elemento | Classes |
|---|---|
| Container autenticado | `mx-auto w-full max-w-7xl px-4 py-6 md:px-8 md:py-8` |
| Stat cards (dashboard) | `grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4` |
| Conteúdo (dashboard) | `grid grid-cols-1 gap-6 lg:grid-cols-3` (principal `lg:col-span-2`) |
| Cards de contas | `grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3` |
| Container público | `mx-auto max-w-6xl px-4 md:px-6` |
| Tabelas | `overflow-x-auto` dentro de `card p-0`; textos longos em `<span class="block max-w-* truncate" title="...">`; ações de linha só com ícone (`btn-sm` + `aria-label` + `title`) |
| Filtros (transações) | `grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5` |

**Área autenticada (`base_app.html`):**

- **Sidebar** fixa à esquerda a partir de `lg` (`w-64 border-r border-slate-800 bg-slate-900/70`), com logo, links e card do usuário com botão Sair no rodapé.
- **Topbar** no mobile (`lg:hidden`), com logo e botão hambúrguer que alterna a classe `hidden` da sidebar (JavaScript mínimo inline). Ao abrir, o foco vai para o primeiro link da sidebar; `Escape` fecha e devolve o foco ao botão; `aria-expanded` e `aria-label` ("Abrir menu"/"Fechar menu") acompanham o estado.
- **Conteúdo** com `_page_header.html` e `_messages.html`.

**Site público (`base_public.html`):** logo à esquerda; à direita, `btn-ghost` "Entrar" e `btn-primary` "Cadastre-se" (ou "Ir para o dashboard" para quem está logado). Footer com "© Finanpy".

## Menu

Itens da sidebar, com ícones SVG inline (outline, 20px):

1. Dashboard
2. Transações
3. Contas
4. Categorias
5. Perfil
6. Sair (rodapé, `btn-ghost`, via `<form method="post">`)

O item ativo usa `nav-link-active`, comparando `request.resolver_match.app_name` / `url_name`.

## Feedback

| Componente | Classes base |
|---|---|
| Alerta de sucesso | `rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300` |
| Alerta de erro | `rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300` |
| Alerta de aviso | `rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-300` |
| Empty state | `card text-center py-12` + ícone, texto `text-slate-400` e `btn-primary` |
| Stat card | `card` (ou `card-highlight` com `highlight=True`) + label, valor de destaque e ícone em círculo com gradiente |
| Confirmação de exclusão | `card max-w-lg` com o nome do objeto, `btn-danger` e `btn-secondary` |
| Paginação | `btn-secondary btn-sm` (anterior/próxima) + "Página X de Y" |

## Formatação de dados

- Moeda: `R$ {{ value|floatformat:'2g' }}` → `R$ 1.234,56` (com `pt-br` e `USE_THOUSAND_SEPARATOR = True`, sem filtro customizado).
- Datas: `{{ value|date:'d/m/Y' }}`.
- Entradas: prefixo `+` e classe `amount-income`. Saídas: prefixo `−` e classe `amount-expense`.
- Título das páginas: `{% block title %}Transações · Finanpy{% endblock %}`.

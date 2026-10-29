# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

Finanpy: app web de finanças pessoais em **Django full stack** (DTL + TailwindCSS via CDN, SQLite). A fonte oficial de requisitos é o `PRD.md`; a documentação derivada está em `docs/` (índice em `docs/README.md`). Qualquer funcionalidade fora do PRD exige revisão do PRD antes — não implemente nada além do especificado.

O andamento é controlado pela lista de tarefas da seção 13 do `PRD.md` (sprints 0 a 10). Ao concluir uma tarefa, marque `[X]` no PRD; a tarefa pai só é marcada quando todas as subtarefas estiverem concluídas.

### Estado atual do código

O projeto está no Sprint 0: apps criadas e registradas, mas sem models, views, forms, URLs, templates ou migrações. Divergências entre o código e o PRD que ainda precisam ser resolvidas:

- `core/settings.py` ainda usa `LANGUAGE_CODE = 'en-us'` e `TIME_ZONE = 'UTC'` (PRD: `'pt-br'` e `'America/Sao_Paulo'`), não define `AUTH_USER_MODEL` nem `TEMPLATES['DIRS']`, e registra as apps pelo nome curto (PRD: caminho do `AppConfig`).
- O banco atual é `db.sqlite3` (PRD: `db.sqlite`).
- O venv usa Python 3.12 e Django 6.1.2 (PRD: Python 3.13+, Django 5+).
- Ainda não há repositório Git nem `.gitignore`.
- `requirements.txt` está codificado em UTF-16 (gerado com `pip freeze >` no PowerShell).

**Crítico:** `users.User` e `AUTH_USER_MODEL = 'users.User'` devem existir antes da primeira migração das apps do projeto.

### Agentes

Subagentes do time ficam em `.claude/agents/` (índice e fluxo de trabalho em `.claude/agents/README.md`): `django-backend`, `django-frontend`, `qa-tester` (Playwright MCP), `code-reviewer` e `devops-docker`. Os agentes de implementação consultam o MCP context7 antes de escrever código.

## Comandos

```bash
.venv\Scripts\Activate.ps1                 # ativar o venv (PowerShell)
pip install -r requirements.txt
python manage.py runserver
python manage.py check
python manage.py makemigrations [--check]
python manage.py migrate
python manage.py test                      # todos os testes
python manage.py test accounts             # testes de uma app
python manage.py test accounts.tests.AccountTests.test_name   # um único teste
pycodestyle .                              # PEP 8 (ou flake8)
```

Testes automatizados (`django.test.TestCase`) e Docker só entram nas sprints 9 e 10.

## Arquitetura

- `core` é o pacote de configuração e também abriga as views transversais (`LandingPageView` e `DashboardView` em `core/views.py`) e o `UserQuerySetMixin` (`core/mixins.py`). Não crie uma app extra para isso.
- Apps de domínio: `users` (User customizado sem `username`, login por e-mail, `UserManager` em `users/managers.py`), `profiles` (criado por signal `post_save` em `profiles/signals.py`), `accounts`, `categories`, `transactions`.
- Relações: `Account`, `Category` e `Transaction` têm `user` FK com `CASCADE`; `Transaction.account` e `Transaction.category` usam `PROTECT`. As `DeleteView`s de contas e categorias capturam `ProtectedError` e exibem mensagem em vez de excluir.
- O **saldo da conta não é persistido**: `initial_balance + entradas − saídas`, calculado com `Sum` condicional (`filter=Q(...)`); nas listagens, via `annotate()` para evitar N+1. O dashboard reutiliza esse cálculo e trata `None` das agregações como `Decimal('0')`.
- `Transaction.transaction_type` reaproveita as constantes `INCOME`/`EXPENSE` de `Category`; o `clean()` do form exige que a categoria tenha o mesmo tipo da transação.
- **Isolamento por usuário**: toda view privada usa `LoginRequiredMixin` + `UserQuerySetMixin` (filtra `get_queryset()` por `request.user`, logo objeto alheio → 404). `CreateView`s atribuem `form.instance.user` no `form_valid()`. Forms com selects de conta/categoria recebem `user` via `get_form_kwargs()` e filtram os querysets.
- URLs em português (`/contas/`, `/transacoes/`...) com nomes de rota em inglês sob namespace (`accounts:list`, `transactions:create`...). `LOGIN_URL = 'users:login'`, `LOGIN_REDIRECT_URL = 'dashboard'`, `LOGOUT_REDIRECT_URL = 'landing'`. Tabela completa em `docs/estrutura-do-projeto.md`.

### Templates e design system

- `templates/` na raiz: `base.html` (contém o `tailwind.config` e todas as classes de componentes via `@layer components` + `@apply`), `base_public.html` (site público) e `base_app.html` (sidebar + topbar), mais partials em `templates/components/` (`_form.html`, `_form_field.html`, `_messages.html`, `_page_header.html`, `_empty_state.html`, `_pagination.html`, `_confirm_delete.html`...).
- Telas usam **somente** as classes do design system (`btn-primary`, `card`, `form-field`, `badge-income`, `amount-expense`...) e os partials; não crie estilos ad hoc. Especificação em `docs/design-system.md` e seção 9 do PRD.
- Campos de formulário são estilizados pelo wrapper `div.form-field` do `_form_field.html`, então não configure classes CSS em widgets. Widgets usados: `DateInput(attrs={'type': 'date'})` e `NumberInput(attrs={'step': '0.01', 'min': '0.01'})`.
- Moeda: `R$ {{ value|floatformat:'2g' }}` (sem filtro customizado; depende de `pt-br` + `USE_THOUSAND_SEPARATOR = True`). Datas: `|date:'d/m/Y'`.

## Convenções

- Código em inglês; todo texto da interface em português brasileiro (labels, `verbose_name`, mensagens). As mensagens exatas de sucesso/erro estão em `docs/regras-de-negocio.md`.
- PEP 8 e **aspas simples**.
- Todo model tem `created_at` (`auto_now_add=True`) e `updated_at` (`auto_now=True`), `verbose_name` em português, `Meta.ordering` e `__str__`.
- Valores monetários sempre `DecimalField(max_digits=12, decimal_places=2)`, nunca `float`.
- Choices como constantes na classe (`INCOME = 'income'`, `TYPE_CHOICES = [...]`).
- Signals sempre em `signals.py` da app, importados no `ready()` do `AppConfig`.
- Preferir recursos nativos: CBVs, `SuccessMessageMixin`, `django.contrib.messages`, auth e admin. Logout somente via POST.

# Estrutura do projeto

## Diretórios

```
finanpy
├── accounts            # contas bancárias
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── categories          # categorias (mesma estrutura de accounts)
├── core                # configurações globais
│   ├── asgi.py
│   ├── mixins.py       # UserQuerySetMixin
│   ├── settings.py
│   ├── urls.py
│   ├── views.py        # landing page e dashboard
│   └── wsgi.py
├── profiles            # perfis (mesma estrutura + signals.py)
├── transactions        # transações (mesma estrutura de accounts)
├── users               # usuários (mesma estrutura + managers.py)
├── templates
│   ├── base.html               # layout raiz + design system
│   ├── base_public.html        # layout do site público
│   ├── base_app.html           # layout da área autenticada
│   ├── components/             # partials reutilizáveis
│   ├── core/                   # landing.html, dashboard.html
│   ├── users/                  # login.html, signup.html
│   ├── profiles/
│   ├── accounts/
│   ├── categories/
│   └── transactions/
├── docs/
├── db.sqlite
├── manage.py
├── PRD.md
└── requirements.txt
```

## Apps

| App | Responsabilidade |
|---|---|
| `core` | Configurações globais, landing page, dashboard e `UserQuerySetMixin` |
| `users` | `User` customizado (login por e-mail), `UserManager`, cadastro, login e logout |
| `profiles` | Perfil do usuário (telefone e data de nascimento), criado por signal |
| `accounts` | Contas bancárias e cálculo de saldo |
| `categories` | Categorias de entrada e saída |
| `transactions` | Transações, filtros e paginação |

O `core` concentra as duas views transversais (landing e dashboard), para não criar uma app só para isso.

Arquivos além do padrão do `startapp` são criados só quando necessários: `urls.py`, `forms.py`, `signals.py`, `managers.py`.

## Templates e componentes

Cada app tem sua subpasta em `templates/`. Os partials em `templates/components/` são:

| Partial | Função |
|---|---|
| `_messages.html` | Alertas do messages framework |
| `_form_field.html` | Label, campo, ajuda e erros de um campo |
| `_form.html` | Formulário completo (`csrf_token`, erros gerais, campos, botões) |
| `_page_header.html` | Título, subtítulo e botão de ação da página |
| `_stat_card.html` | Indicador do dashboard |
| `_empty_state.html` | Estado de lista vazia com chamada para ação |
| `_pagination.html` | Paginação que preserva a querystring |
| `_sidebar.html` | Menu lateral da área autenticada |
| `_topbar.html` | Barra superior no mobile |
| `_confirm_delete.html` | Confirmação de exclusão |

Nomes dos templates de CRUD seguem o padrão do Django: `<model>_list.html`, `<model>_form.html`, `<model>_confirm_delete.html`.

## Rotas

URLs em português; nomes de rota com namespace (`app_name`) em inglês.

| URL | View | Nome | Acesso |
|---|---|---|---|
| `/` | `LandingPageView` | `landing` | Público |
| `/cadastro/` | `SignUpView` | `users:signup` | Público |
| `/entrar/` | `UserLoginView` | `users:login` | Público |
| `/sair/` | `LogoutView` | `users:logout` | Autenticado |
| `/dashboard/` | `DashboardView` | `dashboard` | Autenticado |
| `/perfil/` | `ProfileDetailView` | `profiles:detail` | Autenticado |
| `/perfil/editar/` | `ProfileUpdateView` | `profiles:update` | Autenticado |
| `/contas/` | `AccountListView` | `accounts:list` | Autenticado |
| `/contas/nova/` | `AccountCreateView` | `accounts:create` | Autenticado |
| `/contas/<pk>/editar/` | `AccountUpdateView` | `accounts:update` | Autenticado |
| `/contas/<pk>/excluir/` | `AccountDeleteView` | `accounts:delete` | Autenticado |
| `/categorias/` | `CategoryListView` | `categories:list` | Autenticado |
| `/categorias/nova/` | `CategoryCreateView` | `categories:create` | Autenticado |
| `/categorias/<pk>/editar/` | `CategoryUpdateView` | `categories:update` | Autenticado |
| `/categorias/<pk>/excluir/` | `CategoryDeleteView` | `categories:delete` | Autenticado |
| `/transacoes/` | `TransactionListView` | `transactions:list` | Autenticado |
| `/transacoes/nova/` | `TransactionCreateView` | `transactions:create` | Autenticado |
| `/transacoes/<pk>/editar/` | `TransactionUpdateView` | `transactions:update` | Autenticado |
| `/transacoes/<pk>/excluir/` | `TransactionDeleteView` | `transactions:delete` | Autenticado |
| `/admin/` | Django Admin | — | Superusuário |

## Configurações principais (`core/settings.py`)

```python
INSTALLED_APPS = [
    # ... apps nativas + 'django.contrib.humanize'
    'users.apps.UsersConfig',
    'profiles.apps.ProfilesConfig',
    'accounts.apps.AccountsConfig',
    'categories.apps.CategoriesConfig',
    'transactions.apps.TransactionsConfig',
]

AUTH_USER_MODEL = 'users.User'

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']
DATABASES['default']['NAME'] = BASE_DIR / 'db.sqlite'

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing'
```

Cada `AppConfig` define `verbose_name` em português (ex.: `verbose_name = 'Usuários'`).

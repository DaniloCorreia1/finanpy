# Finanpy

Aplicação web de gestão de finanças pessoais, simples e enxuta, feita com Django full stack. O usuário cadastra suas contas bancárias, organiza categorias de entrada e saída e registra transações, acompanhando tudo em um dashboard com saldo total, entradas e saídas do mês, saldo por conta e últimas transações.

O sistema tem duas áreas:

- **Site público**: landing page com as opções **Cadastre-se** e **Entrar**;
- **Área autenticada**: dashboard, contas bancárias, categorias, transações (com filtros e paginação) e perfil do usuário. O login é feito com **e-mail e senha**.

Os requisitos estão no [PRD.md](PRD.md) e a documentação derivada em [docs/](docs/README.md).

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ |
| Framework | Django 6.1 |
| Frontend | Django Template Language (DTL) |
| Estilização | TailwindCSS v3 via CDN, com o design system no `templates/base.html` |
| Banco de dados | SQLite (`db.sqlite`) |
| Autenticação | `django.contrib.auth` com `User` customizado (login por e-mail) |
| Testes | `django.test` (`TestCase`) |
| Containerização | Docker + docker compose |

## Rodando localmente

Pré-requisitos: Python 3.12 ou superior (o Django 6.1 exige Python >= 3.12) e Git.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # opcional: acesso ao admin (login com e-mail)
python manage.py runserver
```

Linux / macOS (bash):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # opcional: acesso ao admin (login com e-mail)
python manage.py runserver
```

- Aplicação: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>

## Variáveis de ambiente

As configurações sensíveis são lidas de variáveis de ambiente em `core/settings.py`. Todas têm padrões de desenvolvimento, então o projeto roda sem configurar nada. O arquivo [.env.example](.env.example) documenta cada uma.

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | chave de desenvolvimento (`django-insecure-...`) | Chave secreta do Django. Troque fora do desenvolvimento. |
| `DEBUG` | `True` | Modo de depuração. Aceita `True`/`False` ou `1`/`0`. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts aceitos, separados por vírgula. |
| `SQLITE_PATH` | `db.sqlite` na raiz do projeto | Caminho do banco SQLite. No Docker aponta para o volume. |

Localmente, o Django **não** lê o arquivo `.env`; defina as variáveis no terminal antes de rodar o servidor:

```powershell
# PowerShell
$env:DEBUG = 'False'
$env:ALLOWED_HOSTS = 'localhost,127.0.0.1'
python manage.py runserver
```

```bash
# bash
DEBUG=False ALLOWED_HOSTS=localhost,127.0.0.1 python manage.py runserver
```

> Com `DEBUG=False`, o `runserver` deixa de servir arquivos estáticos (por exemplo, o CSS do admin). As telas da aplicação usam o Tailwind via CDN e não são afetadas.

## Rodando com Docker

Pré-requisito: Docker com o plugin `docker compose`.

```bash
cp .env.example .env    # opcional: sem o .env valem os padrões de desenvolvimento
docker compose up --build
```

- Aplicação: <http://localhost:8000/>
- Na inicialização, o container executa `python manage.py migrate` e depois sobe o servidor em `0.0.0.0:8000`.
- O banco fica em `/app/data/db.sqlite`, dentro do volume nomeado `sqlite_data`, e persiste entre reinicializações e recriações do container.

Comandos úteis:

```bash
docker compose up -d --build                              # sobe em segundo plano
docker compose logs -f web                                # acompanha os logs
docker compose exec web python manage.py createsuperuser  # cria um superusuário
docker compose exec web python manage.py test             # roda os testes no container
docker compose down                                       # para e remove o container (mantém o volume)
docker compose down -v                                    # remove também o volume (apaga o banco)
```

## Testes

Os testes usam `django.test.TestCase` e ficam no `tests.py` de cada app.

```bash
python manage.py test                                              # todos os testes
python manage.py test accounts                                     # testes de uma app
python manage.py test accounts.tests.AccountCrudViewTests.test_name  # um único teste
```

Cobertura (o `coverage` não faz parte do `requirements.txt`; instale-o no venv):

```bash
pip install coverage
coverage run --source=. --omit=".venv/*,*/migrations/*,*/tests.py,manage.py,core/asgi.py,core/wsgi.py" manage.py test
coverage report
```

Outras verificações:

```bash
python manage.py check                     # configuração do projeto
python manage.py makemigrations --check    # migrações pendentes
pycodestyle --exclude=.venv,migrations .   # PEP 8
```

## Estrutura

```
finanpy
├── core            # configurações, landing page, dashboard e UserQuerySetMixin
├── users           # User customizado (login por e-mail), cadastro, login e logout
├── profiles        # perfil do usuário, criado por signal
├── accounts        # contas bancárias e cálculo de saldo
├── categories      # categorias de entrada e saída
├── transactions    # transações, filtros e paginação
├── templates       # layouts, design system e partials (components/)
├── docs            # documentação do projeto
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── manage.py
├── PRD.md
└── requirements.txt
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [PRD.md](PRD.md) | Requisitos do produto (fonte oficial) e lista de tarefas |
| [docs/visao-geral.md](docs/visao-geral.md) | Produto, propósito, público-alvo e objetivos |
| [docs/ambiente-de-desenvolvimento.md](docs/ambiente-de-desenvolvimento.md) | Preparação do ambiente |
| [docs/estrutura-do-projeto.md](docs/estrutura-do-projeto.md) | Diretórios, apps, templates e rotas |
| [docs/modelo-de-dados.md](docs/modelo-de-dados.md) | Entidades e relacionamentos |
| [docs/regras-de-negocio.md](docs/regras-de-negocio.md) | Requisitos funcionais e mensagens |
| [docs/padroes-de-codigo.md](docs/padroes-de-codigo.md) | Convenções de Python e Django |
| [docs/design-system.md](docs/design-system.md) | Cores, tipografia e componentes |
| [docs/roadmap.md](docs/roadmap.md) | Sprints de desenvolvimento |

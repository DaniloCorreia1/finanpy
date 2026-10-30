# Finanpy

Aplicação web de gestão de finanças pessoais, simples e enxuta, feita com Django full stack. O usuário cadastra suas contas bancárias, organiza categorias de entrada e saída e registra transações, acompanhando tudo em um dashboard com saldo total, entradas e saídas do mês, saldo por conta e últimas transações.

O sistema tem duas áreas:

- **Site público**: landing page com as opções **Cadastre-se** e **Entrar**;
- **Área autenticada**: dashboard, contas bancárias, categorias, transações (com filtros e paginação) e perfil do usuário. O login é feito com **e-mail e senha**.

O dashboard também mostra uma **análise financeira gerada por IA** (resumo, insights e dicas sobre os últimos três meses), produzida por um agente LangChain com a OpenAI.

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
| IA | LangChain 1.x (`langchain`, `langchain-openai`) com OpenAI `gpt-5-mini` |
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
| `OPENAI_API_KEY` | vazio | Chave da OpenAI. Vazia desabilita a geração de análises. |
| `AI_MODEL_NAME` | `gpt-5-mini` | Modelo usado pelo agente. |
| `AI_REQUEST_TIMEOUT` | `60` | Timeout, em segundos, de cada chamada ao modelo. |
| `AI_MAX_COMPLETION_TOKENS` | `4000` | Limite de tokens de saída por chamada. |
| `AI_MIN_TRANSACTIONS` | `5` | Mínimo de transações no período para chamar a IA. |
| `AI_MANUAL_COOLDOWN_MINUTES` | `60` | Intervalo mínimo entre pedidos pelo botão do dashboard. |

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

## Análise financeira com IA

A app `ai` usa um agente LangChain 1.x com a OpenAI (`gpt-5-mini`) para analisar os lançamentos dos últimos três meses de cada usuário (do 1º dia do mês de dois meses atrás até hoje) e gravar resumo, insights e dicas na tabela `FinancialInsight`. O dashboard mostra a análise mais recente e nunca chama a IA.

- O agente só lê dados agregados do próprio usuário (tools somente leitura); nome, e-mail, telefone, descrições de transações e nomes de contas ou bancos não são enviados à OpenAI.
- Usuários com menos de `AI_MIN_TRANSACTIONS` transações no período recebem um aviso de dados insuficientes, sem chamada à IA.
- Falhas da API não gravam análise e aparecem no log `ai` (sem dados financeiros nem a chave).

### Configurando a OpenAI

Crie uma chave em <https://platform.openai.com/api-keys> e defina `OPENAI_API_KEY` no ambiente (ou no `.env`, com Docker). Sem a chave, a aplicação funciona normalmente, mas o botão **Gerar nova análise** fica oculto e o command encerra com erro.

```powershell
# PowerShell
$env:OPENAI_API_KEY = 'sk-...'
python manage.py runserver
```

```bash
# bash
export OPENAI_API_KEY='sk-...'
python manage.py runserver
```

### Gerando as análises

```bash
python manage.py generate_financial_insights                         # todos os usuários ativos
python manage.py generate_financial_insights --user ana@example.com  # um único usuário
```

O command processa um usuário por vez (a falha de um não interrompe os demais) e termina com o resumo: análises geradas, dados insuficientes, sem mudança e falhas (identificadas pelo `id` do usuário). O usuário também pode pedir uma nova análise pelo botão **Gerar nova análise** do dashboard, respeitando o intervalo de `AI_MANUAL_COOLDOWN_MINUTES`. O controle desse intervalo usa o cache local do Django (em memória, por processo): ele é zerado quando o servidor reinicia e não é compartilhado entre processos.

### Agendamento sugerido

Semanal, às segundas-feiras às 06:00 (`America/Sao_Paulo`). A análise cobre três meses, então a frequência semanal equilibra custo e utilidade.

- **Linux/macOS (cron)**, com `crontab -e` (a variável `OPENAI_API_KEY` precisa estar disponível para o cron):

  ```cron
  0 6 * * 1 cd /caminho/finanpy && .venv/bin/python manage.py generate_financial_insights >> insights.log 2>&1
  ```

- **Windows (Agendador de Tarefas)**:

  ```powershell
  schtasks /Create /SC WEEKLY /D MON /ST 06:00 /TN "Finanpy - analises de IA" /TR "C:\caminho\finanpy\.venv\Scripts\python.exe C:\caminho\finanpy\manage.py generate_financial_insights"
  ```

  A variável `OPENAI_API_KEY` precisa estar definida para o usuário que executa a tarefa (por exemplo, com `setx OPENAI_API_KEY "sk-..."`).

- **Docker**, agendando no host o comando:

  ```bash
  docker compose run --rm web python manage.py generate_financial_insights
  ```

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

Os testes usam `django.test.TestCase` e ficam no `tests.py` de cada app (na app `ai`, no pacote `ai/tests/`). Os testes da IA usam o LLM mockado: não acessam a rede nem precisam de `OPENAI_API_KEY`.

```bash
python manage.py test                                              # todos os testes
python manage.py test accounts                                     # testes de uma app
python manage.py test accounts.tests.AccountCrudViewTests.test_name  # um único teste
```

Cobertura (o `coverage` não faz parte do `requirements.txt`; instale-o no venv):

```bash
pip install coverage
coverage run --source=. --omit=".venv/*,*/migrations/*,*/tests.py,*/tests/*,manage.py,core/asgi.py,core/wsgi.py" manage.py test
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
├── ai              # agente de IA financeiro (LangChain + OpenAI)
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

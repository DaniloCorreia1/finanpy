# Ambiente de desenvolvimento

## Pré-requisitos

- Python 3.13+
- Git

## Instalação

Na raiz do projeto:

```bash
# Criar o ambiente virtual
python -m venv .venv

# Ativar o ambiente virtual
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

# Instalar as dependências
pip install -r requirements.txt
```

## Banco de dados

O projeto usa o SQLite padrão do Django.

```bash
python manage.py migrate
python manage.py createsuperuser   # login do admin com e-mail
```

> **Importante:** o model `users.User` e o `AUTH_USER_MODEL = 'users.User'` precisam existir **antes** da primeira migração. Trocar o model de usuário depois gera conflitos de migração.

## Executando

```bash
python manage.py runserver
```

- Aplicação: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Comandos úteis

| Comando | Uso |
|---|---|
| `python manage.py check` | Verifica a configuração do projeto |
| `python manage.py makemigrations` | Gera migrações após alterar models |
| `python manage.py makemigrations --check` | Confirma que não há migrações pendentes |
| `python manage.py migrate` | Aplica as migrações |
| `python manage.py test` | Executa os testes |
| `pycodestyle .` ou `flake8` | Verifica a conformidade com a PEP 8 |

## Dependências

Ao instalar um novo pacote, atualize o `requirements.txt`:

```bash
pip freeze > requirements.txt
```

## `.gitignore`

Devem ficar fora do repositório: `__pycache__/`, `*.pyc`, `.venv/`, `db.sqlite`, `.env`.

## Docker (sprint final)

Previsto no PRD: `docker compose up` sobe a aplicação em `http://localhost:8000`, com o SQLite persistido em volume. `SECRET_KEY`, `DEBUG` e `ALLOWED_HOSTS` passam a ser lidos de variáveis de ambiente, documentadas em `.env.example`.

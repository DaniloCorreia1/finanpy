# Imagem da aplicação Finanpy (Django + SQLite).
# Django 6.1 exige Python >= 3.12.
FROM python:3.12-slim

# Não gerar arquivos .pyc e enviar a saída do Python direto para os logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências primeiro, para aproveitar o cache de camadas do Docker.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código da aplicação.
COPY . .

# Usuário sem privilégios de root; /app/data guarda o banco SQLite
# (montado como volume no docker-compose.yml).
RUN useradd --create-home --uid 1000 finanpy \
    && mkdir -p /app/data \
    && chown -R finanpy:finanpy /app/data
USER finanpy

ENV SQLITE_PATH=/app/data/db.sqlite

EXPOSE 8000

# Aplica as migrações e sobe o servidor acessível de fora do container.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]

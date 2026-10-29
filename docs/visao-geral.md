# Visão geral

## O produto

O **Finanpy** é uma aplicação web de gestão de finanças pessoais, simples e enxuta. O usuário cadastra suas contas bancárias, organiza categorias e registra transações de entrada e saída, acompanhando tudo em um dashboard.

O sistema tem duas áreas:

1. **Site público** (landing page): apresenta o produto, com as opções **Cadastre-se** e **Entrar**.
2. **Área autenticada**: acessível só após o login, com:
   - **Dashboard**: saldo total, entradas e saídas do mês, saldo por conta e últimas transações;
   - **Contas bancárias** (CRUD);
   - **Categorias** de entrada e saída (CRUD);
   - **Transações** (CRUD com filtros);
   - **Perfil** do usuário (visualização e edição).

O login é feito com **e-mail e senha**, e não com username.

## Propósito

Permitir que pessoas físicas saibam quanto dinheiro têm (somando todas as contas), entendam de onde vem e para onde vai o dinheiro (por categorias), registrem o dia a dia com poucos cliques e vejam o resumo do mês logo após o login.

## Público-alvo

- Pessoas físicas que querem organizar as finanças sem planilhas ou apps complexos;
- Usuários com várias contas (corrente, poupança, carteira) que querem ver o saldo unificado;
- Acesso pelo navegador, no desktop e no celular;
- Letramento digital básico a intermediário: a interface deve se explicar sozinha.

## Princípios

- **Simplicidade**: sem over engineering; nada além do especificado no PRD.
- **Stack nativa**: Class Based Views, forms, auth, messages e admin do Django.
- **Idiomas**: código em inglês; interface em português brasileiro.
- **Isolamento**: cada usuário vê e manipula somente os próprios dados.

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.13+ |
| Framework | Django 5+ |
| Frontend | Django Template Language (DTL) |
| Estilização | TailwindCSS v3 via CDN |
| Fonte | Inter (Google Fonts) |
| Banco de dados | SQLite |
| Autenticação | `django.contrib.auth` com `User` customizado (login por e-mail) |
| Feedback | `django.contrib.messages` |
| Administração | `django.contrib.admin` |
| Testes (sprint final) | `django.test.TestCase` |
| Containerização (sprint final) | Docker + docker-compose |

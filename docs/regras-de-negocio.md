# Regras de negócio

Resumo dos requisitos funcionais (RF) do PRD.

## Site público

- `/` é pública e mostra a landing page (hero, recursos e chamada final "Comece agora, é grátis").
- Visitante vê **Cadastre-se** e **Entrar**; usuário logado vê **Ir para o dashboard**.

## Autenticação

- **Cadastro**: nome, sobrenome, e-mail, senha e confirmação. O e-mail é único.
- Após o cadastro, o usuário é autenticado e vai para o dashboard.
- **Login** com e-mail e senha, redirecionando para o dashboard ou para a URL do `next`.
- **Logout** via POST, redirecionando para a landing page.
- Rotas privadas redirecionam visitantes para `/entrar/?next=<rota>`.
- Usuário logado que acessa login ou cadastro é redirecionado ao dashboard.

## Perfil

- Criado automaticamente no cadastro (signal).
- Mostra nome, sobrenome, e-mail, telefone e data de nascimento.
- Permite editar nome, sobrenome, telefone e data de nascimento. O e-mail é só leitura.

## Contas bancárias

- Campos: nome, banco, tipo e saldo inicial.
- A lista mostra o saldo atual de cada conta: positivo em verde, negativo em rosa.
- Conta com transações **não pode ser excluída**.

## Categorias

- Campos: nome e tipo (Entrada/Saída).
- O nome é único por usuário e por tipo.
- A lista separa as categorias de entrada e as de saída.
- Categoria com transações **não pode ser excluída**.

## Transações

- Campos: tipo, descrição, valor, data, conta e categoria.
- A data vem preenchida com o dia atual (`timezone.localdate()`).
- Os selects mostram só as contas e categorias do usuário; as categorias aparecem agrupadas em "Entradas" e "Saídas".
- A categoria precisa ser do mesmo tipo da transação.
- O valor precisa ser maior que zero.
- A lista vai da mais recente para a mais antiga, com 20 itens por página.
- Filtros via GET: tipo, conta, categoria, data inicial e data final. A paginação mantém os filtros.
- Sem contas ou categorias cadastradas, o formulário mostra um aviso com links para cadastrá-las.

## Dashboard

- Stat cards: **Saldo total**, **Entradas do mês**, **Saídas do mês** e **Resultado do mês** (entradas − saídas).
- O mês considerado é o mês corrente no fuso `America/Sao_Paulo`.
- Lista de contas com saldo atual e link "Gerenciar contas".
- Últimas 5 transações, com link "Ver todas".
- Atalhos: Nova transação, Nova conta e Nova categoria.
- Usuário sem dados vê valores zerados e empty states com os primeiros passos.

## Regras gerais

- Cada usuário vê e altera **somente os próprios dados**. Acessar objeto de outro usuário retorna **404**.
- Toda criação, edição e exclusão mostra uma mensagem de feedback em português.
- Toda exclusão passa por uma página de confirmação.
- Listas vazias mostram um empty state com chamada para cadastro.

## Mensagens padrão

| Situação | Mensagem |
|---|---|
| Cadastro concluído | Conta criada com sucesso. Bem-vindo(a) ao Finanpy! |
| E-mail duplicado | Já existe um usuário com este e-mail. |
| Login inválido | E-mail ou senha inválidos. |
| Perfil salvo | Perfil atualizado com sucesso. |
| Conta criada / atualizada / excluída | Conta criada com sucesso. / Conta atualizada com sucesso. / Conta excluída com sucesso. |
| Conta com transações | Esta conta possui transações e não pode ser excluída. |
| Categoria criada / atualizada / excluída | Categoria criada com sucesso. / Categoria atualizada com sucesso. / Categoria excluída com sucesso. |
| Categoria duplicada | Você já possui uma categoria com este nome e tipo. |
| Categoria com transações | Esta categoria possui transações e não pode ser excluída. |
| Transação criada / atualizada / excluída | Transação registrada com sucesso. / Transação atualizada com sucesso. / Transação excluída com sucesso. |
| Categoria de tipo diferente | A categoria deve ser do mesmo tipo da transação. |
| Valor inválido | O valor deve ser maior que zero. |

## Fluxos de UX

```mermaid
flowchart TD
    A([Visitante]) --> B[Landing page]
    B --> C{Já possui conta?}
    C -- Não --> D[Cadastro] --> D1{Dados válidos?}
    D1 -- Não --> D
    D1 -- Sim --> D2[Cria usuário + perfil e autentica] --> F
    C -- Sim --> E[Login] --> E1{Credenciais válidas?}
    E1 -- Não --> E
    E1 -- Sim --> F[Dashboard]

    F --> G[Contas]
    F --> H[Categorias]
    F --> I[Transações]
    F --> J[Perfil]
    F --> K[Sair] --> B

    G --> G1{Excluir: possui transações?}
    G1 -- Sim --> G2[Bloqueia e exibe aviso]
    G1 -- Não --> G3[Confirma exclusão]

    H --> H1{Excluir: possui transações?}
    H1 -- Sim --> H2[Bloqueia e exibe aviso]
    H1 -- Não --> H3[Confirma exclusão]

    I --> I1[Nova transação] --> I2{Categoria compatível e valor > 0?}
    I2 -- Não --> I1
    I2 -- Sim --> I3[Salva e exibe sucesso]
```

O fluxograma completo está na seção 6.9 do [PRD.md](../PRD.md).

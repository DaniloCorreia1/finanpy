# Roadmap

O desenvolvimento é dividido em sprints. A lista detalhada de tarefas, com os checkboxes de andamento, fica na seção 13 do [PRD.md](../PRD.md).

| Sprint | Tema | Entregas principais |
|---|---|---|
| 0 | Setup | Ambiente, projeto Django, apps, settings, `User` customizado, rotas base |
| 1 | Design system | `base.html`, partials de componentes, layouts público e autenticado, landing page |
| 2 | Autenticação | Cadastro, login por e-mail, logout, dashboard placeholder |
| 3 | Perfis | Model `Profile`, signal de criação, visualização e edição |
| 4 | Contas bancárias | Model `Account`, `UserQuerySetMixin`, CRUD, saldo atual |
| 5 | Categorias | Model `Category`, validação de duplicidade, CRUD |
| 6 | Transações | Model `Transaction`, validações, CRUD, filtros, paginação |
| 7 | Dashboard | Stat cards, últimas transações, contas e ações rápidas |
| 8 | Refinamento | Revisão de interface, segurança, PEP 8 e validação manual |
| 9 | Testes | Testes automatizados com `django.test.TestCase` |
| 10 | Docker e entrega | Variáveis de ambiente, Docker, docker-compose, README |

## Regras

- Uma tarefa só é marcada como concluída (`[X]`) no PRD quando todas as subtarefas estiverem prontas.
- Ao fim de cada sprint, validar manualmente os fluxos entregues.
- Testes automatizados e Docker ficam só para as sprints 9 e 10.

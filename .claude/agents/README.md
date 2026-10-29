# Agentes do Finanpy

Agentes de IA (subagentes do Claude Code) que formam o time de desenvolvimento do Finanpy. Todos seguem o [PRD.md](../../PRD.md) e a [documentação do projeto](../../docs/README.md).

| Agente | Função | Quando usar |
|---|---|---|
| [django-backend](django-backend.md) | Desenvolvedor backend Django | Models, migrações, managers, signals, forms, views, URLs, mixins, settings e admin |
| [django-frontend](django-frontend.md) | Desenvolvedor frontend (DTL + TailwindCSS) | Templates, layouts, partials, design system no `base.html`, landing page e responsividade |
| [qa-tester](qa-tester.md) | QA / tester | Após cada entrega, para validar no navegador os fluxos e o design; na Sprint 9, para escrever testes automatizados |
| [code-reviewer](code-reviewer.md) | Revisor de código | Antes de marcar uma tarefa ou sprint como concluída: aderência ao PRD, segurança, isolamento, desempenho e estilo |
| [devops-docker](devops-docker.md) | DevOps | Somente na Sprint 10: variáveis de ambiente, Docker, docker-compose e README de execução |
| [langchain-ai-specialist](langchain-ai-specialist.md) | Engenheiro de integrações com IA (LangChain 1.0 + OpenAI) | Na Sprint 11: tudo da app `ai` (dependências, model, schemas, tools, prompt, agente, service, command, view de geração e testes com o LLM mockado) |

## MCP servers

| MCP server | Usado por | Para quê |
|---|---|---|
| **context7** | `django-backend`, `django-frontend`, `qa-tester` (testes automatizados), `devops-docker`, `langchain-ai-specialist` | Consultar a documentação atualizada de Django, TailwindCSS, Docker, LangChain 1.0 e `langchain-openai` antes de escrever código (obrigatório para o `langchain-ai-specialist` antes de qualquer código de LangChain) |
| **playwright** | `qa-tester` | Acessar o sistema no navegador, testar os fluxos e verificar o design em 360px, 768px e 1280px |

## Fluxo de trabalho sugerido

Para cada tarefa da seção 13 do PRD:

1. **django-backend** implementa models, forms, views e URLs.
2. **django-frontend** cria os templates usando o design system.
3. **qa-tester** valida a funcionalidade e o visual no navegador.
4. **code-reviewer** revisa o código.
5. As correções voltam para o agente responsável, e a tarefa é marcada como `[X]` no PRD.

Tarefas só de interface (como a Sprint 1) começam pelo `django-frontend`. A Sprint 9 é conduzida pelo `qa-tester` e a Sprint 10, pelo `devops-docker`. A Sprint 11 (Agente de IA Financeiro) é conduzida pelo `langchain-ai-specialist`; o `django-frontend` cria o card do dashboard, e o `qa-tester` e o `code-reviewer` validam como nas demais sprints.

## Como usar

Os agentes ficam em `.claude/agents/` e são carregados automaticamente pelo Claude Code. Você pode chamá-los pelo nome, por exemplo: *"use o django-backend para implementar a tarefa 4.1 do PRD"*. Para ver a lista, use o comando `/agents`.

# Padrões de código

## Estilo

- Seguir a **PEP 8** (verificar com `pycodestyle` ou `flake8`).
- Usar **aspas simples** sempre que possível.
- Todo o código (variáveis, funções, classes, models, campos) em **inglês**.
- Todo texto exibido ao usuário em **português brasileiro**: labels, `verbose_name`, mensagens, títulos e erros.
- Não deixar imports, arquivos ou código sem uso.

## Princípios

- **Sem over engineering**: implementar só o que está no PRD.
- **Recursos nativos do Django** sempre que possível: CBVs, forms, auth, messages e admin.
- Cada domínio em sua própria app.

## Models

- Todo model tem os campos de auditoria:

```python
created_at = models.DateTimeField('criado em', auto_now_add=True)
updated_at = models.DateTimeField('atualizado em', auto_now=True)
```

- `verbose_name` em português nos campos e no `Meta` (`verbose_name` e `verbose_name_plural`).
- Sempre definir `__str__` e `Meta.ordering`.
- Usar `settings.AUTH_USER_MODEL` para referenciar o usuário.
- Valores monetários em `DecimalField`, nunca `float`.
- Choices declaradas como constantes da classe (`INCOME = 'income'`, `TYPE_CHOICES = [...]`).
- Valores derivados (como o saldo) são calculados via ORM, não salvos em campo.

## Views

- Usar Class Based Views (`ListView`, `CreateView`, `UpdateView`, `DeleteView`, `DetailView`, `TemplateView`).
- Views privadas usam `LoginRequiredMixin`.
- Views de listagem, edição e exclusão usam o `UserQuerySetMixin` (`core/mixins.py`), que filtra o `get_queryset()` por `user=self.request.user`. Assim, um objeto de outro usuário retorna 404.
- Nas `CreateView`s, atribuir o dono em `form_valid()`:

```python
def form_valid(self, form):
    form.instance.user = self.request.user
    return super().form_valid(form)
```

- Mensagens de sucesso com `SuccessMessageMixin`.
- `success_url` com `reverse_lazy('<app>:list')`.
- Nas `DeleteView`s de contas e categorias, capturar `ProtectedError` em `form_valid()`, mostrar a mensagem de erro e redirecionar para a lista.
- Usar `select_related` em listagens com relacionamentos e `annotate()` para evitar N+1.

## Forms

- Usar `ModelForm` para cadastros e `forms.Form` para formulários não persistidos (ex.: filtros).
- Forms que dependem do usuário o recebem no `__init__`, passado por `get_form_kwargs()` da view, e filtram os querysets dos selects por ele.
- Validações entre campos ficam em `clean()`, com mensagens em português.
- Widgets:
  - Datas: `DateInput(attrs={'type': 'date'})`;
  - Valores: `NumberInput(attrs={'step': '0.01', 'min': '0.01'})`.

## Signals

- Ficam sempre em `signals.py` dentro da app correspondente.
- São registrados importando o módulo no `ready()` do `AppConfig`:

```python
class ProfilesConfig(AppConfig):
    name = 'profiles'
    verbose_name = 'Perfis'

    def ready(self):
        from . import signals  # noqa: F401
```

## Admin

Todo model é registrado no admin com `list_display` e, quando fizer sentido, `list_filter`, `search_fields` e `list_select_related`.

## Segurança

- Proteção CSRF nativa em todos os formulários (`{% csrf_token %}`).
- Senhas com os hashers e validadores nativos do Django.
- Logout somente via POST.

## Testes

- Ficam para a sprint final, com `django.test.TestCase`, no `tests.py` de cada app.
- Cobrem models, forms e views das apps principais. Meta de cobertura: ≥ 80%.
- Resultado da Sprint 9 (29/10/2026): 179 testes passando e **99% de cobertura** (614 instruções, 2 não cobertas: `Transaction.__str__` e o ramo de e-mails duplicados por caixa em `UserManager.get_by_natural_key`).
- Para medir (o `coverage` não faz parte do `requirements.txt`; instale-o no venv):

  ```bash
  pip install coverage
  coverage run --source=. --omit=".venv/*,*/migrations/*,*/tests.py,manage.py,core/asgi.py,core/wsgi.py" manage.py test
  coverage report
  ```

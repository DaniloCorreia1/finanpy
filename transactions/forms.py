from django import forms
from django.utils import timezone

from accounts.models import Account
from categories.models import Category

from .models import Transaction

DATE_WIDGET_FORMAT = '%Y-%m-%d'


def grouped_category_choices(categories, empty_label):
    """Agrupa as categorias em optgroups "Entradas" e "Saídas"."""
    groups = {Category.INCOME: [], Category.EXPENSE: []}
    for category in categories:
        groups[category.category_type].append((category.pk, category.name))
    choices = [('', empty_label)]
    for label, category_type in [
        ('Entradas', Category.INCOME),
        ('Saídas', Category.EXPENSE),
    ]:
        if groups[category_type]:
            choices.append((label, groups[category_type]))
    return choices


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'transaction_type', 'description', 'amount', 'date', 'account',
            'category',
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'date': forms.DateInput(
                attrs={'type': 'date'}, format=DATE_WIDGET_FORMAT
            ),
        }
        error_messages = {
            'amount': {'min_value': 'O valor deve ser maior que zero.'},
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].choices = [
            ('', 'Selecione'),
            *Category.TYPE_CHOICES,
        ]
        if not self.instance.pk:
            self.fields['date'].initial = timezone.localdate()

        account_field = self.fields['account']
        account_field.queryset = Account.objects.filter(user=self.user)
        account_field.empty_label = 'Selecione'

        # As choices agrupadas só alteram a renderização do select; a
        # validação continua sendo feita pelo queryset do ModelChoiceField.
        category_field = self.fields['category']
        category_field.queryset = Category.objects.filter(user=self.user)
        category_field.choices = grouped_category_choices(
            category_field.queryset, 'Selecione'
        )

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        category = cleaned_data.get('category')
        if (
            transaction_type and category
            and category.category_type != transaction_type
        ):
            self.add_error(
                'category', 'A categoria deve ser do mesmo tipo da transação.'
            )
        return cleaned_data


class TransactionFilterForm(forms.Form):
    transaction_type = forms.ChoiceField(
        label='Tipo',
        required=False,
        choices=[('', 'Todos'), *Category.TYPE_CHOICES],
    )
    account = forms.ModelChoiceField(
        label='Conta',
        required=False,
        queryset=Account.objects.none(),
        empty_label='Todas',
    )
    category = forms.ModelChoiceField(
        label='Categoria',
        required=False,
        queryset=Category.objects.none(),
        empty_label='Todas',
    )
    start_date = forms.DateField(
        label='Data inicial',
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date'}, format=DATE_WIDGET_FORMAT
        ),
    )
    end_date = forms.DateField(
        label='Data final',
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date'}, format=DATE_WIDGET_FORMAT
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.filter(
            user=self.user
        )
        self.fields['category'].queryset = Category.objects.filter(
            user=self.user
        )

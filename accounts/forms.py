from django import forms

from .models import Account


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'bank', 'account_type', 'initial_balance']
        widgets = {
            'initial_balance': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account_type'].choices = [
            ('', 'Selecione'),
            *Account.TYPE_CHOICES,
        ]

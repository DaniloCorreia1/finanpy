from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].widget.attrs.pop('autofocus', None)
        self.fields['first_name'].widget.attrs['autofocus'] = True
        self.fields['password1'].label = 'Senha'
        self.fields['password2'].label = 'Confirmar senha'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'Já existe um usuário com este e-mail.', code='unique'
            )
        return email


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'autofocus': True}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'E-mail ou senha inválidos.',
    }

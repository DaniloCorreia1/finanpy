from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import EmailAuthenticationForm, SignUpForm


class SignUpView(SuccessMessageMixin, CreateView):
    form_class = SignUpForm
    template_name = 'users/signup.html'
    success_url = reverse_lazy('dashboard')
    success_message = 'Conta criada com sucesso. Bem-vindo(a) ao Finanpy!'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class UserLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

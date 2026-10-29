from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import (
    DecimalField, F, ProtectedError, Q, Sum, Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from categories.models import Category
from core.mixins import UserQuerySetMixin

from .forms import AccountForm
from .models import Account


class AccountListView(LoginRequiredMixin, UserQuerySetMixin, ListView):
    model = Account
    template_name = 'accounts/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        money = DecimalField(max_digits=12, decimal_places=2)
        zero = Value(Decimal('0'), output_field=money)
        income = Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(transactions__transaction_type=Category.INCOME),
            ),
            zero,
            output_field=money,
        )
        expense = Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(transactions__transaction_type=Category.EXPENSE),
            ),
            zero,
            output_field=money,
        )
        return super().get_queryset().annotate(
            balance=F('initial_balance') + income - expense
        )


class AccountCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('accounts:list')
    success_message = 'Conta criada com sucesso.'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AccountUpdateView(
    LoginRequiredMixin, UserQuerySetMixin, SuccessMessageMixin, UpdateView
):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('accounts:list')
    success_message = 'Conta atualizada com sucesso.'


class AccountDeleteView(LoginRequiredMixin, UserQuerySetMixin, DeleteView):
    model = Account
    template_name = 'accounts/account_confirm_delete.html'
    success_url = reverse_lazy('accounts:list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Esta conta possui transações e não pode ser excluída.',
            )
            return redirect(self.success_url)
        messages.success(self.request, 'Conta excluída com sucesso.')
        return response

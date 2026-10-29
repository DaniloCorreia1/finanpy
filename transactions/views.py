from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import UserQuerySetMixin

from .forms import TransactionFilterForm, TransactionForm
from .models import Transaction


class TransactionListView(LoginRequiredMixin, UserQuerySetMixin, ListView):
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'account', 'category'
        )
        self.filter_form = TransactionFilterForm(
            self.request.GET or None, user=self.request.user
        )
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data['transaction_type']:
                queryset = queryset.filter(
                    transaction_type=data['transaction_type']
                )
            if data['account']:
                queryset = queryset.filter(account=data['account'])
            if data['category']:
                queryset = queryset.filter(category=data['category'])
            if data['start_date']:
                queryset = queryset.filter(date__gte=data['start_date'])
            if data['end_date']:
                queryset = queryset.filter(date__lte=data['end_date'])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        return context


class TransactionFormMixin:
    """Repassa o usuário ao TransactionForm e informa se há contas e
    categorias cadastradas para orientar o usuário no template."""

    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transactions:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['has_accounts'] = user.accounts.exists()
        context['has_categories'] = user.categories.exists()
        return context


class TransactionCreateView(
    LoginRequiredMixin, TransactionFormMixin, SuccessMessageMixin,
    CreateView,
):
    success_message = 'Transação registrada com sucesso.'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TransactionUpdateView(
    LoginRequiredMixin, UserQuerySetMixin, TransactionFormMixin,
    SuccessMessageMixin, UpdateView,
):
    success_message = 'Transação atualizada com sucesso.'


class TransactionDeleteView(
    LoginRequiredMixin, UserQuerySetMixin, DeleteView
):
    model = Transaction
    template_name = 'transactions/transaction_confirm_delete.html'
    success_url = reverse_lazy('transactions:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Transação excluída com sucesso.')
        return response

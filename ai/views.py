from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import redirect
from django.views import View

from .services import GenerationResult, generate_insight_for_user

SUCCESS_MESSAGE = 'Análise gerada com sucesso.'
INSUFFICIENT_DATA_MESSAGE = (
    'Ainda não há dados suficientes para gerar uma análise. Registre ao '
    'menos {min_transactions} transações nos últimos 3 meses.'
)
COOLDOWN_MESSAGE = (
    'Você gerou uma análise recentemente. Aguarde alguns minutos para gerar '
    'outra.'
)
FAILURE_MESSAGE = (
    'Não foi possível gerar a análise agora. Tente novamente mais tarde.'
)


def cooldown_cache_key(user_id):
    return f'ai:generate:{user_id}'


class GenerateInsightView(LoginRequiredMixin, View):
    """Synchronous on-demand generation for ``request.user`` (POST only)."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        if not settings.OPENAI_API_KEY:
            messages.error(request, FAILURE_MESSAGE)
            return redirect('dashboard')

        # Failed attempts also count, to avoid repeated cost.
        added = cache.add(
            cooldown_cache_key(request.user.pk),
            True,
            timeout=settings.AI_MANUAL_COOLDOWN_MINUTES * 60,
        )
        if not added:
            messages.warning(request, COOLDOWN_MESSAGE)
            return redirect('dashboard')

        result = generate_insight_for_user(request.user)
        if result.status == GenerationResult.COMPLETED:
            messages.success(request, SUCCESS_MESSAGE)
        elif result.status in (
            GenerationResult.INSUFFICIENT_DATA, GenerationResult.UNCHANGED,
        ):
            messages.warning(request, INSUFFICIENT_DATA_MESSAGE.format(
                min_transactions=settings.AI_MIN_TRANSACTIONS,
            ))
        else:
            messages.error(request, FAILURE_MESSAGE)
        return redirect('dashboard')

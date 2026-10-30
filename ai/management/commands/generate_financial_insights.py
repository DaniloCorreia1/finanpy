from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ai.services import GenerationResult, generate_insight_for_user


class Command(BaseCommand):
    help = (
        'Gera a análise financeira com IA de todos os usuários ativos ou de '
        'um único usuário (--user).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            dest='email',
            metavar='E-MAIL',
            help='Gera a análise somente para o usuário com este e-mail.',
        )

    def handle(self, *args, **options):
        if not settings.OPENAI_API_KEY:
            raise CommandError(
                'OPENAI_API_KEY não configurada. Defina a variável de '
                'ambiente para gerar as análises.'
            )

        users = get_user_model().objects.filter(is_active=True)
        email = options.get('email')
        if email:
            users = users.filter(email__iexact=email.strip())
            if not users.exists():
                raise CommandError(
                    'Nenhum usuário ativo encontrado com o e-mail informado.'
                )

        counters = {
            GenerationResult.COMPLETED: 0,
            GenerationResult.INSUFFICIENT_DATA: 0,
            GenerationResult.UNCHANGED: 0,
            GenerationResult.FAILED: 0,
        }
        failed_ids = []
        for user in users.order_by('pk').iterator():
            # The service never raises: a failure does not stop the others.
            result = generate_insight_for_user(user)
            counters[result.status] += 1
            if result.status == GenerationResult.FAILED:
                failed_ids.append(str(user.pk))

        self.stdout.write(
            'Resumo: '
            f'{counters[GenerationResult.COMPLETED]} gerada(s), '
            f'{counters[GenerationResult.INSUFFICIENT_DATA]} com dados '
            'insuficientes, '
            f'{counters[GenerationResult.UNCHANGED]} sem mudança, '
            f'{counters[GenerationResult.FAILED]} falha(s).'
        )
        if failed_ids:
            self.stderr.write(
                'Falha nos usuários de id: ' + ', '.join(failed_ids) + '.'
            )

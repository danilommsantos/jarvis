from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Sincroniza o progress.json do GitHub com os campos lido/data_leitura no banco'

    def handle(self, *args, **options):
        from django.conf import settings
        from biblioteca.services import github_sync

        if not getattr(settings, 'GITHUB_TOKEN', None):
            raise CommandError('GITHUB_TOKEN não configurado. Verifique o .env.')
        if not getattr(settings, 'GITHUB_REPO', None):
            raise CommandError('GITHUB_REPO não configurado. Verifique o .env.')

        self.stdout.write('Sincronizando status de leitura do GitHub...')

        resultado = github_sync.sincronizar()

        self.stdout.write(
            self.style.SUCCESS(f'{resultado["atualizados"]} documento(s) atualizado(s).')
        )
        if resultado.get('erros'):
            self.stdout.write(self.style.WARNING(f'Erros:\n{resultado["erros"]}'))

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Publica documentos não publicados no GitHub e regenera mkdocs.yml'

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Republica todos os documentos, mesmo os já publicados.',
        )
        parser.add_argument(
            '--categoria',
            type=str,
            help='Publica somente documentos de uma categoria (slug).',
        )

    def handle(self, *args, **options):
        from django.conf import settings
        from biblioteca.models import Documento
        from biblioteca.services import github_publisher

        if not getattr(settings, 'GITHUB_TOKEN', None):
            raise CommandError('GITHUB_TOKEN não configurado. Verifique o .env.')
        if not getattr(settings, 'GITHUB_REPO', None):
            raise CommandError('GITHUB_REPO não configurado. Verifique o .env.')

        qs = Documento.objects.select_related('categoria')

        if not options['todos']:
            qs = qs.filter(publicado_github=False)

        if options['categoria']:
            qs = qs.filter(categoria__slug=options['categoria'])

        documentos = list(qs)

        if not documentos:
            self.stdout.write(self.style.WARNING('Nenhum documento para publicar.'))
            return

        self.stdout.write(f'Publicando {len(documentos)} documento(s) no GitHub...')

        resultado = github_publisher.publicar_documentos(documentos)

        self.stdout.write(
            self.style.SUCCESS(f'{resultado["publicados"]} documento(s) publicado(s) com sucesso.')
        )
        if resultado.get('erros'):
            self.stdout.write(self.style.WARNING(f'Erros:\n{resultado["erros"]}'))

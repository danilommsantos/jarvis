from django.core.management.base import BaseCommand
from processos.models import Processo


class Command(BaseCommand):
    help = 'Recalcula o campo "impedido" em todos os processos com base nos advogados marcados com gera_impedimento=True.'

    def handle(self, *args, **options):
        processos = Processo.objects.prefetch_related('advogados').all()
        total = processos.count()
        atualizados = 0

        for processo in processos:
            novo_valor = processo.advogados.filter(gera_impedimento=True).exists()
            if processo.impedido != novo_valor:
                processo.impedido = novo_valor
                processo.save(update_fields=['impedido'])
                atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(f'{atualizados} processo(s) atualizado(s) de {total} total.')
        )

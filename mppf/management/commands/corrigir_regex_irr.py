"""
Management command para corrigir os padrões regex dos temas de IRR.

Problema: expressões terminadas em \\b após caractere não-palavra (ex: ponto)
nunca casam. Ex: \\bRECEBO\\s+o\\s+recurso\\.\\b → o \\b após \\. nunca funciona.

Correção: substituir o \\b final por (?!\\d|\\.\\d) para rejeitar:
  - números seguidos de outro dígito  (ex: "1.118" não é Tema 1)
  - números seguidos de ponto+dígito  (ex: "2.1"  não é Tema 2)

Uso:
  # Modo simulação (padrão) — só mostra o que mudaria:
  python manage.py corrigir_regex_irr

  # Aplica as alterações de fato:
  python manage.py corrigir_regex_irr --aplicar
"""

import re
from django.core.management.base import BaseCommand
from mppf.models import ExpressaoMateria

# Assinatura que identifica os regex de tema IRR
PADRAO_IRR = re.compile(r'temas\?|teses\?', re.IGNORECASE)

# O sufixo problemático que queremos corrigir
SUFIXO_ANTIGO = r'\b'
SUFIXO_NOVO   = r'(?!\d|\.\d)'


def corrigir_padrao(texto):
    """
    Substitui o \\b final do padrão pelo lookahead negativo correto.
    Retorna (novo_texto, foi_alterado).
    """
    if texto.endswith(SUFIXO_ANTIGO):
        novo = texto[:-len(SUFIXO_ANTIGO)] + SUFIXO_NOVO
        return novo, True
    return texto, False


class Command(BaseCommand):
    help = 'Corrige o \\b final dos regex de temas IRR para (?!\\d|\\.\\d)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--aplicar',
            action='store_true',
            help='Aplica as alterações no banco. Sem esta flag roda em modo simulação.',
        )

    def handle(self, *args, **options):
        aplicar = options['aplicar']
        modo = 'APLICANDO' if aplicar else 'SIMULAÇÃO'
        self.stdout.write(self.style.WARNING(f'\n=== Modo: {modo} ===\n'))

        candidatas = ExpressaoMateria.objects.filter(usar_regex=True)
        irr = [e for e in candidatas if PADRAO_IRR.search(e.texto)]

        if not irr:
            self.stdout.write(self.style.NOTICE('Nenhuma expressão IRR encontrada.'))
            return

        self.stdout.write(f'Expressões IRR encontradas: {len(irr)}\n')

        alteradas = 0
        sem_alteracao = 0

        for exp in irr:
            novo_texto, mudou = corrigir_padrao(exp.texto)

            if mudou:
                alteradas += 1
                self.stdout.write(
                    f'\n[#{exp.id}] Matéria: {exp.materia.nome}\n'
                    f'  ANTES:  {exp.texto}\n'
                    f'  DEPOIS: {novo_texto}\n'
                )
                if aplicar:
                    exp.texto = novo_texto
                    exp.save()
            else:
                sem_alteracao += 1
                self.stdout.write(
                    self.style.NOTICE(
                        f'[#{exp.id}] Sem alteração ({exp.materia.nome}): {exp.texto}'
                    )
                )

        self.stdout.write('\n' + '─' * 60)
        self.stdout.write(f'Alteradas:      {alteradas}')
        self.stdout.write(f'Sem alteração:  {sem_alteracao}')

        if not aplicar:
            self.stdout.write(self.style.WARNING(
                '\nSimulação concluída. Para aplicar, rode com --aplicar'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nAlterações salvas no banco.'))

from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Processo


@receiver(m2m_changed, sender=Processo.advogados.through)
def atualizar_impedimento(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.impedido = instance.advogados.filter(gera_impedimento=True).exists()
        instance.save(update_fields=['impedido'])

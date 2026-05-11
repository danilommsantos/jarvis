from django.db import models

class BaseModel(models.Model):
    """
    Modelo base abstrato para todo o projeto J.A.R.V.I.S.
    Todos os outros modelos devem herdar deste para ganhar 
    automaticamente os campos de auditoria.
    """
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

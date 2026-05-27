from django.apps import AppConfig


class ProcessosConfig(AppConfig):
    name = 'processos'

    def ready(self):
        import processos.signals  # noqa: F401

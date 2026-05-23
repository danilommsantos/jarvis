import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='Slug')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
            ],
            options={
                'verbose_name': 'Categoria',
                'verbose_name_plural': 'Categorias',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Documento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='Título')),
                ('slug', models.SlugField(max_length=255, unique=True, verbose_name='Slug')),
                ('conteudo', models.TextField(verbose_name='Conteúdo')),
                ('formato', models.CharField(
                    choices=[('md', 'Markdown'), ('html', 'HTML')],
                    default='md',
                    max_length=4,
                    verbose_name='Formato',
                )),
                ('ordem', models.IntegerField(default=0, verbose_name='Ordem')),
                ('prioridade', models.IntegerField(
                    default=0,
                    help_text='0 = normal, 1 = alta, 2 = urgente',
                    verbose_name='Prioridade',
                )),
                ('lido', models.BooleanField(default=False, verbose_name='Lido')),
                ('data_leitura', models.DateTimeField(blank=True, null=True, verbose_name='Data de Leitura')),
                ('publicado_github', models.BooleanField(default=False, verbose_name='Publicado no GitHub')),
                ('github_path', models.CharField(blank=True, max_length=500, verbose_name='Path no GitHub')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('categoria', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documentos',
                    to='biblioteca.categoria',
                    verbose_name='Categoria',
                )),
            ],
            options={
                'verbose_name': 'Documento',
                'verbose_name_plural': 'Documentos',
                'ordering': ['categoria', 'ordem', 'titulo'],
            },
        ),
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateTimeField(auto_now_add=True, verbose_name='Data')),
                ('tipo', models.CharField(
                    choices=[('publicar', 'Publicação no GitHub'), ('sincronizar', 'Sincronização de Leituras')],
                    max_length=15,
                    verbose_name='Tipo',
                )),
                ('documentos_afetados', models.IntegerField(default=0, verbose_name='Documentos Afetados')),
                ('erros', models.TextField(blank=True, verbose_name='Erros')),
                ('detalhes', models.TextField(blank=True, verbose_name='Detalhes')),
            ],
            options={
                'verbose_name': 'Log de Sincronização',
                'verbose_name_plural': 'Logs de Sincronização',
                'ordering': ['-data'],
            },
        ),
    ]

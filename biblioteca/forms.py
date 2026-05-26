from django import forms
from django.utils import timezone
from .models import Documento


class DocumentoForm(forms.ModelForm):
    data_inclusao = forms.DateField(
        label='Data de Inclusão',
        input_formats=['%d/%m/%Y', '%Y-%m-%d'],
        widget=forms.DateInput(
            format='%d/%m/%Y',
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'dd/mm/aaaa',
            },
        ),
    )

    class Meta:
        model = Documento
        fields = [
            'titulo', 'categoria', 'formato', 'conteudo',
            'ordem', 'prioridade', 'data_inclusao',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Título do documento',
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select form-select-sm',
            }),
            'formato': forms.Select(attrs={
                'class': 'form-select form-select-sm',
            }),
            'conteudo': forms.Textarea(attrs={
                'class': 'form-control form-control-sm font-monospace',
                'rows': 18,
                'placeholder': 'Cole o conteúdo aqui (Markdown ou HTML)...',
            }),
            'ordem': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 0,
            }),
            'prioridade': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 0,
                'max': 2,
            }),
        }
        labels = {
            'titulo': 'Título',
            'categoria': 'Categoria',
            'formato': 'Formato',
            'conteudo': 'Conteúdo',
            'ordem': 'Ordem',
            'prioridade': 'Prioridade (0=normal, 1=alta, 2=urgente)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'data_inclusao' not in (self.initial or {}):
            self.fields['data_inclusao'].initial = timezone.localdate()

from django import forms
from .models import ListaProcessos, ObservacaoRevisao

class AdicionarProcessosLoteForm(forms.Form):
    processos_numeros = forms.CharField(
        label='Números dos Processos',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 40})
    )
    
    lista_origem = forms.ModelChoiceField(
        queryset=ListaProcessos.objects.none(),
        required=False,
        label='Adicionar a uma Lista Existente',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    nome_nova_lista = forms.CharField(
        required=False,
        label='OU Criar uma Nova Lista (Digite o nome)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lote de Urgências'})
    )
    
    # CAMPO inclusao_tardia APAGADO DAQUI!

    def __init__(self, *args, **kwargs):
        pauta_atual = kwargs.pop('pauta', None)
        super().__init__(*args, **kwargs)
        if pauta_atual:
            self.fields['lista_origem'].queryset = ListaProcessos.objects.filter(pauta=pauta_atual)
            
            
class ObservacaoRevisaoForm(forms.ModelForm):
    class Meta:
        model = ObservacaoRevisao
        fields = ['tema', 'observacao', 'duvida']
        widgets = {
            'tema': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Contradição na sentença'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Descreva a sua observação ou dúvida...'
            }),
            'duvida': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        

class MarcarRRProvidoForm(forms.Form):
    processos_rr_providos = forms.CharField(
        label='Processos com RR Provido (Um por linha)',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 40, 
            'placeholder': 'Cole aqui os números dos processos que devem ser marcados como rr_provido = True'
        })
    )
from django import forms
from .models import Cliente, ItemOrdemServico, Ativo, NotaInterna, OrdemServico
from inventory.models import Produto


class CampoData(forms.DateInput):
    input_type = 'date'


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'cpf_cnpj', 'telefone', 'email', 'endereco']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control mask-doc'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AtivoForm(forms.ModelForm):
    class Meta:
        model = Ativo
        fields = ['cliente', 'marca', 'modelo', 'ano', 'placa', 'cor', 'km', 'chassi']
        labels = {
            'placa': 'Identificação',
            'km': 'Referência numérica',
            'chassi': 'Código interno',
            'ano': 'Ano/versão',
        }
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'placa': forms.TextInput(attrs={'class': 'form-control'}),
            'cor': forms.TextInput(attrs={'class': 'form-control'}),
            'km': forms.NumberInput(attrs={'class': 'form-control'}),
            'chassi': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa).order_by('nome')


class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ['numero', 'cliente', 'ativo', 'data_abertura', 'previsao_entrega', 'queixa', 'diagnostico', 'observacoes', 'valor_mao_de_obra', 'valor_desconto', 'status']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.Select(attrs={'class': 'form-select'}),
            'data_abertura': CampoData(attrs={'class': 'form-control'}),
            'previsao_entrega': CampoData(attrs={'class': 'form-control'}),
            'queixa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valor_mao_de_obra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa).order_by('nome')
            self.fields['ativo'].queryset = Ativo.objects.filter(empresa=empresa).select_related('cliente').order_by('marca', 'modelo')


class ItemOrdemServicoForm(forms.ModelForm):
    class Meta:
        model = ItemOrdemServico
        fields = ['tipo_item', 'produto', 'descricao', 'quantidade', 'valor_unitario']
        widgets = {
            'tipo_item': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['produto'].queryset = Produto.objects.filter(empresa=empresa, ativo=True).order_by('nome')


class NotaInternaForm(forms.ModelForm):
    class Meta:
        model = NotaInterna
        fields = ['numero_nota', 'data_emissao', 'observacoes']
        widgets = {
            'numero_nota': forms.TextInput(attrs={'class': 'form-control'}),
            'data_emissao': CampoData(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

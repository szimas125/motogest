from django import forms
from .models import Categoria, MovimentacaoEstoque, Produto


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome']
        widgets = {'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: Categoria principal'})}


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'categoria',
            'nome',
            'sku',
            'marca',
            'unidade',
            'preco_custo',
            'preco_venda',
            'estoque_atual',
            'estoque_minimo',
            'ativo',
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estoque_atual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'estoque_atual': 'Estoque inicial',
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa).order_by('nome')
        if self.instance and self.instance.pk:
            self.fields['estoque_atual'].label = 'Estoque disponível'
            self.fields['estoque_atual'].help_text = (
                'Atenção: alterar esse valor aqui ajusta o saldo atual sem registrar uma movimentação histórica.'
            )
        else:
            self.fields['estoque_atual'].help_text = 'Quantidade inicial do produto no momento do cadastro.'


class MovimentacaoEstoqueForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoEstoque
        fields = ['produto', 'tipo_movimentacao', 'quantidade', 'valor_unitario', 'motivo', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'tipo_movimentacao': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['produto'].queryset = Produto.objects.filter(empresa=empresa, ativo=True).order_by('nome')

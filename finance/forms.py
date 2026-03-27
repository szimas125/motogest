from django import forms
from django.utils import timezone
from .models import ContaReceber, LancamentoCaixa


class ContaReceberForm(forms.ModelForm):
    class Meta:
        model = ContaReceber
        fields = ['ordem_servico', 'descricao', 'valor', 'vencimento', 'status', 'forma_pagamento', 'recebido_em', 'observacoes']
        widgets = {
            'ordem_servico': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'recebido_em': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ordem_servico'].required = False
        self.fields['recebido_em'].required = False
        if empresa:
            self.fields['ordem_servico'].queryset = empresa.ordens_servico.order_by('-criado_em')
        if not self.instance.pk:
            self.fields['vencimento'].initial = timezone.localdate()


class LancamentoCaixaForm(forms.ModelForm):
    class Meta:
        model = LancamentoCaixa
        fields = ['conta_receber', 'tipo', 'descricao', 'valor', 'data_lancamento', 'categoria', 'observacoes']
        widgets = {
            'conta_receber': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_lancamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conta_receber'].required = False
        if empresa:
            self.fields['conta_receber'].queryset = empresa.contas_receber.order_by('-criado_em')
        if not self.instance.pk:
            self.fields['data_lancamento'].initial = timezone.localdate()

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import (
    Assinatura,
    ConfiguracaoEmpresa,
    Empresa,
    Plano,
    VinculoUsuarioEmpresa,
)

User = get_user_model()


class OnboardingForm(forms.Form):
    nome_responsavel = forms.CharField(label='Nome do responsável', widget=forms.TextInput(attrs={'class': 'form-control'}))
    nome_empresa = forms.CharField(label='Nome da empresa', widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefone = forms.CharField(label='Telefone', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    username = forms.CharField(label='Usuário', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    plano = forms.ModelChoiceField(
        label='Plano',
        queryset=Plano.objects.filter(ativo=True, exibir_no_site=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Este usuário já existe.')
        return username


class TeamUserForm(forms.Form):
    nome = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    perfil = forms.ChoiceField(choices=VinculoUsuarioEmpresa.PERFIS, widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Este usuário já existe.')
        return username


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'nome_fantasia', 'cnpj', 'telefone', 'email']


class ConfiguracaoEmpresaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoEmpresa
        fields = ['logo_url', 'cor_primaria']


class TeamMembershipForm(forms.ModelForm):
    class Meta:
        model = VinculoUsuarioEmpresa
        fields = ['perfil', 'ativo']


class BillingCardTokenForm(forms.Form):
    card_token = forms.CharField(widget=forms.HiddenInput())
    payment_method_id = forms.CharField(required=False, widget=forms.HiddenInput())
    issuer_id = forms.CharField(required=False, widget=forms.HiddenInput())
    installments = forms.IntegerField(required=False, widget=forms.HiddenInput())

    # 🔥 NOVOS CAMPOS (IMPORTANTE)
    card_last_four = forms.CharField(required=False, max_length=4, widget=forms.HiddenInput())
    card_brand = forms.CharField(required=False, max_length=40, widget=forms.HiddenInput())


# ✅ CORREÇÃO DO ERRO DO ADMIN (ESSA É A PARTE QUE QUEBRAVA TUDO)
class AssinaturaAdminForm(forms.ModelForm):
    class Meta:
        model = Assinatura
        fields = [
            'empresa',
            'plano',
            'status',
            'vencimento',
            'mercado_pago_preapproval_id',
            'mercado_pago_status',
            'cartao_ultimos_digitos',
            'cartao_bandeira',
            'cartao_cadastrado_em',
        ]

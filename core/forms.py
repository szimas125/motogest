from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Assinatura, ConfiguracaoEmpresa, Empresa, Plano, VinculoUsuarioEmpresa

User = get_user_model()


class OnboardingForm(forms.Form):
    nome_responsavel = forms.CharField(label='Nome do responsável', widget=forms.TextInput(attrs={'class': 'form-control'}))
    nome_empresa = forms.CharField(label='Nome da empresa', widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefone = forms.CharField(label='Telefone', required=False, widget=forms.TextInput(attrs={'class': 'form-control mask-phone'}))
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    username = forms.CharField(label='Usuário de acesso', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    plano = forms.ModelChoiceField(label='Plano inicial', queryset=Plano.objects.filter(ativo=True, exibir_no_site=True).order_by('ordem', 'preco_mensal'), widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Este usuário já existe.')
        return username


class TeamUserForm(forms.Form):
    nome = forms.CharField(label='Nome', widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(label='Usuário', widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='E-mail', required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    perfil = forms.ChoiceField(label='Perfil', choices=VinculoUsuarioEmpresa.PERFIS, widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Este usuário já existe.')
        return username


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'nome_fantasia', 'cnpj', 'telefone', 'email', 'endereco', 'cidade', 'estado']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control mask-doc'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'maxlength': '2'}),
        }


class ConfiguracaoEmpresaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoEmpresa
        fields = ['logo_url', 'cor_primaria', 'rodape_nota']
        widgets = {
            'logo_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'cor_primaria': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'rodape_nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class TeamMembershipForm(forms.ModelForm):
    class Meta:
        model = VinculoUsuarioEmpresa
        fields = ['perfil', 'ativo']
        widgets = {
            'perfil': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PlanoAdminForm(forms.ModelForm):
    class Meta:
        model = Plano
        fields = ['nome', 'slug', 'descricao', 'preco_mensal', 'periodo_teste_dias', 'limite_usuarios', 'limite_produtos', 'limite_ordens_mes', 'ativo', 'exibir_no_site', 'ordem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preco_mensal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'periodo_teste_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_usuarios': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_produtos': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_ordens_mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exibir_no_site': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class BillingCardTokenForm(forms.Form):
    card_token = forms.CharField(widget=forms.HiddenInput())
    payment_method_id = forms.CharField(required=False, widget=forms.HiddenInput())
    issuer_id = forms.CharField(required=False, widget=forms.HiddenInput())
    installments = forms.IntegerField(required=False, initial=1, widget=forms.HiddenInput())
    card_last_four = forms.CharField(required=False, max_length=4, widget=forms.HiddenInput())
    card_brand = forms.CharField(required=False, max_length=40, widget=forms.HiddenInput())


class EmpresaAdminCreateForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'slug', 'nome_fantasia', 'cnpj', 'telefone', 'email', 'endereco', 'cidade', 'estado', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control mask-doc'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'maxlength': '2'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

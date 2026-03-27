from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Plano(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    limite_usuarios = models.PositiveIntegerField(null=True, blank=True, help_text='Deixe em branco para ilimitado.')
    limite_ordens_mes = models.PositiveIntegerField(null=True, blank=True, help_text='Deixe em branco para ilimitado.')
    limite_produtos = models.PositiveIntegerField(null=True, blank=True, help_text='Deixe em branco para ilimitado.')
    periodo_teste_dias = models.PositiveIntegerField(default=7)
    destaque = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    exibir_no_site = models.BooleanField(default=True)
    descricao = models.TextField(blank=True)
    recursos = models.TextField(blank=True, help_text='Um recurso por linha.')
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordem', 'preco_mensal', 'nome']
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    @property
    def recursos_lista(self):
        linhas = [linha.strip() for linha in (self.recursos or '').splitlines() if linha.strip()]
        if linhas:
            return linhas
        itens = [
            'Controle de estoque e movimentações',
            'Clientes, ativos e ordens de serviço',
            'Impressão de documentos internos',
        ]
        if self.limite_usuarios:
            itens.insert(0, f'Até {self.limite_usuarios} usuário(s)')
        else:
            itens.insert(0, 'Usuários ilimitados')
        if self.limite_ordens_mes:
            itens.insert(1, f'Até {self.limite_ordens_mes} ordens de serviço por mês')
        else:
            itens.insert(1, 'Ordens de serviço ilimitadas')
        return itens

    def __str__(self):
        return self.nome


class Empresa(models.Model):
    nome = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    nome_fantasia = models.CharField(max_length=150, blank=True)
    cnpj = models.CharField(max_length=20, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nome_fantasia or self.nome


class Assinatura(models.Model):
    STATUS_CHOICES = (
        ('ATIVA', 'Ativa'),
        ('TESTE', 'Período de teste'),
        ('ATRASADA', 'Pagamento pendente'),
        ('CANCELADA', 'Cancelada'),
        ('BLOQUEADA', 'Bloqueada'),
    )
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='assinatura')
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name='assinaturas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TESTE')
    inicio = models.DateField(null=True, blank=True)
    vencimento = models.DateField(null=True, blank=True)
    proximo_plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True, related_name='upgrades_agendados')
    renovar_automaticamente = models.BooleanField(default=True)
    mercado_pago_preapproval_id = models.CharField(max_length=120, blank=True)
    mercado_pago_status = models.CharField(max_length=40, blank=True)
    cartao_ultimos_digitos = models.CharField(max_length=4, blank=True)
    cartao_bandeira = models.CharField(max_length=40, blank=True)
    cartao_cadastrado_em = models.DateTimeField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'


    @property
    def cartao_cadastrado(self):
        return bool(self.mercado_pago_preapproval_id)

    @property
    def em_periodo_teste(self):
        return self.status == 'TESTE'

    @property
    def esta_ativa_para_uso(self):
        hoje = timezone.localdate()
        if self.status in {'CANCELADA', 'BLOQUEADA'}:
            return False
        if self.vencimento and self.vencimento < hoje and self.status not in {'TESTE', 'ATIVA'}:
            return False
        return self.status in {'ATIVA', 'TESTE'} or (self.vencimento and self.vencimento >= hoje and self.status == 'ATRASADA')

    def iniciar_teste(self):
        hoje = timezone.localdate()
        self.status = 'TESTE'
        self.inicio = hoje
        self.vencimento = hoje + timedelta(days=self.plano.periodo_teste_dias)

    def ativar_plano(self):
        hoje = timezone.localdate()
        self.status = 'ATIVA'
        self.inicio = self.inicio or hoje
        self.vencimento = hoje + timedelta(days=30)

    def sincronizar_status(self):
        hoje = timezone.localdate()
        mudou = False
        if self.status == 'TESTE' and self.vencimento and self.vencimento < hoje:
            self.status = 'ATRASADA'
            mudou = True
        elif self.status == 'ATIVA' and self.vencimento and self.vencimento < hoje:
            self.status = 'ATRASADA'
            mudou = True
        elif self.status == 'ATRASADA' and self.vencimento and self.vencimento < hoje - timedelta(days=5):
            self.status = 'BLOQUEADA'
            mudou = True
        if mudou:
            self.save(update_fields=['status', 'atualizado_em'])
        return mudou

    def __str__(self):
        return f'{self.empresa} - {self.plano}'


class ConfiguracaoEmpresa(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='configuracao')
    rodape_nota = models.TextField(blank=True, default='Documento interno sem valor fiscal.')
    cor_primaria = models.CharField(max_length=20, default='#1d4ed8')
    logo_url = models.URLField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração da empresa'
        verbose_name_plural = 'Configurações das empresas'

    def __str__(self):
        return f'Configuração - {self.empresa}'


class VinculoUsuarioEmpresa(models.Model):
    PERFIS = (
        ('ADMIN', 'Administrador'),
        ('GERENTE', 'Gerente'),
        ('ATENDENTE', 'Atendente'),
        ('MECANICO', 'Operador'),
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vinculos_empresariais')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios_vinculados')
    perfil = models.CharField(max_length=20, choices=PERFIS, default='ADMIN')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'empresa')
        verbose_name = 'Vínculo do usuário com empresa'
        verbose_name_plural = 'Vínculos dos usuários com empresas'

    def __str__(self):
        return f'{self.usuario} - {self.empresa}'


class SolicitacaoPlano(models.Model):
    STATUS_CHOICES = (
        ('ABERTA', 'Aberta'),
        ('APROVADA', 'Aprovada'),
        ('CANCELADA', 'Cancelada'),
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='solicitacoes_plano')
    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE, related_name='solicitacoes')
    plano_atual = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name='solicitacoes_origem')
    plano_solicitado = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name='solicitacoes_destino')
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Solicitação de plano'
        verbose_name_plural = 'Solicitações de plano'

    def __str__(self):
        return f'{self.empresa} -> {self.plano_solicitado}'


class EventoAssinatura(models.Model):
    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE, related_name='eventos')
    origem = models.CharField(max_length=40, default='sistema')
    tipo = models.CharField(max_length=80)
    descricao = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Evento da assinatura'
        verbose_name_plural = 'Eventos da assinatura'

    def __str__(self):
        return f'{self.assinatura.empresa} - {self.tipo}'

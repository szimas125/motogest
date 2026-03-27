from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from core.models import Empresa
from workshop.models import OrdemServico


class ContaReceber(models.Model):
    STATUS_CHOICES = (
        ('ABERTA', 'Aberta'),
        ('PAGA', 'Paga'),
        ('ATRASADA', 'Atrasada'),
        ('CANCELADA', 'Cancelada'),
    )
    FORMA_PAGAMENTO = (
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'PIX'),
        ('CARTAO', 'Cartão'),
        ('BOLETO', 'Boleto'),
        ('TRANSFERENCIA', 'Transferência'),
        ('OUTRO', 'Outro'),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='contas_receber')
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.SET_NULL, null=True, blank=True, related_name='contas_receber')
    descricao = models.CharField(max_length=160)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vencimento = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO, blank=True)
    recebido_em = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['status', 'vencimento', '-criado_em']
        verbose_name = 'Conta a receber'
        verbose_name_plural = 'Contas a receber'

    def clean(self):
        if self.valor <= 0:
            raise ValidationError('O valor precisa ser maior que zero.')
        if self.ordem_servico_id and self.ordem_servico.empresa_id != self.empresa_id:
            raise ValidationError('A ordem de serviço precisa pertencer à mesma empresa.')

    def marcar_atrasada_se_necessario(self, hoje=None):
        from django.utils import timezone
        hoje = hoje or timezone.localdate()
        if self.status == 'ABERTA' and self.vencimento < hoje:
            self.status = 'ATRASADA'
            self.save(update_fields=['status'])
            return True
        return False

    def __str__(self):
        return self.descricao


class LancamentoCaixa(models.Model):
    TIPO_CHOICES = (
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='lancamentos_caixa')
    conta_receber = models.ForeignKey(ContaReceber, on_delete=models.SET_NULL, null=True, blank=True, related_name='lancamentos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=160)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    data_lancamento = models.DateField()
    categoria = models.CharField(max_length=80, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_lancamento', '-criado_em']
        verbose_name = 'Lançamento de caixa'
        verbose_name_plural = 'Lançamentos de caixa'

    def clean(self):
        if self.valor <= 0:
            raise ValidationError('O valor precisa ser maior que zero.')
        if self.conta_receber_id and self.conta_receber.empresa_id != self.empresa_id:
            raise ValidationError('A conta precisa pertencer à mesma empresa.')

    def __str__(self):
        return self.descricao

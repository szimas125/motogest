from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from core.models import Empresa
from inventory.models import Produto


class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='clientes')
    nome = models.CharField(max_length=150)
    cpf_cnpj = models.CharField(max_length=20, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.nome


class Ativo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ativos')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='ativos')
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=80)
    ano = models.PositiveIntegerField(null=True, blank=True)
    placa = models.CharField(max_length=10, blank=True)
    cor = models.CharField(max_length=30, blank=True)
    km = models.PositiveIntegerField(default=0)
    chassi = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['marca', 'modelo']
        verbose_name = 'Ativo'
        verbose_name_plural = 'Ativos'

    def clean(self):
        if self.cliente_id and self.cliente.empresa_id != self.empresa_id:
            raise ValidationError('O cliente precisa pertencer à mesma empresa.')

    def __str__(self):
        return f'{self.marca} {self.modelo} - {self.cliente.nome}'


class OrdemServico(models.Model):
    STATUS_CHOICES = (
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em andamento'),
        ('AGUARDANDO', 'Aguardando produto'),
        ('FINALIZADA', 'Finalizada'),
        ('ENTREGUE', 'Entregue'),
        ('CANCELADA', 'Cancelada'),
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ordens_servico')
    numero = models.CharField(max_length=20)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    ativo = models.ForeignKey(Ativo, on_delete=models.PROTECT)
    data_abertura = models.DateField()
    previsao_entrega = models.DateField(null=True, blank=True)
    queixa = models.TextField('Queixa do cliente')
    diagnostico = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    valor_mao_de_obra = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Ordem de serviço'
        verbose_name_plural = 'Ordens de serviço'
        unique_together = ('empresa', 'numero')

    def clean(self):
        if self.cliente_id and self.cliente.empresa_id != self.empresa_id:
            raise ValidationError('O cliente precisa pertencer à mesma empresa.')
        if self.ativo_id and self.ativo.empresa_id != self.empresa_id:
            raise ValidationError('Um ativo precisa pertencer à mesma empresa.')

    def __str__(self):
        return f'OS {self.numero} - {self.cliente.nome}'

    def recalcular_total(self):
        total_itens = sum(item.valor_total for item in self.itens.all())
        self.valor_total = (total_itens + self.valor_mao_de_obra) - self.valor_desconto
        self.save(update_fields=['valor_total'])


class ItemOrdemServico(models.Model):
    TIPOS = (
        ('PRODUTO', 'Produto'),
        ('SERVICO', 'Serviço'),
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='itens_ordem_servico')
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='itens')
    tipo_item = models.CharField(max_length=10, choices=TIPOS, default='PRODUTO')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, null=True, blank=True)
    descricao = models.CharField(max_length=150)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Item da ordem de serviço'
        verbose_name_plural = 'Itens da ordem de serviço'

    def clean(self):
        if self.quantidade <= 0:
            raise ValidationError('A quantidade deve ser maior que zero.')
        if self.ordem_servico_id and self.ordem_servico.empresa_id != self.empresa_id:
            raise ValidationError('A ordem de serviço precisa pertencer à mesma empresa.')
        if self.tipo_item == 'PRODUTO' and not self.produto:
            raise ValidationError('Selecione um produto para item do tipo produto.')
        if self.produto_id and self.produto.empresa_id != self.empresa_id:
            raise ValidationError('O produto precisa pertencer à mesma empresa.')
        if self.tipo_item == 'PRODUTO' and self.produto and self.quantidade > self.produto.estoque_atual:
            raise ValidationError('Estoque insuficiente para o produto informado.')

    def save(self, *args, **kwargs):
        self.full_clean()
        anterior = None
        if self.pk:
            anterior = ItemOrdemServico.objects.get(pk=self.pk)
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)
        if anterior and anterior.tipo_item == 'PRODUTO' and anterior.produto:
            anterior.produto.estoque_atual += anterior.quantidade
            anterior.produto.save(update_fields=['estoque_atual'])
        if self.tipo_item == 'PRODUTO' and self.produto:
            self.produto.estoque_atual -= self.quantidade
            self.produto.save(update_fields=['estoque_atual'])
        self.ordem_servico.recalcular_total()

    def delete(self, *args, **kwargs):
        if self.tipo_item == 'PRODUTO' and self.produto:
            self.produto.estoque_atual += self.quantidade
            self.produto.save(update_fields=['estoque_atual'])
        ordem = self.ordem_servico
        super().delete(*args, **kwargs)
        ordem.recalcular_total()

    def __str__(self):
        return self.descricao


class NotaInterna(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='notas_internas')
    ordem_servico = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='nota_interna')
    numero_nota = models.CharField(max_length=20)
    data_emissao = models.DateField()
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Nota interna'
        verbose_name_plural = 'Notas internas'
        unique_together = ('empresa', 'numero_nota')

    def clean(self):
        if self.ordem_servico_id and self.ordem_servico.empresa_id != self.empresa_id:
            raise ValidationError('A ordem de serviço precisa pertencer à mesma empresa.')

    def __str__(self):
        return f'Nota {self.numero_nota}'

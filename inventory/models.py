from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from core.models import Empresa


class Categoria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='categorias')
    nome = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        unique_together = ('empresa', 'nome')

    def __str__(self):
        return self.nome


class Produto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='produtos')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos')
    nome = models.CharField(max_length=150)
    sku = models.CharField(max_length=50)
    marca = models.CharField(max_length=80, blank=True)
    unidade = models.CharField(max_length=20, default='UN')
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    estoque_atual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        unique_together = ('empresa', 'sku')

    def __str__(self):
        return f'{self.nome} ({self.sku})'


class MovimentacaoEstoque(models.Model):
    TIPOS = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimentacoes_estoque')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='movimentacoes')
    tipo_movimentacao = models.CharField(max_length=10, choices=TIPOS)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    motivo = models.CharField(max_length=150)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Movimentação de estoque'
        verbose_name_plural = 'Movimentações de estoque'

    def clean(self):
        if self.produto_id and self.produto.empresa_id != self.empresa_id:
            raise ValidationError('O produto precisa pertencer à mesma empresa da movimentação.')
        if self.quantidade <= 0:
            raise ValidationError('A quantidade deve ser maior que zero.')
        if self.tipo_movimentacao == 'SAIDA' and self.produto_id:
            estoque_atual = self.produto.estoque_atual or 0
            if self.pk:
                anterior = MovimentacaoEstoque.objects.get(pk=self.pk)
                if anterior.tipo_movimentacao == 'ENTRADA':
                    estoque_atual -= anterior.quantidade
                else:
                    estoque_atual += anterior.quantidade
            if self.quantidade > estoque_atual:
                raise ValidationError('Estoque insuficiente para esta saída.')

    def save(self, *args, **kwargs):
        self.full_clean()
        anterior = None
        if self.pk:
            anterior = MovimentacaoEstoque.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        produto = self.produto
        if anterior:
            if anterior.tipo_movimentacao == 'ENTRADA':
                produto.estoque_atual -= anterior.quantidade
            else:
                produto.estoque_atual += anterior.quantidade
        if self.tipo_movimentacao == 'ENTRADA':
            produto.estoque_atual += self.quantidade
        else:
            produto.estoque_atual -= self.quantidade
        produto.save(update_fields=['estoque_atual'])

    def delete(self, *args, **kwargs):
        produto = self.produto
        if self.tipo_movimentacao == 'ENTRADA':
            produto.estoque_atual -= self.quantidade
        else:
            produto.estoque_atual += self.quantidade
        produto.save(update_fields=['estoque_atual'])
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.get_tipo_movimentacao_display()} - {self.produto.nome}'

from django.contrib import admin
from .models import Categoria, MovimentacaoEstoque, Produto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'criado_em')
    list_filter = ('empresa',)
    search_fields = ('nome', 'empresa__nome')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'categoria', 'sku', 'preco_venda', 'estoque_atual', 'ativo')
    list_filter = ('empresa', 'categoria', 'ativo')
    search_fields = ('nome', 'sku', 'marca')


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'empresa', 'tipo_movimentacao', 'quantidade', 'valor_unitario', 'criado_em')
    list_filter = ('empresa', 'tipo_movimentacao')
    search_fields = ('produto__nome', 'motivo')

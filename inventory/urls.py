from django.urls import path
from .views import (
    criar_categoria,
    criar_movimentacao,
    criar_produto,
    editar_categoria,
    editar_movimentacao,
    editar_produto,
    excluir_categoria,
    excluir_movimentacao,
    excluir_produto,
    lista_movimentacoes,
    lista_produtos,
)

urlpatterns = [
    path('', lista_produtos, name='product_list'),
    path('produtos/novo/', criar_produto, name='product_create'),
    path('produtos/<int:pk>/editar/', editar_produto, name='product_edit'),
    path('produtos/<int:pk>/excluir/', excluir_produto, name='product_delete'),
    path('categorias/nova/', criar_categoria, name='category_create'),
    path('categorias/<int:pk>/editar/', editar_categoria, name='category_edit'),
    path('categorias/<int:pk>/excluir/', excluir_categoria, name='category_delete'),
    path('movimentacoes/', lista_movimentacoes, name='movement_list'),
    path('movimentacoes/nova/', criar_movimentacao, name='movement_create'),
    path('movimentacoes/<int:pk>/editar/', editar_movimentacao, name='movement_edit'),
    path('movimentacoes/<int:pk>/excluir/', excluir_movimentacao, name='movement_delete'),
]

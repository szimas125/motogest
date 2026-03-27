from django.urls import path
from .views import (
    conta_create,
    conta_delete,
    conta_edit,
    financeiro_dashboard,
    gerar_conta_os,
    lancamento_create,
    marcar_conta_paga,
)

urlpatterns = [
    path('', financeiro_dashboard, name='finance_dashboard'),
    path('contas/nova/', conta_create, name='account_receivable_create'),
    path('contas/<int:pk>/editar/', conta_edit, name='account_receivable_edit'),
    path('contas/<int:pk>/excluir/', conta_delete, name='account_receivable_delete'),
    path('contas/<int:pk>/pagar/', marcar_conta_paga, name='account_receivable_pay'),
    path('ordens/<int:order_pk>/gerar-conta/', gerar_conta_os, name='generate_os_account'),
    path('lancamentos/novo/', lancamento_create, name='cash_entry_create'),
]

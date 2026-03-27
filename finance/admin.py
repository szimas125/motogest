from django.contrib import admin
from .models import ContaReceber, LancamentoCaixa


@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'empresa', 'valor', 'vencimento', 'status', 'forma_pagamento')
    list_filter = ('status', 'forma_pagamento', 'empresa')
    search_fields = ('descricao', 'ordem_servico__numero', 'empresa__nome')


@admin.register(LancamentoCaixa)
class LancamentoCaixaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'empresa', 'tipo', 'valor', 'data_lancamento', 'categoria')
    list_filter = ('tipo', 'empresa', 'categoria')
    search_fields = ('descricao', 'categoria', 'empresa__nome')

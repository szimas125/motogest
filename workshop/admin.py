from django.contrib import admin
from .models import Cliente, ItemOrdemServico, Ativo, NotaInterna, OrdemServico

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'telefone', 'email')
    list_filter = ('empresa',)
    search_fields = ('nome', 'cpf_cnpj', 'telefone')


@admin.register(Ativo)
class AtivoAdmin(admin.ModelAdmin):
    list_display = ('marca', 'modelo', 'placa', 'cliente', 'empresa', 'km')
    list_filter = ('empresa', 'marca')
    search_fields = ('marca', 'modelo', 'placa', 'cliente__nome')


class ItemOrdemServicoInline(admin.TabularInline):
    model = ItemOrdemServico
    extra = 0


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'empresa', 'cliente', 'ativo', 'status', 'valor_total', 'data_abertura')
    list_filter = ('empresa', 'status')
    search_fields = ('numero', 'cliente__nome', 'ativo__modelo')
    inlines = [ItemOrdemServicoInline]


@admin.register(NotaInterna)
class NotaInternaAdmin(admin.ModelAdmin):
    list_display = ('numero_nota', 'empresa', 'ordem_servico', 'data_emissao')
    list_filter = ('empresa',)


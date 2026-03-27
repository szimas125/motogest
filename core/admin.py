from django.contrib import admin
from .models import Assinatura, ConfiguracaoEmpresa, Empresa, Plano, SolicitacaoPlano, VinculoUsuarioEmpresa

admin.site.site_header = 'EzStock'
admin.site.site_title = 'EzStock Admin'
admin.site.index_title = 'Administração do EzStock'


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco_mensal', 'usuarios_formatado', 'ordens_formatado', 'produtos_formatado', 'ativo', 'destaque')
    list_filter = ('ativo', 'destaque', 'exibir_no_site')
    search_fields = ('nome', 'descricao')
    prepopulated_fields = {'slug': ('nome',)}

    @admin.display(description='Usuários')
    def usuarios_formatado(self, obj):
        return obj.limite_usuarios or 'Ilimitado'

    @admin.display(description='OS/mês')
    def ordens_formatado(self, obj):
        return obj.limite_ordens_mes or 'Ilimitado'

    @admin.display(description='Produtos')
    def produtos_formatado(self, obj):
        return obj.limite_produtos or 'Ilimitado'


class ConfiguracaoEmpresaInline(admin.StackedInline):
    model = ConfiguracaoEmpresa
    extra = 0


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'nome_fantasia', 'cnpj', 'telefone', 'ativa')
    search_fields = ('nome', 'nome_fantasia', 'cnpj')
    prepopulated_fields = {'slug': ('nome',)}
    inlines = [ConfiguracaoEmpresaInline]


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'plano', 'status', 'inicio', 'vencimento', 'renovar_automaticamente')
    list_filter = ('status', 'plano')
    search_fields = ('empresa__nome', 'empresa__nome_fantasia')


@admin.register(VinculoUsuarioEmpresa)
class VinculoUsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'perfil', 'ativo')
    list_filter = ('perfil', 'ativo', 'empresa')
    search_fields = ('usuario__username', 'empresa__nome', 'empresa__nome_fantasia')


@admin.register(SolicitacaoPlano)
class SolicitacaoPlanoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'plano_atual', 'plano_solicitado', 'status', 'criada_em')
    list_filter = ('status', 'plano_solicitado')
    search_fields = ('empresa__nome', 'empresa__nome_fantasia')

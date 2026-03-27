from django.shortcuts import redirect
from django.urls import reverse


class AssinaturaBloqueioMiddleware:
    ROTAS_LIBERADAS = {
        'home', 'login', 'logout', 'onboarding', 'plans',
        'billing_checkout', 'billing_status', 'billing_webhook',
        'password_reset', 'password_reset_done', 'password_reset_confirm',
        'password_reset_complete', 'selecionar_empresa',
        'saas_admin_dashboard', 'saas_admin_empresas',
        'saas_admin_empresa_create', 'saas_admin_empresa_edit',
        'saas_admin_assinaturas', 'saas_admin_usuarios',
        'saas_admin_planos', 'saas_admin_plano_create',
        'saas_admin_plano_edit', 'blocked_subscription',
    }
    PREFIXOS_LIBERADOS = ('/admin/', '/static/', '/media/')
    STATUS_PERMITIDOS = {'ATIVA', 'TESTE'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or '/'
        if any(path.startswith(prefix) for prefix in self.PREFIXOS_LIBERADOS):
            return self.get_response(request)

        if request.user.is_authenticated:
            try:
                match = request.resolver_match
                route_name = match.url_name if match else None
                if route_name in self.ROTAS_LIBERADAS:
                    return self.get_response(request)

                empresa = None
                empresa_id = request.session.get('empresa_id')
                if empresa_id and hasattr(request.user, 'vinculos_empresas'):
                    vinculo = request.user.vinculos_empresas.filter(
                        ativo=True, empresa_id=empresa_id
                    ).select_related('empresa').first()
                    if vinculo:
                        empresa = vinculo.empresa

                if not empresa and hasattr(request.user, 'vinculos_empresas'):
                    vinculo = request.user.vinculos_empresas.filter(
                        ativo=True
                    ).select_related('empresa').first()
                    if vinculo:
                        empresa = vinculo.empresa

                if empresa and hasattr(empresa, 'assinatura'):
                    assinatura = empresa.assinatura
                    if assinatura.status not in self.STATUS_PERMITIDOS:
                        return redirect(reverse('blocked_subscription'))
            except Exception:
                return self.get_response(request)

        return self.get_response(request)

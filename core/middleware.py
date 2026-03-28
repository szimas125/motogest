from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve, Resolver404

from .services import obter_empresa_atual, assinatura_cancelada


class AssinaturaCanceladaRestricaoMiddleware:
    """
    Quando a assinatura estiver cancelada, restringe o acesso do cliente
    apenas às telas de planos e assinatura até ele selecionar um novo plano.
    """

    ALLOWED_VIEW_NAMES = {
        'plans',
        'billing_status',
        'billing_checkout',
        'change_plan',
        'cancel_subscription',
        'selecionar_empresa',
        'blocked_subscription',
        'billing_webhook',
        'billing_webhook_no_slash',
        'logout',
        'login',
    }

    ALLOWED_PATH_PREFIXES = (
        '/admin/',
        '/painel-admin/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or '/'

        if any(path.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return self.get_response(request)

        try:
            match = resolve(path)
            view_name = match.view_name
        except Resolver404:
            view_name = None

        if view_name in self.ALLOWED_VIEW_NAMES:
            return self.get_response(request)

        empresa = obter_empresa_atual(request)
        if empresa and assinatura_cancelada(empresa):
            messages.warning(
                request,
                'Sua assinatura está cancelada. Escolha um novo plano para reativar a empresa.'
            )
            return redirect('plans')

        return self.get_response(request)

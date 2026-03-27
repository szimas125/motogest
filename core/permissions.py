from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from .services import obter_empresa_atual, obter_perfil_usuario_empresa


def require_company_profile(*allowed_profiles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            empresa = obter_empresa_atual(request)
            if not empresa:
                return redirect('selecionar_empresa')
            perfil = obter_perfil_usuario_empresa(request.user, empresa)
            if allowed_profiles and perfil not in allowed_profiles:
                messages.error(request, 'Seu perfil não possui permissão para acessar esta área.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

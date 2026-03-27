from .services import obter_empresa_atual, obter_perfil_usuario_empresa


def empresa_atual(request):
    empresa = obter_empresa_atual(request)
    perfil = obter_perfil_usuario_empresa(request.user, empresa) if empresa else None
    return {
        'empresa_atual': empresa,
        'perfil_usuario_empresa': perfil,
    }

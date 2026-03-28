from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from inventory.models import Produto
from workshop.models import OrdemServico

from .models import Assinatura, ConfiguracaoEmpresa, Empresa, SolicitacaoPlano, VinculoUsuarioEmpresa

User = get_user_model()


def obter_vinculos_usuario(usuario):
    if not usuario.is_authenticated:
        return VinculoUsuarioEmpresa.objects.none()
    return VinculoUsuarioEmpresa.objects.select_related(
        'empresa', 'empresa__assinatura', 'empresa__assinatura__plano'
    ).filter(
        usuario=usuario,
        ativo=True,
        empresa__ativa=True,
    )


def obter_empresa_atual(request):
    if not request.user.is_authenticated:
        return None

    empresa_id = request.session.get('empresa_id')
    vinculos = obter_vinculos_usuario(request.user)

    if empresa_id:
        vinculo = vinculos.filter(empresa_id=empresa_id).first()
        if vinculo:
            assinatura = getattr(vinculo.empresa, 'assinatura', None)
            if assinatura:
                assinatura.sincronizar_status()
            return vinculo.empresa

    primeiro = vinculos.first()
    if primeiro:
        request.session['empresa_id'] = primeiro.empresa_id
        assinatura = getattr(primeiro.empresa, 'assinatura', None)
        if assinatura:
            assinatura.sincronizar_status()
        return primeiro.empresa

    return None


def obter_perfil_usuario_empresa(usuario, empresa):
    if not usuario or not getattr(usuario, 'is_authenticated', False) or not empresa:
        return None
    vinculo = VinculoUsuarioEmpresa.objects.filter(usuario=usuario, empresa=empresa, ativo=True).first()
    return vinculo.perfil if vinculo else None


def empresa_bloqueada(empresa):
    assinatura = getattr(empresa, 'assinatura', None)
    if not assinatura:
        return True

    assinatura.sincronizar_status()

    hoje = timezone.localdate()
    status = (assinatura.status or '').upper()
    mp_status = (assinatura.mercado_pago_status or '').lower()

    if status == 'TESTE':
        return not bool(assinatura.vencimento and assinatura.vencimento >= hoje)

    if status in {'ATRASADA', 'BLOQUEADA', 'CANCELADA'}:
        return True

    if mp_status in {'pending', 'paused', 'rejected', 'expired', 'cancelled', 'cancelled_by_user'}:
        return True

    return not assinatura.esta_ativa_para_uso


def total_usuarios_empresa(empresa):
    return empresa.usuarios_vinculados.count()


def total_usuarios_ativos_empresa(empresa):
    return empresa.usuarios_vinculados.filter(ativo=True).count()


def pode_adicionar_usuario(empresa):
    assinatura = getattr(empresa, 'assinatura', None)
    if not assinatura:
        return False
    limite = assinatura.plano.limite_usuarios
    if limite is None:
        return True
    return total_usuarios_empresa(empresa) < limite


def pode_ativar_usuario(empresa, vinculo_atual=None):
    assinatura = getattr(empresa, 'assinatura', None)
    if not assinatura:
        return False
    limite = assinatura.plano.limite_usuarios
    if limite is None:
        return True

    ativos = total_usuarios_ativos_empresa(empresa)
    if vinculo_atual and vinculo_atual.ativo:
        return True
    return ativos < limite


def pode_criar_os(empresa):
    assinatura = getattr(empresa, 'assinatura', None)
    if not assinatura:
        return False
    limite = assinatura.plano.limite_ordens_mes
    if limite is None:
        return True
    hoje = timezone.localdate()
    total = OrdemServico.objects.filter(
        empresa=empresa,
        data_abertura__month=hoje.month,
        data_abertura__year=hoje.year,
    ).count()
    return total < limite


def pode_criar_produto(empresa):
    assinatura = getattr(empresa, 'assinatura', None)
    if not assinatura:
        return False
    limite = assinatura.plano.limite_produtos
    if limite is None:
        return True
    return Produto.objects.filter(empresa=empresa).count() < limite


def criar_empresa_com_trial(*, nome_responsavel, username, email, password, nome_empresa, telefone, plano):
    base_slug = slugify(nome_empresa) or 'empresa'
    slug = base_slug
    i = 2
    while Empresa.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{i}'
        i += 1

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=nome_responsavel,
    )
    empresa = Empresa.objects.create(
        nome=nome_empresa,
        nome_fantasia=nome_empresa,
        slug=slug,
        telefone=telefone,
        email=email,
    )
    assinatura = Assinatura.objects.create(empresa=empresa, plano=plano)
    assinatura.iniciar_teste()
    assinatura.save()
    ConfiguracaoEmpresa.objects.create(empresa=empresa)
    VinculoUsuarioEmpresa.objects.create(usuario=user, empresa=empresa, perfil='ADMIN')
    return user, empresa, assinatura


def solicitar_troca_plano(empresa, novo_plano, observacoes=''):
    assinatura = empresa.assinatura
    solicitacao = SolicitacaoPlano.objects.create(
        empresa=empresa,
        assinatura=assinatura,
        plano_atual=assinatura.plano,
        plano_solicitado=novo_plano,
        observacoes=observacoes,
    )
    assinatura.proximo_plano = novo_plano
    assinatura.save(update_fields=['proximo_plano', 'atualizado_em'])
    return solicitacao


def aplicar_troca_plano(assinatura, novo_plano, renovar_ciclo=True):
    assinatura.plano = novo_plano
    assinatura.proximo_plano = None
    if assinatura.status in {'ATRASADA', 'BLOQUEADA', 'CANCELADA'}:
        assinatura.status = 'ATIVA'
    if renovar_ciclo:
        assinatura.vencimento = timezone.localdate() + timedelta(days=30)
    assinatura.save()

    assinatura.solicitacoes.filter(status='ABERTA').update(status='APROVADA')
    assinatura.solicitacoes.filter(status='APROVADA', plano_solicitado=novo_plano).update(status='APLICADA')

    return assinatura


def contexto_limites_empresa(empresa):
    assinatura = getattr(empresa, 'assinatura', None)
    plano = getattr(assinatura, 'plano', None)
    hoje = timezone.localdate()
    os_mes = OrdemServico.objects.filter(
        empresa=empresa,
        data_abertura__month=hoje.month,
        data_abertura__year=hoje.year,
    ).count()
    return {
        'usuarios': total_usuarios_ativos_empresa(empresa),
        'usuarios_total': total_usuarios_empresa(empresa),
        'usuarios_limite': getattr(plano, 'limite_usuarios', None),
        'produtos': Produto.objects.filter(empresa=empresa).count(),
        'produtos_limite': getattr(plano, 'limite_produtos', None),
        'os_mes': os_mes,
        'os_limite': getattr(plano, 'limite_ordens_mes', None),
    }

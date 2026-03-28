import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from finance.services import resumo_financeiro_empresa, sincronizar_contas_empresa
from inventory.models import MovimentacaoEstoque, Produto
from workshop.models import Cliente, OrdemServico

from .forms import (
    BillingCardTokenForm,
    ConfiguracaoEmpresaForm,
    EmpresaForm,
    OnboardingForm,
    TeamMembershipForm,
    TeamUserForm,
)
from .mercadopago import (
    MercadoPagoConfigError,
    MercadoPagoService,
    aplicar_resposta_preapproval,
)
from .models import (
    Assinatura,
    ConfiguracaoEmpresa,
    Empresa,
    EventoAssinatura,
    Plano,
    VinculoUsuarioEmpresa,
)
from .permissions import require_company_profile
from .services import (
    aplicar_troca_plano,
    assinatura_cancelada,
    contexto_limites_empresa,
    criar_empresa_com_trial,
    empresa_bloqueada,
    obter_empresa_atual,
    obter_vinculos_usuario,
    pode_adicionar_usuario,
    pode_ativar_usuario,
    solicitar_troca_plano,
)

User = get_user_model()


def _redirecionar_se_cancelada(request, empresa, destino='plans'):
    if empresa and assinatura_cancelada(empresa):
        messages.warning(
            request,
            'Sua assinatura está cancelada. Para continuar, escolha um novo plano para reativar a empresa.'
        )
        return redirect(destino)
    return None


def pagina_inicial(request):
    planos = Plano.objects.filter(ativo=True, exibir_no_site=True).order_by('ordem', 'preco_mensal')
    return render(request, 'core/home.html', {'planos': planos})


def comecar_agora(request):
    initial_plan = None
    slug = request.GET.get('plano')
    if slug:
        initial_plan = Plano.objects.filter(slug=slug, ativo=True).first()

    form = OnboardingForm(request.POST or None, initial={'plano': initial_plan})
    if request.method == 'POST' and form.is_valid():
        user, empresa, assinatura = criar_empresa_com_trial(**form.cleaned_data)
        login(request, user)
        request.session['empresa_id'] = empresa.id
        messages.success(
            request,
            f'Empresa criada com sucesso. Seu teste grátis vai até '
            f'{assinatura.vencimento.strftime("%d/%m/%Y")}. Agora cadastre o cartão '
            f'para iniciar a cobrança automática somente após o período de teste.'
        )
        if settings.MERCADOPAGO_ENABLED:
            return redirect('billing_checkout')
        messages.warning(
            request,
            'Mercado Pago não configurado. Configure as credenciais para ativar o '
            'cadastro de cartão e a cobrança automática.'
        )
        return redirect('dashboard')
    return render(request, 'core/onboarding.html', {'form': form})


@login_required
def selecionar_empresa(request):
    vinculos = obter_vinculos_usuario(request.user)
    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        vinculo = vinculos.filter(empresa_id=empresa_id).first()
        if vinculo:
            request.session['empresa_id'] = vinculo.empresa_id
            messages.success(
                request,
                f'Você está visualizando a empresa {vinculo.empresa.nome_fantasia or vinculo.empresa.nome}.'
            )
            return redirect('dashboard')
        messages.error(request, 'Empresa inválida para este usuário.')
    return render(request, 'core/select_company.html', {'vinculos': vinculos})


@login_required
def dashboard(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    bloqueio = _redirecionar_se_cancelada(request, empresa)
    if bloqueio:
        return bloqueio

    assinatura = getattr(empresa, 'assinatura', None)
    sincronizar_contas_empresa(empresa)
    ordens = OrdemServico.objects.filter(empresa=empresa)
    total_produtos = Produto.objects.filter(empresa=empresa).count()
    total_clientes = Cliente.objects.filter(empresa=empresa).count()
    os_abertas = ordens.exclude(status__in=['ENTREGUE', 'CANCELADA']).count()
    faturamento = ordens.exclude(status='CANCELADA').aggregate(total=Sum('valor_total'))['total'] or 0
    baixo_estoque = Produto.objects.filter(empresa=empresa, estoque_atual__lte=0)[:5]
    if not baixo_estoque:
        baixo_estoque = Produto.objects.filter(empresa=empresa, estoque_atual__lte=1).order_by(
            'estoque_atual', 'nome'
        )[:5]
    limites = contexto_limites_empresa(empresa)
    movimentacoes = MovimentacaoEstoque.objects.filter(empresa=empresa).select_related('produto')[:5]
    financeiro = resumo_financeiro_empresa(empresa)

    return render(
        request,
        'core/dashboard.html',
        {
            'empresa': empresa,
            'assinatura': assinatura,
            'total_produtos': total_produtos,
            'total_clientes': total_clientes,
            'os_abertas': os_abertas,
            'faturamento': faturamento,
            'ultimas_os': ordens.select_related('cliente', 'ativo')[:5],
            'baixo_estoque': baixo_estoque,
            'movimentacoes': movimentacoes,
            'limites': limites,
            'bloqueada': empresa_bloqueada(empresa),
            'financeiro': financeiro,
        },
    )


@login_required
@require_company_profile('ADMIN')
def planos_empresa(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    assinatura = empresa.assinatura
    limites = contexto_limites_empresa(empresa)
    planos = Plano.objects.filter(ativo=True, exibir_no_site=True)
    solicitacoes = empresa.solicitacoes_plano.select_related('plano_solicitado')[:10]
    plano_atual = None if (assinatura and (assinatura.status or '').upper() == 'CANCELADA') else getattr(assinatura, 'plano', None)
    return render(
        request,
        'core/plans.html',
        {
            'empresa': empresa,
            'assinatura': assinatura,
            'plano_atual': plano_atual,
            'planos': planos,
            'solicitacoes': solicitacoes,
            'limites': limites,
        },
    )


@login_required
@require_company_profile('ADMIN')
def trocar_plano(request, plano_id):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    assinatura = empresa.assinatura
    novo_plano = get_object_or_404(Plano, pk=plano_id, ativo=True)

    if request.method == 'POST':
        if assinatura.status != 'CANCELADA' and novo_plano.id == assinatura.plano_id:
            messages.info(request, 'Este plano já está ativo para sua empresa.')
            return redirect('plans')

        if assinatura.status == 'CANCELADA':
            aplicar_troca_plano(assinatura, novo_plano, renovar_ciclo=False)
            messages.success(request, f'Assinatura reativada com o plano {novo_plano.nome}.')
            if settings.MERCADOPAGO_ENABLED and not assinatura.cartao_cadastrado_em:
                messages.info(request, 'Agora cadastre um cartão para reativar a cobrança automática.')
                return redirect('billing_checkout')
            return redirect('billing_status')

        if novo_plano.preco_mensal >= assinatura.plano.preco_mensal:
            aplicar_troca_plano(assinatura, novo_plano)
            messages.success(request, f'Plano alterado para {novo_plano.nome} com sucesso.')
        else:
            solicitar_troca_plano(empresa, novo_plano)
            messages.success(
                request,
                f'Sua solicitação de mudança para o plano {novo_plano.nome} foi registrada.'
            )
        return redirect('plans')

    return redirect('plans')


@login_required
@require_company_profile('ADMIN')
def cancelar_assinatura_cliente(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    assinatura = getattr(empresa, 'assinatura', None)
    if not assinatura:
        messages.error(request, 'Nenhuma assinatura encontrada para esta empresa.')
        return redirect('plans')

    if request.method != 'POST':
        return redirect('billing_status')

    if assinatura.status == 'CANCELADA':
        messages.info(request, 'A assinatura já está cancelada.')
        return redirect('billing_status')

    erro_mp = None
    if settings.MERCADOPAGO_ENABLED and assinatura.mercado_pago_preapproval_id:
        try:
            service = MercadoPagoService()
            if hasattr(service, 'cancelar_assinatura'):
                response = service.cancelar_assinatura(assinatura.mercado_pago_preapproval_id)
                assinatura.mercado_pago_status = (
                    response.get('status')
                    or response.get('auto_recurring', {}).get('status')
                    or 'cancelled'
                )
            else:
                assinatura.mercado_pago_status = 'cancelled'
        except Exception as exc:
            erro_mp = str(exc)

    assinatura.status = 'CANCELADA'
    assinatura.proximo_plano = None
    assinatura.save(update_fields=['status', 'mercado_pago_status', 'proximo_plano', 'atualizado_em'])

    EventoAssinatura.objects.create(
        assinatura=assinatura,
        origem='cliente',
        tipo='cancelamento_assinatura',
        descricao='Assinatura cancelada pela empresa no painel do cliente.',
        payload={'erro_mercado_pago': erro_mp} if erro_mp else {},
    )

    if erro_mp:
        messages.warning(
            request,
            'A assinatura foi cancelada no EzStock, mas houve falha ao confirmar no Mercado Pago. '
            f'Detalhe: {erro_mp}'
        )
    else:
        messages.success(request, 'Assinatura cancelada com sucesso.')
    return redirect('billing_status')


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def equipe(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    bloqueio = _redirecionar_se_cancelada(request, empresa)
    if bloqueio:
        return bloqueio

    form = TeamUserForm(request.POST or None)
    usuarios = empresa.usuarios_vinculados.select_related('usuario').order_by(
        'usuario__first_name', 'usuario__username'
    )
    limites = contexto_limites_empresa(empresa)
    administrador_principal = empresa.usuarios_vinculados.filter(perfil='ADMIN').order_by('id').first()

    if request.method == 'POST':
        if empresa_bloqueada(empresa):
            messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para adicionar novos usuários.')
            return redirect('plans')
        if not pode_adicionar_usuario(empresa):
            messages.error(
                request,
                'Você atingiu o limite de usuários do seu plano. Para adicionar outro usuário, faça upgrade ou exclua um vínculo existente.'
            )
            return redirect('plans')
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['nome'],
            )
            VinculoUsuarioEmpresa.objects.create(
                usuario=user,
                empresa=empresa,
                perfil=form.cleaned_data['perfil'],
                ativo=True,
            )
            messages.success(request, 'Usuário adicionado com sucesso.')
            return redirect('team')

    return render(
        request,
        'team/team.html',
        {
            'form': form,
            'usuarios': usuarios,
            'empresa': empresa,
            'limites': limites,
            'administrador_principal_id': administrador_principal.id if administrador_principal else None,
        },
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_vinculo(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    bloqueio = _redirecionar_se_cancelada(request, empresa)
    if bloqueio:
        return bloqueio

    vinculo = get_object_or_404(VinculoUsuarioEmpresa.objects.select_related('usuario'), pk=pk, empresa=empresa)
    administrador_principal = empresa.usuarios_vinculados.filter(perfil='ADMIN').order_by('id').first()

    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')

    if request.method != 'POST':
        return redirect('team')

    if administrador_principal and vinculo.id == administrador_principal.id:
        messages.error(request, 'Não é possível excluir o administrador principal que cadastrou a empresa.')
        return redirect('team')

    total_admins = empresa.usuarios_vinculados.filter(ativo=True, perfil='ADMIN').count()
    if vinculo.perfil == 'ADMIN' and vinculo.ativo and total_admins <= 1:
        messages.error(request, 'Não é possível excluir o último administrador ativo da empresa.')
        return redirect('team')

    usuario_nome = vinculo.usuario.get_full_name() or vinculo.usuario.username
    vinculo.delete()
    messages.success(request, f'Usuário {usuario_nome} removido com sucesso.')
    return redirect('team')


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def editar_empresa(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    bloqueio = _redirecionar_se_cancelada(request, empresa)
    if bloqueio:
        return bloqueio

    configuracao = getattr(empresa, 'configuracao', None)
    form_empresa = EmpresaForm(request.POST or None, instance=empresa, prefix='empresa')
    form_config = ConfiguracaoEmpresaForm(request.POST or None, instance=configuracao, prefix='config')

    if request.method == 'POST' and form_empresa.is_valid() and form_config.is_valid():
        form_empresa.save()
        config = form_config.save(commit=False)
        config.empresa = empresa
        config.save()
        messages.success(request, 'Dados da empresa atualizados com sucesso.')
        return redirect('company_settings')

    return render(
        request,
        'core/company_settings.html',
        {
            'empresa': empresa,
            'form_empresa': form_empresa,
            'form_config': form_config,
            'assinatura': getattr(empresa, 'assinatura', None),
        },
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def atualizar_vinculo(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    bloqueio = _redirecionar_se_cancelada(request, empresa)
    if bloqueio:
        return bloqueio

    vinculo = get_object_or_404(VinculoUsuarioEmpresa, pk=pk, empresa=empresa)
    form = TeamMembershipForm(request.POST or None, instance=vinculo)
    administrador_principal = empresa.usuarios_vinculados.filter(perfil='ADMIN').order_by('id').first()

    if request.method == 'POST':
        if empresa_bloqueada(empresa):
            messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
            return redirect('plans')

        if administrador_principal and vinculo.id == administrador_principal.id:
            messages.error(
                request,
                'Não é possível alterar o status do administrador principal que cadastrou a empresa.'
            )
            return redirect('team')

        deseja_ativar = request.POST.get('ativo') in {'on', 'true', '1', 'True'}
        if deseja_ativar and not pode_ativar_usuario(empresa, vinculo):
            messages.error(
                request,
                'Você atingiu o limite de usuários ativos do seu plano. Faça upgrade ou desative outro usuário antes de ativar este.'
            )
            return redirect('team')

        total_admins = empresa.usuarios_vinculados.filter(ativo=True, perfil='ADMIN').count()
        if vinculo.perfil == 'ADMIN' and vinculo.ativo and not deseja_ativar and total_admins <= 1:
            messages.error(request, 'Não é possível desativar o último administrador ativo da empresa.')
            return redirect('team')

        if form.is_valid():
            form.save()
            messages.success(request, 'Vínculo atualizado com sucesso.')
            return redirect('team')

    return render(request, 'team/edit_membership.html', {'form': form, 'vinculo': vinculo, 'empresa': empresa})


def registrar_evento_assinatura(assinatura, tipo, descricao='', payload=None, origem='sistema'):
    EventoAssinatura.objects.create(
        assinatura=assinatura,
        origem=origem,
        tipo=tipo,
        descricao=descricao or tipo.replace('_', ' ').title(),
        payload=payload or {},
    )


def _formatar_bandeira(value):
    mapping = {
        'master': 'Mastercard',
        'mastercard': 'Mastercard',
        'visa': 'Visa',
        'amex': 'American Express',
        'american express': 'American Express',
        'elo': 'Elo',
        'hipercard': 'Hipercard',
        'diners': 'Diners',
        'discover': 'Discover',
        'jcb': 'JCB',
        'aura': 'Aura',
    }
    raw = (value or '').strip().lower()
    return mapping.get(raw, value or '')


@login_required
@require_company_profile('ADMIN')
def billing_checkout(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    bloqueio = _redirecionar_se_cancelada(request, empresa, destino='billing_status')
    if bloqueio:
        return bloqueio

    assinatura = empresa.assinatura
    form = BillingCardTokenForm(request.POST or None)

    if request.method == 'POST':
        if not settings.MERCADOPAGO_ENABLED:
            messages.error(request, 'Credenciais do Mercado Pago ainda não foram configuradas no servidor.')
            return redirect('plans')

        if form.is_valid():
            try:
                card_last_four = (form.cleaned_data.get('card_last_four') or request.POST.get('card_last_four') or '').strip()[-4:]
                raw_brand = (
                    form.cleaned_data.get('card_brand')
                    or request.POST.get('card_brand')
                    or form.cleaned_data.get('payment_method_id')
                    or request.POST.get('payment_method_id')
                    or ''
                )
                card_brand = _formatar_bandeira(raw_brand)

                service = MercadoPagoService()
                if assinatura.mercado_pago_preapproval_id:
                    service.atualizar_cartao_assinatura(
                        assinatura,
                        form.cleaned_data['card_token'],
                    )
                    response = service.buscar_assinatura(assinatura.mercado_pago_preapproval_id)
                else:
                    response = service.criar_assinatura_com_teste(
                        request=request,
                        assinatura=assinatura,
                        card_token_id=form.cleaned_data['card_token'],
                        issuer_id=form.cleaned_data.get('issuer_id', ''),
                        payment_method_id=form.cleaned_data.get('payment_method_id', ''),
                        installments=form.cleaned_data.get('installments') or 1,
                    )

                if not response or not response.get('id'):
                    registrar_evento_assinatura(
                        assinatura,
                        'erro_checkout',
                        'Mercado Pago não retornou uma assinatura válida.',
                        response or {},
                        origem='checkout',
                    )
                    messages.error(
                        request,
                        f'Erro ao criar assinatura no Mercado Pago: {response or "sem detalhes"}'
                    )
                    return redirect('billing_checkout')

                aplicar_resposta_preapproval(assinatura, response)

                if not card_brand:
                    card_brand = _formatar_bandeira(response.get('payment_method_id', ''))

                campos_para_salvar = []
                if card_last_four:
                    assinatura.cartao_ultimos_digitos = card_last_four
                    campos_para_salvar.append('cartao_ultimos_digitos')
                if card_brand:
                    assinatura.cartao_bandeira = card_brand
                    campos_para_salvar.append('cartao_bandeira')

                if campos_para_salvar:
                    assinatura.save(update_fields=campos_para_salvar + ['atualizado_em'])

                registrar_evento_assinatura(
                    assinatura,
                    'cartao_cadastrado',
                    'Cartão vinculado à assinatura.',
                    response,
                    origem='checkout',
                )
                messages.success(
                    request,
                    'Cartão cadastrado com sucesso. A primeira cobrança ficará agendada '
                    'para depois do seu teste grátis.'
                )
                return redirect('billing_status')
            except MercadoPagoConfigError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                registrar_evento_assinatura(
                    assinatura,
                    'erro_checkout',
                    f'Erro inesperado no checkout: {exc}',
                    {'erro': str(exc)},
                    origem='checkout',
                )
                messages.error(request, f'Não foi possível cadastrar o cartão agora. Detalhe: {exc}')

    return render(
        request,
        'core/billing_checkout.html',
        {
            'empresa': empresa,
            'assinatura': assinatura,
            'form': form,
            'mercadopago_public_key': settings.MERCADOPAGO_PUBLIC_KEY,
            'mercadopago_enabled': settings.MERCADOPAGO_ENABLED,
        },
    )


@login_required
@require_company_profile('ADMIN')
def billing_status(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    assinatura = empresa.assinatura
    assinatura.sincronizar_status()
    return render(
        request,
        'core/billing_status.html',
        {'empresa': empresa, 'assinatura': assinatura, 'eventos': assinatura.eventos.all()[:20]},
    )


@csrf_exempt
def billing_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        payload = {}

    preapproval_id = (
        payload.get('data', {}).get('id')
        or request.GET.get('data.id')
        or request.GET.get('id')
    )

    if preapproval_id:
        assinatura = Assinatura.objects.filter(mercado_pago_preapproval_id=preapproval_id).first()
        if assinatura:
            status = payload.get('data', {}).get('status') or payload.get('status') or ''
            if status:
                assinatura.mercado_pago_status = status
                assinatura.save(update_fields=['mercado_pago_status', 'atualizado_em'])
            registrar_evento_assinatura(
                assinatura,
                'webhook_mercado_pago',
                f"Webhook recebido com status {status or 'sem status'}",
                payload,
                origem='mercado_pago',
            )

    return JsonResponse({'ok': True})


@login_required
def blocked_subscription(request):
    empresa = obter_empresa_atual(request)
    assinatura = getattr(empresa, 'assinatura', None) if empresa else None
    return render(
        request,
        'core/billing_blocked.html',
        {
            'empresa': empresa,
            'assinatura': assinatura,
        },
    )

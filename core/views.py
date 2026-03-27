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
    SolicitacaoPlano,
    VinculoUsuarioEmpresa,
)
from .permissions import require_company_profile
from .services import (
    aplicar_troca_plano,
    contexto_limites_empresa,
    criar_empresa_com_trial,
    empresa_bloqueada,
    obter_empresa_atual,
    obter_vinculos_usuario,
    pode_adicionar_usuario,
    solicitar_troca_plano,
)

User = get_user_model()


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
    return render(
        request,
        'core/plans.html',
        {
            'empresa': empresa,
            'assinatura': assinatura,
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
        if novo_plano.id == assinatura.plano_id:
            messages.info(request, 'Este plano já está ativo para sua empresa.')
            return redirect('plans')

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
@require_company_profile('ADMIN', 'GERENTE')
def equipe(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    form = TeamUserForm(request.POST or None)
    usuarios = empresa.usuarios_vinculados.select_related('usuario').order_by(
        'usuario__first_name', 'usuario__username'
    )
    limites = contexto_limites_empresa(empresa)

    if request.method == 'POST':
        if empresa_bloqueada(empresa):
            messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para adicionar novos usuários.')
            return redirect('plans')
        if not pode_adicionar_usuario(empresa):
            messages.error(request, 'Você atingiu o limite de usuários do seu plano.')
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
            )
            messages.success(request, 'Usuário adicionado com sucesso.')
            return redirect('team')

    return render(
        request,
        'team/team.html',
        {'form': form, 'usuarios': usuarios, 'empresa': empresa, 'limites': limites},
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def editar_empresa(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

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

    vinculo = get_object_or_404(VinculoUsuarioEmpresa, pk=pk, empresa=empresa)
    form = TeamMembershipForm(request.POST or None, instance=vinculo)

    if request.method == 'POST' and form.is_valid():
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


@login_required
@require_company_profile('ADMIN')
def billing_checkout(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')

    assinatura = empresa.assinatura
    form = BillingCardTokenForm(request.POST or None)

    if request.method == 'POST':
        if not settings.MERCADOPAGO_ENABLED:
            messages.error(request, 'Credenciais do Mercado Pago ainda não foram configuradas no servidor.')
            return redirect('plans')

        if form.is_valid():
            try:
                service = MercadoPagoService()
                if assinatura.mercado_pago_preapproval_id:
                    response = service.atualizar_cartao_assinatura(
                        assinatura,
                        form.cleaned_data['card_token'],
                    )
                else:
                    response = service.criar_assinatura_com_teste(
                        request=request,
                        assinatura=assinatura,
                        card_token_id=form.cleaned_data['card_token'],
                        issuer_id=form.cleaned_data.get('issuer_id', ''),
                        payment_method_id=form.cleaned_data.get('payment_method_id', ''),
                        installments=form.cleaned_data.get('installments') or 1,
                    )

                print('\n======= RESPOSTA FINAL MP =======')
                print(response)

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
                print('\nERRO NO CHECKOUT:')
                print(exc)
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
    eventos = assinatura.eventos.all()[:20]
    return render(
        request,
        'core/billing_status.html',
        {'empresa': empresa, 'assinatura': assinatura, 'eventos': eventos},
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

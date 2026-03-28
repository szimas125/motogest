from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from finance.models import ContaReceber
from workshop.models import OrdemServico

from .forms import AssinaturaAdminForm, EmpresaAdminCreateForm, EmpresaForm, PlanoAdminForm
from .models import Assinatura, Empresa, EventoAssinatura, Plano, SolicitacaoPlano, VinculoUsuarioEmpresa
from .services import aplicar_troca_plano

User = get_user_model()


def superuser_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Acesso restrito ao administrador do sistema.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _admin_url(app_label, model_name, object_id=None):
    if object_id:
        return reverse(f'admin:{app_label}_{model_name}_change', args=[object_id])
    return reverse(f'admin:{app_label}_{model_name}_changelist')


@superuser_required
def painel_admin(request):
    hoje = timezone.localdate()
    for assinatura in Assinatura.objects.select_related('plano', 'empresa'):
        assinatura.sincronizar_status()

    empresas = Empresa.objects.count()
    usuarios = User.objects.count()
    assinaturas = Assinatura.objects.select_related('empresa', 'plano')
    ativas = assinaturas.filter(status='ATIVA').count()
    testes = assinaturas.filter(status='TESTE').count()
    atrasadas = assinaturas.filter(status='ATRASADA').count()
    bloqueadas = assinaturas.filter(status='BLOQUEADA').count()
    mrr = assinaturas.filter(status__in=['ATIVA', 'TESTE']).aggregate(total=Sum('plano__preco_mensal'))['total'] or Decimal('0.00')
    contas_abertas = ContaReceber.objects.exclude(status__in=['PAGA', 'CANCELADA']).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    ordens_mes = OrdemServico.objects.filter(criado_em__year=hoje.year, criado_em__month=hoje.month).count()

    solicitacoes = SolicitacaoPlano.objects.select_related(
        'empresa', 'plano_atual', 'plano_solicitado', 'assinatura'
    ).order_by('-criada_em')[:20]

    context = {
        'cards': {
            'empresas': empresas,
            'usuarios': usuarios,
            'ativas': ativas,
            'testes': testes,
            'atrasadas': atrasadas,
            'bloqueadas': bloqueadas,
            'mrr': mrr,
            'contas_abertas': contas_abertas,
            'ordens_mes': ordens_mes,
        },
        'empresas_recentes': Empresa.objects.annotate(
            total_usuarios=Count('usuarios_vinculados', distinct=True),
            total_os=Count('ordens_servico', distinct=True),
            total_produtos=Count('produtos', distinct=True),
        ).select_related('assinatura__plano').order_by('-criada_em')[:8],
        'planos': Plano.objects.annotate(total_clientes=Count('assinaturas')).order_by('ordem', 'preco_mensal'),
        'solicitacoes': solicitacoes,
        'usuarios_recentes': User.objects.order_by('-date_joined')[:8],
        'eventos_recentes': EventoAssinatura.objects.select_related('assinatura__empresa')[:8],
    }
    return render(request, 'saas_admin/dashboard.html', context)


@superuser_required
def saas_empresas(request):
    q = request.GET.get('q', '').strip()
    qs = Empresa.objects.annotate(
        total_usuarios=Count('usuarios_vinculados', distinct=True),
        total_produtos=Count('produtos', distinct=True),
        total_os=Count('ordens_servico', distinct=True),
    ).select_related('assinatura__plano').order_by('nome')
    if q:
        qs = qs.filter(
            Q(nome__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(cnpj__icontains=q) |
            Q(email__icontains=q)
        )
    return render(request, 'saas_admin/empresas.html', {'empresas': qs[:100], 'q': q})


@superuser_required
def editar_empresa_saas(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    form = EmpresaForm(request.POST or None, instance=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Empresa atualizada com sucesso.')
        return redirect('saas_admin_empresas')
    return render(
        request,
        'saas_admin/form_page.html',
        {
            'titulo': 'Editar empresa',
            'subtitulo': empresa.nome_fantasia or empresa.nome,
            'form': form,
            'voltar_url': reverse('saas_admin_empresas'),
        },
    )


@superuser_required
def saas_assinaturas(request):
    status = request.GET.get('status', '').strip()
    qs = Assinatura.objects.select_related('empresa', 'plano', 'proximo_plano').order_by('vencimento', 'empresa__nome')
    if status:
        qs = qs.filter(status=status)
    return render(
        request,
        'saas_admin/assinaturas.html',
        {'assinaturas': qs[:100], 'status_atual': status, 'status_choices': Assinatura.STATUS_CHOICES},
    )


@superuser_required
def editar_assinatura_saas(request, pk):
    assinatura = get_object_or_404(Assinatura.objects.select_related('empresa', 'plano'), pk=pk)
    form = AssinaturaAdminForm(request.POST or None, instance=assinatura)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Assinatura atualizada com sucesso.')
        return redirect('saas_admin_assinaturas')
    return render(
        request,
        'saas_admin/form_page.html',
        {
            'titulo': 'Editar assinatura',
            'subtitulo': assinatura.empresa.nome_fantasia or assinatura.empresa.nome,
            'form': form,
            'voltar_url': reverse('saas_admin_assinaturas'),
        },
    )


@superuser_required
def saas_usuarios(request):
    q = request.GET.get('q', '').strip()
    vinculos = VinculoUsuarioEmpresa.objects.select_related('usuario', 'empresa').order_by(
        'empresa__nome', 'usuario__first_name', 'usuario__username'
    )
    if q:
        vinculos = vinculos.filter(
            Q(usuario__username__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__email__icontains=q) |
            Q(empresa__nome__icontains=q) |
            Q(empresa__nome_fantasia__icontains=q)
        )
    return render(request, 'saas_admin/usuarios.html', {'vinculos': vinculos[:150], 'q': q})


@superuser_required
def saas_planos(request):
    q = request.GET.get('q', '').strip()
    planos = Plano.objects.annotate(total_clientes=Count('assinaturas')).order_by('ordem', 'preco_mensal')
    if q:
        planos = planos.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
    return render(request, 'saas_admin/planos.html', {'planos': planos[:100], 'q': q})


@superuser_required
def editar_plano_saas(request, pk):
    plano = get_object_or_404(Plano, pk=pk)
    form = PlanoAdminForm(request.POST or None, instance=plano)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Plano atualizado com sucesso.')
        return redirect('saas_admin_planos')
    return render(
        request,
        'saas_admin/form_page.html',
        {
            'titulo': 'Editar plano',
            'subtitulo': plano.nome,
            'form': form,
            'voltar_url': reverse('saas_admin_planos'),
        },
    )


@superuser_required
def criar_empresa_saas(request):
    form = EmpresaAdminCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.save()
        messages.success(request, 'Empresa criada com sucesso.')
        return redirect('saas_admin_empresa_edit', pk=empresa.pk)
    return render(
        request,
        'saas_admin/form_page.html',
        {
            'titulo': 'Nova empresa',
            'subtitulo': 'Cadastre uma nova empresa no SaaS',
            'form': form,
            'voltar_url': reverse('saas_admin_empresas'),
        },
    )


@superuser_required
def criar_plano_saas(request):
    form = PlanoAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plano = form.save()
        messages.success(request, 'Plano criado com sucesso.')
        return redirect('saas_admin_plano_edit', pk=plano.pk)
    return render(
        request,
        'saas_admin/form_page.html',
        {
            'titulo': 'Novo plano',
            'subtitulo': 'Cadastre um novo plano do EzStock',
            'form': form,
            'voltar_url': reverse('saas_admin_planos'),
        },
    )


@superuser_required
def aprovar_solicitacao_plano_saas(request, pk):
    solicitacao = get_object_or_404(
        SolicitacaoPlano.objects.select_related(
            'assinatura', 'empresa', 'plano_solicitado', 'plano_atual'
        ),
        pk=pk,
    )
    assinatura = solicitacao.assinatura

    if request.method == 'POST':
        # idempotente: se ainda não foi aplicada, aplica agora
        if assinatura.plano_id != solicitacao.plano_solicitado_id:
            aplicar_troca_plano(assinatura, solicitacao.plano_solicitado, renovar_ciclo=False)

        solicitacao.status = 'APLICADA'
        solicitacao.save(update_fields=['status', 'atualizado_em'])
        messages.success(
            request,
            f'Troca para o plano {solicitacao.plano_solicitado.nome} aplicada com sucesso.'
        )

    return redirect('saas_admin_dashboard')


@superuser_required
def recusar_solicitacao_plano_saas(request, pk):
    solicitacao = get_object_or_404(
        SolicitacaoPlano.objects.select_related('assinatura', 'empresa', 'plano_solicitado'),
        pk=pk,
    )
    if request.method == 'POST':
        solicitacao.status = 'RECUSADA'
        solicitacao.save(update_fields=['status', 'atualizado_em'])
        assinatura = solicitacao.assinatura
        assinatura.proximo_plano = None
        assinatura.save(update_fields=['proximo_plano', 'atualizado_em'])
        messages.success(request, 'Solicitação recusada com sucesso.')
    return redirect('saas_admin_dashboard')

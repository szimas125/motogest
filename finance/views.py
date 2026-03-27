from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from core.permissions import require_company_profile
from core.services import empresa_bloqueada, obter_empresa_atual
from .forms import ContaReceberForm, LancamentoCaixaForm
from .models import ContaReceber, LancamentoCaixa
from .services import gerar_conta_por_os, registrar_recebimento, resumo_financeiro_empresa, sincronizar_contas_empresa
from workshop.models import OrdemServico


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def financeiro_dashboard(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    sincronizar_contas_empresa(empresa)
    busca = request.GET.get('q', '').strip()
    contas = ContaReceber.objects.filter(empresa=empresa).select_related('ordem_servico', 'ordem_servico__cliente')
    if busca:
        contas = contas.filter(Q(descricao__icontains=busca) | Q(ordem_servico__numero__icontains=busca) | Q(ordem_servico__cliente__nome__icontains=busca))
    lancamentos = LancamentoCaixa.objects.filter(empresa=empresa)[:10]
    resumo = resumo_financeiro_empresa(empresa)
    return render(request, 'finance/dashboard.html', {
        'empresa': empresa,
        'resumo': resumo,
        'contas': contas[:20],
        'lancamentos': lancamentos,
        'busca': busca,
        'bloqueada': empresa_bloqueada(empresa),
    })


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def conta_create(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = ContaReceberForm(request.POST or None, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        conta = form.save(commit=False)
        conta.empresa = empresa
        conta.save()
        messages.success(request, 'Conta a receber cadastrada com sucesso.')
        return redirect('finance_dashboard')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Nova conta a receber', 'cancel_url': 'finance_dashboard'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def conta_edit(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    conta = get_object_or_404(ContaReceber, pk=pk, empresa=empresa)
    form = ContaReceberForm(request.POST or None, instance=conta, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Conta atualizada com sucesso.')
        return redirect('finance_dashboard')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Editar conta a receber', 'cancel_url': 'finance_dashboard'})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def conta_delete(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    conta = get_object_or_404(ContaReceber, pk=pk, empresa=empresa)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso.')
        return redirect('finance_dashboard')
    return render(request, 'shared/confirm_delete.html', {'title': 'Excluir conta', 'message': f'Deseja excluir a conta "{conta.descricao}"?', 'cancel_url': 'finance_dashboard'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def gerar_conta_os(request, order_pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico, pk=order_pk, empresa=empresa)
    conta, created = gerar_conta_por_os(order)
    messages.success(request, 'Conta gerada com sucesso.' if created else 'Esta OS já possui conta a receber vinculada.')
    return redirect('finance_dashboard')


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def marcar_conta_paga(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    conta = get_object_or_404(ContaReceber, pk=pk, empresa=empresa)
    if request.method == 'POST':
        registrar_recebimento(conta, forma_pagamento=request.POST.get('forma_pagamento', ''))
        messages.success(request, 'Pagamento registrado com sucesso.')
    return redirect('finance_dashboard')


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def lancamento_create(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    form = LancamentoCaixaForm(request.POST or None, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        lancamento = form.save(commit=False)
        lancamento.empresa = empresa
        lancamento.save()
        messages.success(request, 'Lançamento registrado com sucesso.')
        return redirect('finance_dashboard')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Novo lançamento de caixa', 'cancel_url': 'finance_dashboard'})

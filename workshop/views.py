from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from core.permissions import require_company_profile
from core.services import empresa_bloqueada, obter_empresa_atual, pode_criar_os
from .forms import ClienteForm, ItemOrdemServicoForm, AtivoForm, NotaInternaForm, OrdemServicoForm
from .models import Cliente, ItemOrdemServico, Ativo, NotaInterna, OrdemServico


@login_required
def lista_clientes(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    busca = request.GET.get('q', '').strip()
    customers = Cliente.objects.filter(empresa=empresa)
    if busca:
        customers = customers.filter(
            Q(nome__icontains=busca) |
            Q(cpf_cnpj__icontains=busca) |
            Q(telefone__icontains=busca) |
            Q(email__icontains=busca)
        )
    return render(request, 'workshop/customer_list.html', {'customers': customers.order_by('nome'), 'empresa': empresa, 'busca': busca})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def criar_cliente(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = ClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cliente = form.save(commit=False)
        cliente.empresa = empresa
        cliente.save()
        messages.success(request, 'Cliente cadastrado com sucesso.')
        return redirect('customer_list')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Novo cliente', 'cancel_url': 'customer_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def editar_cliente(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    cliente = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Cliente atualizado com sucesso.')
        return redirect('customer_list')
    return render(request, 'shared/form.html', {'form': form, 'title': f'Editar cliente - {cliente.nome}', 'cancel_url': 'customer_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_cliente(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    cliente = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    if request.method == 'POST':
        if cliente.ativos.exists() or OrdemServico.objects.filter(empresa=empresa, cliente=cliente).exists():
            messages.error(request, 'Não é possível excluir este cliente porque ele possui ativos ou ordens de serviço vinculadas.')
        else:
            cliente.delete()
            messages.success(request, 'Cliente excluído com sucesso.')
        return redirect('customer_list')
    return render(request, 'shared/confirm_delete.html', {
        'title': 'Excluir cliente',
        'message': f'Deseja excluir o cliente "{cliente.nome}"?',
        'cancel_url': 'customer_list',
    })


@login_required
def lista_ativos(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    busca = request.GET.get('q', '').strip()
    assets = Ativo.objects.select_related('cliente').filter(empresa=empresa)
    if busca:
        assets = assets.filter(
            Q(marca__icontains=busca) |
            Q(modelo__icontains=busca) |
            Q(placa__icontains=busca) |
            Q(cliente__nome__icontains=busca)
        )
    return render(request, 'workshop/asset_list.html', {'assets': assets.order_by('marca', 'modelo'), 'empresa': empresa, 'busca': busca})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def criar_ativo(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = AtivoForm(request.POST or None, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        ativo = form.save(commit=False)
        ativo.empresa = empresa
        ativo.save()
        messages.success(request, 'Ativo cadastrado com sucesso.')
        return redirect('asset_list')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Novo ativo', 'cancel_url': 'asset_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def editar_ativo(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    ativo = get_object_or_404(Ativo, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = AtivoForm(request.POST or None, instance=ativo, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Ativo atualizado com sucesso.')
        return redirect('asset_list')
    return render(request, 'shared/form.html', {'form': form, 'title': f'Editar ativo - {ativo.marca} {ativo.modelo}', 'cancel_url': 'asset_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_ativo(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    ativo = get_object_or_404(Ativo, pk=pk, empresa=empresa)
    if request.method == 'POST':
        if OrdemServico.objects.filter(empresa=empresa, ativo=ativo).exists():
            messages.error(request, 'Não é possível excluir este ativo porque ele possui ordens de serviço vinculadas.')
        else:
            ativo.delete()
            messages.success(request, 'Ativo excluído com sucesso.')
        return redirect('asset_list')
    return render(request, 'shared/confirm_delete.html', {
        'title': 'Excluir ativo',
        'message': f'Deseja excluir o ativo "{ativo.marca} {ativo.modelo}"?',
        'cancel_url': 'asset_list',
    })


@login_required
def lista_ordens_servico(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    busca = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    orders = OrdemServico.objects.select_related('cliente', 'ativo').filter(empresa=empresa)
    if busca:
        orders = orders.filter(
            Q(numero__icontains=busca) |
            Q(cliente__nome__icontains=busca) |
            Q(ativo__marca__icontains=busca) |
            Q(ativo__modelo__icontains=busca)
        )
    if status:
        orders = orders.filter(status=status)
    return render(request, 'workshop/service_order_list.html', {
        'orders': orders.order_by('-criado_em'),
        'empresa': empresa,
        'bloqueada': empresa_bloqueada(empresa),
        'busca': busca,
        'status_atual': status,
        'status_choices': OrdemServico.STATUS_CHOICES,
    })


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE', 'MECANICO')
def criar_ordem_servico(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = OrdemServicoForm(request.POST or None, initial={'data_abertura': date.today()}, empresa=empresa)
    if request.method == 'POST':
        if not pode_criar_os(empresa):
            messages.error(request, 'Você atingiu o limite de ordens de serviço do seu plano neste mês.')
            return redirect('plans')
        if form.is_valid():
            ordem = form.save(commit=False)
            ordem.empresa = empresa
            ordem.save()
            messages.success(request, 'Ordem de serviço criada com sucesso.')
            return redirect('service_order_detail', pk=ordem.pk)
    return render(request, 'shared/form.html', {'form': form, 'title': 'Nova ordem de serviço', 'cancel_url': 'service_order_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE', 'MECANICO')
def editar_ordem_servico(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = OrdemServicoForm(request.POST or None, instance=order, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        order.recalcular_total()
        messages.success(request, 'Ordem de serviço atualizada com sucesso.')
        return redirect('service_order_detail', pk=order.pk)
    return render(request, 'shared/form.html', {'form': form, 'title': f'Editar OS {order.numero}', 'cancel_url': 'service_order_detail', 'cancel_kwargs': {'pk': order.pk}})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_ordem_servico(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    if request.method == 'POST':
        for item in list(order.itens.all()):
            item.delete()
        order.delete()
        messages.success(request, 'Ordem de serviço excluída com sucesso.')
        return redirect('service_order_list')
    return render(request, 'shared/confirm_delete.html', {
        'title': 'Excluir ordem de serviço',
        'message': f'Deseja excluir a ordem de serviço "{order.numero}"?',
        'cancel_url': 'service_order_detail',
        'cancel_kwargs': {'pk': order.pk},
    })


@login_required
def detalhe_ordem_servico(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico.objects.select_related('cliente', 'ativo'), pk=pk, empresa=empresa)
    item_form = ItemOrdemServicoForm(empresa=empresa)
    return render(request, 'workshop/service_order_detail.html', {'order': order, 'item_form': item_form, 'empresa': empresa, 'bloqueada': empresa_bloqueada(empresa)})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE', 'MECANICO')
def adicionar_item_ordem_servico(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    order = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    form = ItemOrdemServicoForm(request.POST or None, empresa=empresa)
    if request.method == 'POST':
        if form.is_valid():
            item = form.save(commit=False)
            item.empresa = empresa
            item.ordem_servico = order
            if item.tipo_item == 'PRODUTO' and item.produto and not item.descricao:
                item.descricao = item.produto.nome
            item.save()
            messages.success(request, 'Item adicionado à ordem de serviço.')
        else:
            messages.error(request, 'Não foi possível adicionar o item. Revise os dados.')
    return redirect('service_order_detail', pk=pk)


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE', 'MECANICO')
def editar_item_ordem_servico(request, pk, item_pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    item = get_object_or_404(ItemOrdemServico, pk=item_pk, ordem_servico=order, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = ItemOrdemServicoForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == 'POST':
        if form.is_valid():
            novo_item = form.save(commit=False)
            novo_item.empresa = empresa
            novo_item.ordem_servico = order
            if novo_item.tipo_item == 'PRODUTO' and novo_item.produto and not novo_item.descricao:
                novo_item.descricao = novo_item.produto.nome
            novo_item.save()
            messages.success(request, 'Item atualizado com sucesso.')
            return redirect('service_order_detail', pk=pk)
        messages.error(request, 'Não foi possível atualizar o item.')
    return render(request, 'shared/form.html', {'form': form, 'title': f'Editar item da OS {order.numero}', 'cancel_url': 'service_order_detail', 'cancel_kwargs': {'pk': order.pk}})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_item_ordem_servico(request, pk, item_pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    item = get_object_or_404(ItemOrdemServico, pk=item_pk, ordem_servico=order, empresa=empresa)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item removido da ordem de serviço.')
        return redirect('service_order_detail', pk=pk)
    return render(request, 'shared/confirm_delete.html', {
        'title': 'Excluir item da ordem de serviço',
        'message': f'Deseja excluir o item "{item.descricao}" da OS {order.numero}?',
        'cancel_url': 'service_order_detail',
        'cancel_kwargs': {'pk': order.pk},
    })


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def criar_nota(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    order = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    invoice = getattr(order, 'nota_interna', None)
    form = NotaInternaForm(request.POST or None, instance=invoice, initial={'data_emissao': date.today(), 'numero_nota': f'N{order.numero}'})
    if request.method == 'POST' and form.is_valid():
        nota = form.save(commit=False)
        nota.empresa = empresa
        nota.ordem_servico = order
        nota.save()
        messages.success(request, 'Nota interna gerada com sucesso.')
        return redirect('invoice_print', pk=nota.pk)
    return render(request, 'shared/form.html', {'form': form, 'title': f'Gerar nota interna - OS {order.numero}', 'cancel_url': 'service_order_detail', 'cancel_kwargs': {'pk': order.pk}})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE', 'MECANICO')
def imprimir_nota(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    invoice = get_object_or_404(NotaInterna.objects.select_related('ordem_servico__cliente', 'ordem_servico__ativo', 'empresa'), pk=pk, empresa=empresa)
    return render(request, 'workshop/invoice_print.html', {'invoice': invoice, 'empresa': empresa, 'configuracao': getattr(empresa, 'configuracao', None)})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE', 'MECANICO')
def imprimir_ordem_servico(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    order = get_object_or_404(OrdemServico.objects.select_related('cliente', 'ativo', 'empresa'), pk=pk, empresa=empresa)
    return render(request, 'workshop/service_order_print.html', {'order': order, 'empresa': empresa, 'configuracao': getattr(empresa, 'configuracao', None)})

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import require_company_profile
from core.services import empresa_bloqueada, obter_empresa_atual, pode_criar_produto

from .forms import CategoriaForm, MovimentacaoEstoqueForm, ProdutoForm
from .models import Categoria, MovimentacaoEstoque, Produto


@login_required
def lista_produtos(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    busca = request.GET.get('q', '').strip()
    produtos = Produto.objects.select_related('categoria').filter(empresa=empresa)
    if busca:
        produtos = produtos.filter(
            Q(nome__icontains=busca)
            | Q(sku__icontains=busca)
            | Q(marca__icontains=busca)
            | Q(categoria__nome__icontains=busca)
        )
    produtos = produtos.order_by('nome')
    return render(
        request,
        'inventory/product_list.html',
        {
            'products': produtos,
            'empresa': empresa,
            'bloqueada': empresa_bloqueada(empresa),
            'busca': busca,
        },
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def criar_categoria(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = CategoriaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        categoria = form.save(commit=False)
        categoria.empresa = empresa
        categoria.save()
        messages.success(request, 'Categoria cadastrada com sucesso.')
        return redirect('product_list')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Nova categoria', 'cancel_url': 'product_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def editar_categoria(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    categoria = get_object_or_404(Categoria, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Categoria atualizada com sucesso.')
        return redirect('product_list')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Editar categoria', 'cancel_url': 'product_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_categoria(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    categoria = get_object_or_404(Categoria, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    if request.method == 'POST':
        if categoria.produtos.exists():
            messages.error(request, 'Não é possível excluir uma categoria com produtos vinculados.')
        else:
            categoria.delete()
            messages.success(request, 'Categoria excluída com sucesso.')
        return redirect('product_list')
    return render(
        request,
        'shared/confirm_delete.html',
        {
            'title': 'Excluir categoria',
            'message': f'Deseja excluir a categoria "{categoria.nome}"?',
            'cancel_url': 'product_list',
        },
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def criar_produto(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = ProdutoForm(request.POST or None, empresa=empresa)
    if request.method == 'POST':
        if not pode_criar_produto(empresa):
            messages.error(request, 'Você atingiu o limite de produtos do seu plano.')
            return redirect('plans')
        if form.is_valid():
            produto = form.save(commit=False)
            produto.empresa = empresa
            produto.save()
            messages.success(request, 'Produto cadastrado com sucesso.')
            return redirect('product_list')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Novo produto', 'cancel_url': 'product_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def editar_produto(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    produto = get_object_or_404(Produto, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = ProdutoForm(request.POST or None, instance=produto, empresa=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Produto atualizado com sucesso.')
        return redirect('product_list')
    return render(
        request,
        'shared/form.html',
        {'form': form, 'title': f'Editar produto - {produto.nome}', 'cancel_url': 'product_list'},
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_produto(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    produto = get_object_or_404(Produto, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    if request.method == 'POST':
        if produto.movimentacoes.exists() or produto.itemordemservico_set.exists():
            messages.error(
                request,
                'Não é possível excluir este produto porque ele já possui movimentações ou uso em ordem de serviço.',
            )
        else:
            produto.delete()
            messages.success(request, 'Produto excluído com sucesso.')
        return redirect('product_list')
    return render(
        request,
        'shared/confirm_delete.html',
        {
            'title': 'Excluir produto',
            'message': f'Deseja excluir o produto "{produto.nome}"?',
            'cancel_url': 'product_list',
        },
    )


@login_required
def lista_movimentacoes(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    busca = request.GET.get('q', '').strip()
    movements = MovimentacaoEstoque.objects.select_related('produto').filter(empresa=empresa)
    if busca:
        movements = movements.filter(Q(produto__nome__icontains=busca) | Q(motivo__icontains=busca))
    movements = movements.order_by('-criado_em')
    return render(
        request,
        'inventory/movement_list.html',
        {
            'movements': movements,
            'empresa': empresa,
            'bloqueada': empresa_bloqueada(empresa),
            'busca': busca,
        },
    )


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def criar_movimentacao(request):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = MovimentacaoEstoqueForm(request.POST or None, empresa=empresa)
    if request.method == 'POST':
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.empresa = empresa
            movimentacao.save()
            messages.success(request, 'Movimentação registrada com sucesso.')
            return redirect('movement_list')
        messages.error(request, 'Não foi possível salvar a movimentação. Verifique os dados.')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Nova movimentação', 'cancel_url': 'movement_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE', 'ATENDENTE')
def editar_movimentacao(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    form = MovimentacaoEstoqueForm(request.POST or None, instance=movimentacao, empresa=empresa)
    if request.method == 'POST':
        if form.is_valid():
            nova = form.save(commit=False)
            nova.empresa = empresa
            nova.save()
            messages.success(request, 'Movimentação atualizada com sucesso.')
            return redirect('movement_list')
        messages.error(request, 'Não foi possível atualizar a movimentação.')
    return render(request, 'shared/form.html', {'form': form, 'title': 'Editar movimentação', 'cancel_url': 'movement_list'})


@login_required
@require_company_profile('ADMIN', 'GERENTE')
def excluir_movimentacao(request, pk):
    empresa = obter_empresa_atual(request)
    if not empresa:
        return redirect('selecionar_empresa')
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk, empresa=empresa)
    if empresa_bloqueada(empresa):
        messages.error(request, 'Sua assinatura está bloqueada. Regularize o plano para continuar.')
        return redirect('plans')
    if request.method == 'POST':
        movimentacao.delete()
        messages.success(request, 'Movimentação excluída com sucesso.')
        return redirect('movement_list')
    return render(
        request,
        'shared/confirm_delete.html',
        {
            'title': 'Excluir movimentação',
            'message': f'Deseja excluir a movimentação do produto "{movimentacao.produto.nome}"?',
            'cancel_url': 'movement_list',
        },
    )

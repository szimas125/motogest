from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import ContaReceber, LancamentoCaixa


def sincronizar_contas_empresa(empresa):
    hoje = timezone.localdate()
    for conta in ContaReceber.objects.filter(empresa=empresa, status='ABERTA', vencimento__lt=hoje):
        conta.marcar_atrasada_se_necessario(hoje=hoje)


def gerar_conta_por_os(ordem_servico, vencimento=None):
    conta = ContaReceber.objects.filter(ordem_servico=ordem_servico).first()
    if conta:
        return conta, False
    conta = ContaReceber.objects.create(
        empresa=ordem_servico.empresa,
        ordem_servico=ordem_servico,
        descricao=f'Ordem de serviço {ordem_servico.numero} - {ordem_servico.cliente.nome}',
        valor=ordem_servico.valor_total,
        vencimento=vencimento or ordem_servico.data_abertura,
        status='ABERTA',
    )
    return conta, True


def registrar_recebimento(conta, forma_pagamento='', recebido_em=None):
    hoje = recebido_em or timezone.localdate()
    conta.status = 'PAGA'
    conta.forma_pagamento = forma_pagamento or conta.forma_pagamento
    conta.recebido_em = hoje
    conta.save(update_fields=['status', 'forma_pagamento', 'recebido_em'])
    existe = LancamentoCaixa.objects.filter(conta_receber=conta, tipo='RECEITA').exists()
    if not existe:
        LancamentoCaixa.objects.create(
            empresa=conta.empresa,
            conta_receber=conta,
            tipo='RECEITA',
            descricao=conta.descricao,
            valor=conta.valor,
            data_lancamento=hoje,
            categoria='Ordens de serviço' if conta.ordem_servico_id else 'Recebimentos',
        )
    return conta


def resumo_financeiro_empresa(empresa, mes=None, ano=None):
    hoje = timezone.localdate()
    mes = mes or hoje.month
    ano = ano or hoje.year
    receitas = LancamentoCaixa.objects.filter(empresa=empresa, tipo='RECEITA', data_lancamento__month=mes, data_lancamento__year=ano).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    despesas = LancamentoCaixa.objects.filter(empresa=empresa, tipo='DESPESA', data_lancamento__month=mes, data_lancamento__year=ano).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    aberto = ContaReceber.objects.filter(empresa=empresa, status__in=['ABERTA', 'ATRASADA']).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    atrasado = ContaReceber.objects.filter(empresa=empresa, status='ATRASADA').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    return {
        'receitas': receitas,
        'despesas': despesas,
        'saldo': receitas - despesas,
        'em_aberto': aberto,
        'atrasado': atrasado,
    }

import uuid
from datetime import datetime

import mercadopago
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


class MercadoPagoConfigError(Exception):
    pass


def _parse_mp_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return timezone.localdate(value)
    raw = str(value).replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
        except ValueError:
            return None


def _sync_status_from_mp(assinatura, mp_status, next_payment_date=None):
    hoje = timezone.localdate()
    vencimento_atual = assinatura.vencimento

    if mp_status:
        assinatura.mercado_pago_status = mp_status

    parsed = _parse_mp_date(next_payment_date) if next_payment_date else None
    if parsed:
        if assinatura.status == 'TESTE' and vencimento_atual:
            if parsed > vencimento_atual:
                assinatura.vencimento = parsed
        else:
            assinatura.vencimento = parsed

    status = (mp_status or '').lower()
    if status in {'authorized', 'active'}:
        if assinatura.status == 'TESTE' and assinatura.vencimento and assinatura.vencimento >= hoje:
            pass
        else:
            assinatura.status = 'ATIVA'
            if not assinatura.vencimento or assinatura.vencimento < hoje:
                assinatura.vencimento = hoje + timezone.timedelta(days=30)
    elif status in {'pending', 'paused'}:
        if assinatura.status != 'TESTE':
            assinatura.status = 'ATRASADA'
    elif status in {'cancelled', 'cancelled_by_user'}:
        assinatura.status = 'CANCELADA'
    elif status in {'rejected', 'expired'}:
        if assinatura.status != 'TESTE':
            assinatura.status = 'BLOQUEADA'
    return assinatura


class MercadoPagoService:
    def __init__(self):
        if not settings.MERCADOPAGO_ENABLED:
            raise MercadoPagoConfigError('Credenciais do Mercado Pago não configuradas.')
        self.sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    def _request_options(self):
        request_options = mercadopago.config.RequestOptions()
        request_options.custom_headers = {
            'x-idempotency-key': str(uuid.uuid4()),
        }
        return request_options

    def criar_assinatura_com_teste(self, request, assinatura, card_token_id, issuer_id='', payment_method_id='', installments=1):
        empresa = assinatura.empresa
        plano = assinatura.plano
        agora = timezone.now()
        proxima_cobranca = agora + timezone.timedelta(days=plano.periodo_teste_dias)

        payer_email = (
            (request.POST.get('holder_email') or '').strip()
            or getattr(empresa, 'email', '')
            or getattr(request.user, 'email', '')
            or 'buyer@testuser.com'
        ).strip()

        cpf = (
            request.POST.get('cpf')
            or request.POST.get('cpf_cnpj')
            or request.POST.get('doc_number')
            or request.POST.get('docNumber')
            or request.POST.get('document')
            or request.POST.get('documento')
            or request.POST.get('identificationNumber')
            or ''
        )
        cpf = ''.join(ch for ch in cpf if ch.isdigit())

        if not cpf:
            raise MercadoPagoConfigError('CPF do titular não enviado para o Mercado Pago.')

        document_type = (
            request.POST.get('document_type')
            or request.POST.get('doc_type')
            or request.POST.get('identificationType')
            or 'CPF'
        ).strip().upper()

        start_date = proxima_cobranca.strftime('%Y-%m-%dT%H:%M:%S.000-03:00')

        payload = {
            'reason': f'EzStock - Plano {plano.nome}',
            'payer_email': payer_email,
            'payer': {
                'email': payer_email,
                'identification': {
                    'type': document_type,
                    'number': cpf,
                }
            },
            'card_token_id': card_token_id,
            'auto_recurring': {
                'frequency': 1,
                'frequency_type': 'months',
                'transaction_amount': float(plano.preco_mensal),
                'currency_id': 'BRL',
                'start_date': start_date,
            },
            'back_url': request.build_absolute_uri(reverse('billing_status')),
            'external_reference': f'assinatura:{assinatura.id}:empresa:{empresa.id}',
            'status': 'authorized',
        }

        if issuer_id:
            payload['issuer_id'] = issuer_id

        if payment_method_id:
            payload['payment_method_id'] = payment_method_id

        print('\n========== MP PAYLOAD ==========')
        print(payload)

        result = self.sdk.preapproval().create(payload, self._request_options())

        print('\n========== MP RESPONSE ==========')
        print(result)

        response = result.get('response', {})

        if result.get('status') not in (200, 201):
            print('\nERRO AO CRIAR ASSINATURA')
            print('Status:', result.get('status'))
            print('Response:', response)

        return response

    def atualizar_cartao_assinatura(self, assinatura, card_token_id):
        if not assinatura.mercado_pago_preapproval_id:
            raise MercadoPagoConfigError('A assinatura ainda não possui vínculo com o Mercado Pago.')

        payload = {'card_token_id': card_token_id}
        result = self.sdk.preapproval().update(
            assinatura.mercado_pago_preapproval_id,
            payload,
            self._request_options()
        )

        print('\n========== MP UPDATE RESPONSE ==========')
        print(result)

        return result.get('response', {})

    def buscar_assinatura(self, subscription_id):
        result = self.sdk.preapproval().get(subscription_id)
        print('\n========== MP GET SUBSCRIPTION ==========')
        print(result)
        return result.get('response', {})

    def cancelar_assinatura(self, subscription_id):
        result = self.sdk.preapproval().update(
            subscription_id,
            {'status': 'cancelled'},
            self._request_options()
        )
        print('\n========== MP CANCEL RESPONSE ==========')
        print(result)
        return result.get('response', {})


def aplicar_resposta_preapproval(assinatura, data):
    if not data:
        return assinatura

    assinatura.mercado_pago_preapproval_id = data.get('id', assinatura.mercado_pago_preapproval_id or '')
    assinatura.mercado_pago_status = data.get('status', assinatura.mercado_pago_status or '')

    card = data.get('card', {}) or {}
    if card:
        assinatura.cartao_ultimos_digitos = card.get('last_four_digits', assinatura.cartao_ultimos_digitos or '')
        assinatura.cartao_bandeira = card.get('payment_method', {}).get('name', assinatura.cartao_bandeira or '')

    if assinatura.mercado_pago_preapproval_id and not assinatura.cartao_cadastrado_em:
        assinatura.cartao_cadastrado_em = timezone.now()

    next_payment_date = (
        data.get('next_payment_date')
        or data.get('auto_recurring', {}).get('start_date')
    )
    _sync_status_from_mp(assinatura, data.get('status', assinatura.mercado_pago_status), next_payment_date)

    assinatura.save(update_fields=[
        'mercado_pago_preapproval_id',
        'mercado_pago_status',
        'cartao_ultimos_digitos',
        'cartao_bandeira',
        'cartao_cadastrado_em',
        'status',
        'vencimento',
        'atualizado_em'
    ])
    return assinatura

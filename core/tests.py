from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Assinatura, Empresa, EventoAssinatura, Plano, VinculoUsuarioEmpresa

User = get_user_model()


class BillingStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='adminempresa', password='123456')
        self.plano = Plano.objects.create(nome='Starter Teste', slug='starter-teste', preco_mensal='79.99')
        self.empresa = Empresa.objects.create(nome='Oficina Central', slug='empresa-central', nome_fantasia='Oficina Central')
        self.assinatura = Assinatura.objects.create(empresa=self.empresa, plano=self.plano)
        self.assinatura.iniciar_teste()
        self.assinatura.save()
        VinculoUsuarioEmpresa.objects.create(usuario=self.user, empresa=self.empresa, perfil='ADMIN')
        session = self.client.session
        session['empresa_id'] = self.empresa.id
        session.save()

    def test_status_page_requires_login(self):
        response = self.client.get(reverse('billing_status'))
        self.assertEqual(response.status_code, 302)

    def test_status_page_shows_event_log(self):
        self.client.login(username='adminempresa', password='123456')
        EventoAssinatura.objects.create(assinatura=self.assinatura, origem='teste', tipo='cartao_cadastrado', descricao='Cartão salvo com sucesso')
        response = self.client.get(reverse('billing_status'))
        self.assertContains(response, 'Status da assinatura')
        self.assertContains(response, 'cartao_cadastrado')

    def test_webhook_creates_event(self):
        self.assinatura.mercado_pago_preapproval_id = 'pre123'
        self.assinatura.save(update_fields=['mercado_pago_preapproval_id'])
        payload = {'data': {'id': 'pre123', 'status': 'authorized'}}
        response = self.client.post(reverse('billing_webhook'), data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assinatura.refresh_from_db()
        self.assertEqual(self.assinatura.mercado_pago_status, 'authorized')
        self.assertTrue(EventoAssinatura.objects.filter(assinatura=self.assinatura, tipo='webhook_mercado_pago').exists())

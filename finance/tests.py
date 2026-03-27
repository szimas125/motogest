from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Assinatura, ConfiguracaoEmpresa, Empresa, Plano, VinculoUsuarioEmpresa
from finance.services import gerar_conta_por_os, registrar_recebimento
from workshop.models import Cliente, Ativo, OrdemServico

User = get_user_model()


class FinanceiroTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(nome='Teste', slug='teste-x', preco_mensal='79.99')
        self.empresa = Empresa.objects.create(nome='Oficina Teste', slug='empresa-teste')
        self.assinatura = Assinatura.objects.create(empresa=self.empresa, plano=self.plano, status='ATIVA', inicio=date.today(), vencimento=date.today())
        ConfiguracaoEmpresa.objects.create(empresa=self.empresa)
        self.user = User.objects.create_user(username='admin', password='123456')
        VinculoUsuarioEmpresa.objects.create(usuario=self.user, empresa=self.empresa, perfil='ADMIN')
        self.cliente = Cliente.objects.create(empresa=self.empresa, nome='Cliente Teste')
        self.ativo = Ativo.objects.create(empresa=self.empresa, cliente=self.cliente, marca='Honda', modelo='CG')
        self.os = OrdemServico.objects.create(empresa=self.empresa, numero='1', cliente=self.cliente, ativo=self.ativo, data_abertura=date.today(), queixa='Revisão', valor_total='120.00')

    def test_gerar_conta_por_os(self):
        conta, created = gerar_conta_por_os(self.os)
        self.assertTrue(created)
        self.assertEqual(conta.valor, self.os.valor_total)

    def test_registrar_recebimento_cria_lancamento(self):
        conta, _ = gerar_conta_por_os(self.os)
        registrar_recebimento(conta, forma_pagamento='PIX', recebido_em=date.today())
        conta.refresh_from_db()
        self.assertEqual(conta.status, 'PAGA')
        self.assertEqual(conta.lancamentos.count(), 1)

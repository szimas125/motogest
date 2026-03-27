from django.core.management.base import BaseCommand
from core.models import Plano

PLANS = [
    {
        'nome': 'Starter', 'slug': 'starter', 'preco_mensal': '79.99', 'limite_usuarios': 1, 'limite_ordens_mes': 50, 'limite_produtos': 100,
        'descricao': 'Para empresas menores que precisam sair do papel com estoque, OS e nota interna.',
        'recursos': '1 usuário\nAté 50 ordens de serviço por mês\nAté 100 produtos\nClientes, ativos e estoque\nNota interna com impressão\nSuporte por e-mail', 'ordem': 1
    },
    {
        'nome': 'Profissional', 'slug': 'profissional', 'preco_mensal': '149.99', 'limite_usuarios': 3, 'limite_ordens_mes': None, 'limite_produtos': None,
        'descricao': 'O plano mais equilibrado para empresas que querem crescer com equipe e sem limite de OS.',
        'recursos': 'Até 3 usuários\nOrdens de serviço ilimitadas\nProdutos ilimitados\nDashboard com indicadores\nHistórico de movimentações\nPersonalização básica', 'destaque': True, 'ordem': 2
    },
    {
        'nome': 'Premium', 'slug': 'premium', 'preco_mensal': '249.99', 'limite_usuarios': None, 'limite_ordens_mes': None, 'limite_produtos': None,
        'descricao': 'Para operações maiores, com equipe completa e todos os recursos liberados.',
        'recursos': 'Usuários ilimitados\nOrdens de serviço ilimitadas\nProdutos ilimitados\nControle operacional completo\nPrioridade no suporte\nIdeal para múltiplos atendentes', 'ordem': 3
    },
]

class Command(BaseCommand):
    help = 'Cria os planos padrão do EzStock.'

    def handle(self, *args, **options):
        for data in PLANS:
            Plano.objects.update_or_create(slug=data['slug'], defaults=data)
        self.stdout.write(self.style.SUCCESS('Planos padrão criados/atualizados com sucesso.'))

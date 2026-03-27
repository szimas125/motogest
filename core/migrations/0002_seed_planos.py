from django.db import migrations


def seed_planos(apps, schema_editor):
    Plano = apps.get_model('core', 'Plano')
    plans = [
        {
            'nome': 'Starter', 'slug': 'starter', 'preco_mensal': '79.99', 'limite_usuarios': 1, 'limite_ordens_mes': 50, 'limite_produtos': 100,
            'descricao': 'Ideal para empresas menores que querem organizar atendimento, estoque e ordens de serviço.',
            'recursos': '1 usuário\nAté 50 ordens de serviço por mês\nAté 100 produtos\nClientes, ativos e estoque\nNota interna com impressão\nSuporte por e-mail', 'ordem': 1
        },
        {
            'nome': 'Profissional', 'slug': 'profissional', 'preco_mensal': '149.99', 'limite_usuarios': 3, 'limite_ordens_mes': None, 'limite_produtos': None,
            'descricao': 'Perfeito para empresas em crescimento que precisam de mais equipe, produtividade e liberdade operacional.',
            'recursos': 'Até 3 usuários\nOrdens de serviço ilimitadas\nProdutos ilimitados\nDashboard com indicadores\nHistórico de movimentações\nPersonalização básica', 'destaque': True, 'ordem': 2
        },
        {
            'nome': 'Premium', 'slug': 'premium', 'preco_mensal': '249.99', 'limite_usuarios': None, 'limite_ordens_mes': None, 'limite_produtos': None,
            'descricao': 'Indicado para operações mais estruturadas, com maior volume de atendimento e equipe ampliada.',
            'recursos': 'Usuários ilimitados\nOrdens de serviço ilimitadas\nProdutos ilimitados\nControle operacional completo\nPrioridade no suporte\nIdeal para múltiplos atendentes', 'ordem': 3
        },
    ]
    for data in plans:
        Plano.objects.update_or_create(slug=data['slug'], defaults=data)


def unseed_planos(apps, schema_editor):
    Plano = apps.get_model('core', 'Plano')
    Plano.objects.filter(slug__in=['starter', 'profissional', 'premium']).delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunPython(seed_planos, unseed_planos)]

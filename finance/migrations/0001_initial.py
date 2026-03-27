from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('core', '0002_seed_planos'),
        ('workshop', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContaReceber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=160)),
                ('valor', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('vencimento', models.DateField()),
                ('status', models.CharField(choices=[('ABERTA', 'Aberta'), ('PAGA', 'Paga'), ('ATRASADA', 'Atrasada'), ('CANCELADA', 'Cancelada')], default='ABERTA', max_length=20)),
                ('forma_pagamento', models.CharField(blank=True, choices=[('DINHEIRO', 'Dinheiro'), ('PIX', 'PIX'), ('CARTAO', 'Cartão'), ('BOLETO', 'Boleto'), ('TRANSFERENCIA', 'Transferência'), ('OUTRO', 'Outro')], max_length=20)),
                ('recebido_em', models.DateField(blank=True, null=True)),
                ('observacoes', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contas_receber', to='core.empresa')),
                ('ordem_servico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contas_receber', to='workshop.ordemservico')),
            ],
            options={'ordering': ['status', 'vencimento', '-criado_em'], 'verbose_name': 'Conta a receber', 'verbose_name_plural': 'Contas a receber'},
        ),
        migrations.CreateModel(
            name='LancamentoCaixa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('RECEITA', 'Receita'), ('DESPESA', 'Despesa')], max_length=10)),
                ('descricao', models.CharField(max_length=160)),
                ('valor', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('data_lancamento', models.DateField()),
                ('categoria', models.CharField(blank=True, max_length=80)),
                ('observacoes', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('conta_receber', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lancamentos', to='finance.contareceber')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lancamentos_caixa', to='core.empresa')),
            ],
            options={'ordering': ['-data_lancamento', '-criado_em'], 'verbose_name': 'Lançamento de caixa', 'verbose_name_plural': 'Lançamentos de caixa'},
        ),
    ]

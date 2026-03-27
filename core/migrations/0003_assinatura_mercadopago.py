from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_seed_planos'),
    ]

    operations = [
        migrations.AddField(
            model_name='assinatura',
            name='mercado_pago_preapproval_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='mercado_pago_status',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='cartao_ultimos_digitos',
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='cartao_bandeira',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='cartao_cadastrado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

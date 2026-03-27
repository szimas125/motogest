from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_assinatura_mercadopago'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoAssinatura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('origem', models.CharField(default='sistema', max_length=40)),
                ('tipo', models.CharField(max_length=80)),
                ('descricao', models.CharField(blank=True, max_length=255)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('assinatura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eventos', to='core.assinatura')),
            ],
            options={
                'verbose_name': 'Evento da assinatura',
                'verbose_name_plural': 'Eventos da assinatura',
                'ordering': ['-criado_em'],
            },
        ),
    ]

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Cria superusuário automaticamente'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = "admin"
        email = "admin@admin.com"
        password = "admin000"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS("Superuser criado com sucesso!"))
        else:
            self.stdout.write("Superuser já existe.")

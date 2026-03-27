from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.logout_views import sair_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('entrar/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('sair/', sair_view, name='logout'),
    path(
        'senha/esqueci/',
        auth_views.PasswordResetView.as_view(
            template_name='auth/password_reset_form.html',
            email_template_name='auth/password_reset_email.txt',
            subject_template_name='auth/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'senha/enviado/',
        auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'senha/redefinir/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'),
        name='password_reset_confirm',
    ),
    path(
        'senha/concluida/',
        auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('', include('core.urls')),
    path('estoque/', include('inventory.urls')),
    path('empresa/', include('workshop.urls')),
    path('financeiro/', include('finance.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

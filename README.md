# EzStock

Sistema SaaS para empresas que precisam de controle operacional com estoque, ordens de serviço, financeiro, equipe, planos e assinatura.

## Rodando localmente

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Acesse:
- site: `http://127.0.0.1:8000/`
- login: `http://127.0.0.1:8000/entrar/`
- onboarding: `http://127.0.0.1:8000/comecar/`
- painel do SaaS: `http://127.0.0.1:8000/painel-admin/`
- admin técnico: `http://127.0.0.1:8000/admin/`

## Primeiro uso

1. Entre em `/comecar/` e cadastre a empresa.
2. Faça login.
3. Cadastre produtos, clientes e ativos.
4. Abra a primeira ordem de serviço.
5. Em `Planos e assinatura`, cadastre o cartão.

## Variáveis de ambiente úteis

### Produção

```env
DEBUG=false
ALLOWED_HOSTS=seudominio.com,www.seudominio.com
DEFAULT_FROM_EMAIL=noreply@seudominio.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seudominio.com
EMAIL_PORT=587
EMAIL_HOST_USER=seuusuario
EMAIL_HOST_PASSWORD=suasenha
EMAIL_USE_TLS=true
```

### Mercado Pago

```env
MERCADOPAGO_PUBLIC_KEY=
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_WEBHOOK_SECRET=
```

## O que esta versão entrega

- área comercial pública
- onboarding com teste grátis
- painel da empresa
- estoque, clientes, ativos e OS
- financeiro básico
- painel administrativo do SaaS
- tela de status da assinatura
- histórico de eventos da assinatura
- integração pronta para cartão e assinatura

## Antes de publicar

- trocar SQLite por PostgreSQL
- configurar SMTP real
- apontar webhook do gateway para uma URL pública HTTPS
- rodar com `DEBUG=false`
- revisar domínio, backups e SSL

## Testes

```bash
python manage.py test
```

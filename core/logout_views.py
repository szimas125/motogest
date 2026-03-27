from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def sair_view(request):
    logout(request)
    return redirect("home")

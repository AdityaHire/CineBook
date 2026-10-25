from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from axes.decorators import axes_dispatch
from .forms import RegisterForm, LoginForm


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Welcome to Cenebook, {user.name}!")
            return redirect("/")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@axes_dispatch
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(request.GET.get("next", "/"))
    if request.method == "POST":
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            next_url = request.POST.get("next") or request.GET.get("next") or "/"
            return redirect(next_url)
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("/")

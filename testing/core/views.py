from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserPreference
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User

@login_required
def privacy(request):
    return render(request, 'core/privacy.html')

@login_required
def terms(request):
    return render(request, 'core/terms.html')


@login_required
def update_preferences(request):
    if request.method == 'POST' and request.user.is_authenticated:
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)

        # Get submitted values
        username = request.POST.get('username')
        email = request.POST.get('email')
        currency = request.POST.get('currency')
        theme = request.POST.get('theme')

        # ---- Update username ----
        if username and username != request.user.username:
            if User.objects.filter(username=username).exclude(pk=request.user.pk).exists():
                messages.error(request, "⚠ Username already taken!")
            else:
                request.user.username = username
                request.user.save()
                messages.success(request, "👤 Username updated successfully!")

        # ---- Update email ----
        if email and email != request.user.email:
            if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, "⚠ Email already in use!")
            else:
                request.user.email = email
                request.user.save()
                messages.success(request, "📩 Email updated successfully!")

        # ---- Update currency ----
        if currency and currency != prefs.currency:
            prefs.currency = currency
            prefs.save()
            messages.success(request, "💱 Currency updated successfully!")

        # ---- Update theme ----
        if theme and theme != prefs.theme:
            prefs.theme = theme
            prefs.save()
            messages.success(request, "🌗 Theme updated successfully!")

        return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect("settings_view")

@login_required
def settings_view(request):
    prefs, _ = UserPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # ---- Handle Password Change ----
        if "current_password" in request.POST:
            current = request.POST.get("current_password")
            new = request.POST.get("new_password")
            confirm = request.POST.get("confirm_password")

            if not current or not new or not confirm:
                messages.error(request, "⚠ Please fill all password fields!")
            elif not request.user.check_password(current):
                messages.error(request, "❌ Current password is incorrect!")
            elif new != confirm:
                messages.error(request, "❌ New passwords do not match!")
            else:
                request.user.set_password(new)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "🔒 Password updated successfully!")

            return redirect("settings_view")

    return render(request, "core/settings.html", {"prefs": prefs})
from .models import UserPreference

def user_preferences(request):
    if request.user.is_authenticated:
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        return {
            "user_theme": prefs.theme,
            "user_currency": prefs.currency,
        }
    return {
        "user_theme": "dark",
        "user_currency": "INR",
    }

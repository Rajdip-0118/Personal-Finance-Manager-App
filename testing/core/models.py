from django.db import models
from django.conf import settings
from django.db import models

class UserPreference(models.Model):
    THEME_CHOICES = [("light", "Light"), ("dark", "Dark")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.CharField(max_length=10, default="₹")
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="dark")

    def __str__(self):
        return f"{self.user.username} Preferences"

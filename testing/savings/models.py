from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class SurplusTracker(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_surplus = models.DecimalField(max_digits=21, decimal_places=2, default=0)
    last_rollover_month = models.IntegerField(null=True, blank=True)  # NEW

    def __str__(self):
        return f"{self.user.username} Surplus Tracker"

class SavingsGoal(models.Model):
    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="savings_goals")
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=21, decimal_places=2)
    current_amount = models.DecimalField(max_digits=21, decimal_places=2, default=0)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Low")

    def progress(self) -> float:
        if self.target_amount == 0:
            return 0.0
        return round((self.current_amount / self.target_amount) * 100, 2)

    def remaining_amount(self) -> Decimal:
        return max(self.target_amount - self.current_amount, Decimal(0))

    def is_completed(self) -> bool:
        return self.current_amount >= self.target_amount

    def __str__(self):
        return f"{self.name} ({self.current_amount}/{self.target_amount})"

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
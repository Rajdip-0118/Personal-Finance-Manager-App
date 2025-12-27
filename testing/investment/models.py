from django.db import models
from django.contrib.auth.models import User
from datetime import date
from django.utils import timezone
from decimal import Decimal

class Investment(models.Model):
    INVESTMENT_TYPES = [
        ('Stock', 'Stock'),
        ('Mutual Fund', 'Mutual Fund'),
        ('FD', 'Fixed Deposit'),
        ('RD', 'Recurring Deposit'),
        ('Bond', 'Bond'),
        ('ETF', 'Exchange-Traded Fund'),
        ('Pension', 'Pension Fund'),
        ('Gold', 'Gold'),
        ('Crypto', 'Cryptocurrency'),
        ('Real Estate', 'Real Estate'),
        ('Other', 'Other'),
    ]

    FREQUENCY_CHOICES = [

        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Biannual', 'Biannual'),
        ('Yearly', 'Yearly'),
     
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    investment_type = models.CharField(max_length=50, choices=INVESTMENT_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expected_return = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='Yearly') 
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Completed', 'Completed')], default="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(default=timezone.now)

    @property
    def estimated_value(self):
        """Calculate projected maturity value based on expected return and duration."""
        if self.expected_return:
            years = Decimal('1')
            if self.end_date:
                days = (self.end_date - self.start_date).days
                years = Decimal(max(1, days / 365))
            return round(self.amount + (self.amount * (self.expected_return / Decimal('100')) * years), 2)
        return self.amount

    @property
    def profit_estimate(self):
        """Estimated profit from this investment."""
        return round(self.estimated_value - self.amount, 2)

    def is_matured(self):
        """Check if the investment has reached its maturity date."""
        return self.end_date and date.today() >= self.end_date

    def __str__(self):
        return f"{self.name} ({self.investment_type})"

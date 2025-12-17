from django.conf import settings
from django.utils import timezone
from django.db import models
from investment.models import Investment

# Create your models here.
class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Housing & Utilities', 'Housing & Utilities'),
        ('Transportation', 'Transportation'),
        ('Food & Dining', 'Food & Dining'),
        ('Personal & Shopping', 'Personal & Shopping'),
        ('Health & Fitness', 'Health & Fitness'),
        ('Entertainment & Leisure', 'Entertainment & Leisure'),
        ('Education', 'Education'),
        ('Financial', 'Financial'),
        ('Travel & Vacation', 'Travel & Vacation'),
        ('Miscellaneous', 'Miscellaneous'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    investment = models.ForeignKey('investment.Investment', on_delete=models.CASCADE, null=True, blank=True, related_name='expenses')  # ← new
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=21, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    recurring = models.ForeignKey('RecurringExpense', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} - {self.amount} ({self.category})"

class Income(models.Model):
    CATEGORY_CHOICES = [
        ('Salary', 'Salary'),
        ('Business', 'Business'),
        ('Freelance', 'Freelance'),
        ('Rental Income', 'Rental Income'),
        ('Dividends', 'Dividends'),
        ('Interest Income', 'Interest Income'),
        ('Gifts & Donations', 'Gifts & Donations'),
        ('Refunds', 'Refunds'),
        ('Retirement Income', 'Retirement Income'),
        ('Bonus & Incentives', 'Bonus & Incentives'),
        ('Other Income', 'Other Income'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    investment = models.ForeignKey('investment.Investment', on_delete=models.CASCADE, null=True, blank=True, related_name='incomes')  # ← new
    source = models.CharField(max_length=100)  
    amount = models.DecimalField(max_digits=21, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    recurring = models.ForeignKey('RecurringIncome', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.source} - {self.amount} ({self.category})"

# models.py

class RecurringIncome(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("biannually", "Biannually"),
        ("yearly", "Yearly"),
    ]
    CATEGORY_CHOICES = [
        ("Salary", "Salary"),
        ("Business", "Business"),
        ("Freelance", "Freelance"),
        ("Rental Income", "Rental Income"),
        ("Dividends", "Dividends"),
        ("Interest Income", "Interest Income"),
        ("Retirement Income", "Retirement Income"),
        ("Other Income", "Other Income")
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    source = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=21, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("active", "Active"), ("inactive", "Inactive")], default="active")

class RecurringExpense(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("biannually", "Biannually"),
        ("yearly", "Yearly"),
    ]
    CATEGORY_CHOICES = [
        ("Housing & Utilities", "Housing & Utilities"),
        ("Transportation", "Transportation"),
        ("Food & Dining", "Food & Dining"),
        ("Health & Fitness", "Health & Fitness"),
        ("Entertainment & Leisure", "Entertainment & Leisure"),
        ("Education", "Education"),
        ("Financial", "Financial"),
        ("Miscellaneous", "Miscellaneous")
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=21, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("active", "Active"), ("inactive", "Inactive")], default="active")
    
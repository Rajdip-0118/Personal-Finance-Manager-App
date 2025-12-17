# budget/models.py
from django.db import models
from django.conf import settings
from decimal import Decimal
from django.db.models import Sum
from finance.models import Income, RecurringIncome, Expense
from dateutil.relativedelta import relativedelta

FREQ_RELATIVE = {
    "daily": lambda d: d + relativedelta(days=1),
    "weekly": lambda d: d + relativedelta(weeks=1),
    "monthly": lambda d: d + relativedelta(months=1),
    "quarterly": lambda d: d + relativedelta(months=3),
    "biannually": lambda d: d + relativedelta(months=6),
    "annually": lambda d: d + relativedelta(years=1),
}


def _calculate_recurring_total(start_date, end_date, user):
    total = Decimal("0.00")
    recurring_qs = RecurringIncome.objects.filter(user=user)
    for r in recurring_qs:
        freq = (r.frequency or "").lower()
        next_date = r.next_due_date
        r_end = r.end_date or end_date
        if not next_date:
            continue

        # advance until in range
        while next_date < start_date:
            next_date = FREQ_RELATIVE.get(freq, lambda d: d)(next_date)

        while next_date <= end_date and next_date <= r_end:
            total += r.amount
            next_date = FREQ_RELATIVE.get(freq, lambda d: d)(next_date)
    return total


class Budget(models.Model):
    """
    Percentage-based budget: store the percent of available income the user wants
    to allocate for this budget period. The actual monetary total is computed on the fly
    from the user's incomes (one-time + recurring) in the period.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    name = models.CharField(max_length=100)

    # store budget as percentage of available income (0.00 - 100.00)
    total_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'))

    start_date = models.DateField()
    end_date = models.DateField()

    # is_zero_based removed per request

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    def _get_available_income(self):
        """Return Decimal total of one-time income + recurring incomes for this budget period."""
        income_total = Income.objects.filter(
            user=self.user,
            date__range=[self.start_date, self.end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

        recurring_total = _calculate_recurring_total(self.start_date, self.end_date, self.user)

        return (income_total or Decimal("0.00")) + (recurring_total or Decimal("0.00"))

    @property
    def total_amount(self):
        """Compute actual budget amount = available_income * (total_percent / 100)."""
        available = self._get_available_income()
        return (available * (self.total_percent or Decimal('0')) / Decimal('100')).quantize(Decimal('0.01'))

    def total_spent(self):
        """Total spent across all categories in this budget period (sums expenses by category membership)."""
        expenses = Expense.objects.filter(user=self.user, date__range=[self.start_date, self.end_date])
        return sum(exp.amount for exp in expenses) or Decimal("0.00")

    def remaining(self):
        return self.total_amount - self.total_spent()


class BudgetCategory(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="categories")
    category = models.CharField(max_length=50, choices=Expense.CATEGORY_CHOICES)

    # store category as percent of the budget (0.00 - 100.00)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.category} ({self.budget.name})"

    def limit_amount(self):
        """Return the monetary limit for this category based on budget.total_amount and percent."""
        return (Decimal(self.percent or 0) / Decimal('100')) * Decimal(self.budget.total_amount)

    def spent(self):
        expenses = Expense.objects.filter(
            user=self.budget.user,
            category=self.category,
            date__range=[self.budget.start_date, self.budget.end_date]
        )
        return sum(exp.amount for exp in expenses) or Decimal("0.00")

    def remaining(self):
        return Decimal(self.limit_amount()) - self.spent()

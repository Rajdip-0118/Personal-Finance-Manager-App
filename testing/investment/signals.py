from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Investment
from finance.models import Expense, Income
from decimal import Decimal, ROUND_HALF_UP, getcontext


getcontext().prec = 28

def choose_income_category(inv_type):
    t = (inv_type or "").lower()
    if t in ["fd", "fixed deposit", "rd", "recurring deposit", "bond"]:
        return "Interest Income"
    if t in ["stock", "mutual fund", "etf", "crypto", "share"]:
        return "Dividends"
    if t in ["real estate", "pension"]:
        return "Rental Income"
    if t in ["gold"]:
        return "Other Income"
    return "Other Income"


def _to_decimal(value):
    if value is None:
        return Decimal('0')
    return value if isinstance(value, Decimal) else Decimal(str(value))

def _calculate_estimated_value(amount, expected_return, start_date, end_date, investment_type=None, frequency=None):
    """
    amount: Decimal or numeric
    expected_return: Decimal or numeric (annual percent, e.g. 4 for 4%)
    investment_type: string like 'fd', 'rd', 'bond', 'stock' (optional)
    frequency: optional override: 'Monthly','Quarterly','Biannual','Yearly'
    """
    amount = _to_decimal(amount)
    expected_return = _to_decimal(expected_return or Decimal('0'))

    if not start_date or not end_date or expected_return == 0:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    days = (end_date - start_date).days
    if days <= 0:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    years = Decimal(days) / Decimal("365")

    # Frequency defaults by type
    type_based_freq = {
        'fd': 'Quarterly',
        'fixed deposit': 'Quarterly',
        'bond': 'Biannual',
        'rd': 'Monthly',
        'recurring deposit': 'Monthly',
        'stock': 'Yearly',
        'mutual fund': 'Yearly',
        'etf': 'Yearly',
        'crypto': 'Yearly',
        'pension': 'Yearly',
        'real estate': 'Yearly',
        'gold': 'Yearly',
        'other': 'Yearly',
    }

    freq_map = {
        'Monthly': Decimal('12'),
        'Quarterly': Decimal('4'),
        'Biannual': Decimal('2'),
        'Yearly': Decimal('1'),
    }

    investment_type_lower = (investment_type or "").lower()
    auto_freq = type_based_freq.get(investment_type_lower, 'Yearly')
    final_frequency = frequency or auto_freq
    comp_per_year = freq_map.get(final_frequency, Decimal('1'))


    rate_per_period = (expected_return / Decimal('100')) / comp_per_year
    periods = comp_per_year * years

    if 'rd' in investment_type_lower or 'recurring' in investment_type_lower:

        months = int((years * Decimal('12')).to_integral_value(rounding=ROUND_HALF_UP))
        if months <= 0 or rate_per_period == 0:
            return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        monthly_rate = (expected_return / Decimal('100')) / Decimal('12')
   
        value = amount * (((Decimal('1') + monthly_rate) ** months - Decimal('1')) / monthly_rate)
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    value = amount * ((Decimal('1') + rate_per_period) ** (periods))
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)



@receiver(pre_save, sender=Investment)
def track_old_name(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Investment.objects.get(pk=instance.pk)
            instance._old_name = old.name
        except Investment.DoesNotExist:
            instance._old_name = None
    else:
        instance._old_name = None


@receiver(post_save, sender=Investment)
def sync_investment_records(sender, instance, created, **kwargs):
    old_name = getattr(instance, "_old_name", None)
    name_changed = old_name and old_name != instance.name


    expense_name = f"Investment in {instance.name}"

    expense, _ = Expense.objects.get_or_create(
        user=instance.user,
        investment=instance,  
        defaults={
            "name": expense_name,
            "amount": instance.amount,
            "date": instance.start_date or timezone.now().date(),
            "category": "Financial",
        },
    )

    updated_fields = []
    expected_date = instance.start_date or timezone.now().date()
    if _to_decimal(expense.amount) != _to_decimal(instance.amount):
        expense.amount = instance.amount
        updated_fields.append("amount")
    if expense.date != expected_date:
        expense.date = expected_date
        updated_fields.append("date")
    if name_changed:
        expense.name = expense_name
        updated_fields.append("name")
    if updated_fields:
        expense.save(update_fields=updated_fields)

    income_name = f"Investment Maturity - {instance.name}"
    income = Income.objects.filter(user=instance.user, investment=instance).first()  

    if instance.status == "Completed" and instance.end_date:
        amount = _to_decimal(instance.amount)
        expected_return = _to_decimal(instance.expected_return or Decimal('0'))

        investment_type = getattr(instance, "investment_type", None)
        frequency = getattr(instance, "frequency", None)

        est_value = _calculate_estimated_value(amount, expected_return, instance.start_date, instance.end_date, investment_type, frequency)

        category = choose_income_category(investment_type)

        if income:
            updated = False
          
            if _to_decimal(income.amount) != est_value:
                income.amount = est_value
                updated = True
            if income.date != instance.end_date:
                income.date = instance.end_date
                updated = True
            if income.source != income_name:
                income.source = income_name
                updated = True
            if updated:
                income.save(update_fields=["amount", "date", "source"])
        else:
            Income.objects.create(
                user=instance.user,
                investment=instance, 
                source=income_name,
                amount=est_value,
                date=instance.end_date,
                category=category,
            )

    elif income and instance.status != "Completed":
        income.delete()


@receiver(post_delete, sender=Investment)
def delete_linked_records(sender, instance, **kwargs):
    Expense.objects.filter(investment=instance).delete()
    Income.objects.filter(investment=instance).delete()


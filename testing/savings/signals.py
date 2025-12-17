
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from finance.models import Income, Expense

from .utils import surplus_rollover


def recalc_goal_allocations(user):
    surplus_rollover(user)

# -------------------------
# Income Signals
# -------------------------
@receiver(post_save, sender=Income)
def income_saved(sender, instance, created, **kwargs):
    recalc_goal_allocations(instance.user)


@receiver(post_delete, sender=Income)
def income_deleted(sender, instance, **kwargs):
    recalc_goal_allocations(instance.user)


# -------------------------
# Expense Signals
# -------------------------
@receiver(post_save, sender=Expense)
def expense_saved(sender, instance, created, **kwargs):
    recalc_goal_allocations(instance.user)


@receiver(post_delete, sender=Expense)
def expense_deleted(sender, instance, **kwargs):
    recalc_goal_allocations(instance.user)










  
from datetime import date
from decimal import Decimal
from django.db.models import Sum, F, Case, When,IntegerField
from dateutil.relativedelta import relativedelta
from finance.models import Income, Expense
from .models import SavingsGoal, SurplusTracker
from ml.probability import predict_goal_probability
# -------------------------
# Goal Probability
# -------------------------
MESSAGES = {
    "completed_prob": "--",
    "completed_deadline": "--",
    "deadline_passed_prob": "Deadline passed, please extend the deadline",
    "deadline_this_month_prob": "Unable to meet deadline this month",
    "more_than_30_years": "More than 30 years",
}

MAX_DISPLAY_YEARS = 30


def get_goal_probability(user, goal):
    today = date.today()

    # ✅ 1. Goal completed
    if goal.is_completed():
        return {
            "probability": MESSAGES["completed_prob"],
            "suggested_deadline": MESSAGES["completed_deadline"],
        }

    # ✅ 2. Deadline passed
    if goal.deadline and goal.deadline < today:
        return {
            "probability": MESSAGES["deadline_passed_prob"],
            "suggested_deadline": _format_suggested_deadline(goal.deadline, today),
        }

    # ✅ 3. Deadline in current month → show ML predicted deadline
    if goal.deadline and goal.deadline.year == today.year and goal.deadline.month == today.month:
        ml_result = predict_goal_probability(user, goal)
        return {
            "probability": MESSAGES["deadline_this_month_prob"],
            "suggested_deadline": _format_suggested_deadline(ml_result.get("suggested_deadline"), today),
        }

    # ✅ 4. Incomplete goal → get raw ML output
    ml_result = predict_goal_probability(user, goal)
    raw_prob = ml_result.get("probability", 0)
    raw_deadline = ml_result.get("suggested_deadline", None)

    # ✅ Cap at 100
    if isinstance(raw_prob, (int, float)):
        raw_prob = min(100, round(raw_prob, 2))

    return {
        "probability": raw_prob,
        "suggested_deadline": _format_suggested_deadline(raw_deadline, today),
    }


def _format_suggested_deadline(sd, today):
    """Format deadline, cap at 30 years from today."""
    if not sd or sd == "--":
        return "--"

    if isinstance(sd, date):
        max_date = today + relativedelta(years=MAX_DISPLAY_YEARS)
        if sd > max_date:
            return MESSAGES["more_than_30_years"]
        return sd.strftime("%d %b %Y")  # optional: show Month Year for clarity

    return sd

# -------------------------
# Monthly Surplus
# -------------------------
def calculate_monthly_surplus(user, year, month):
    total_income = Income.objects.filter(
        user=user, date__year=year, date__month=month
    ).aggregate(Sum("amount"))["amount__sum"] or 0
    total_expense = Expense.objects.filter(
        user=user, date__year=year, date__month=month
    ).aggregate(Sum("amount"))["amount__sum"] or 0
    return max(Decimal(total_income) - Decimal(total_expense), Decimal(0))


# -------------------------
# Goal Deletion / Refund
# -------------------------
def delete_goals_with_refund(user, goals_queryset):
    tracker, _ = SurplusTracker.objects.get_or_create(user=user)
    refund = goals_queryset.aggregate(total=Sum("current_amount"))["total"] or 0
    tracker.last_surplus += Decimal(refund)
    tracker.save()
    count = goals_queryset.count()
    goals_queryset.delete()
    return count, refund

def surplus_rollover(user):
    tracker, _ = SurplusTracker.objects.get_or_create(user=user)
    today = date.today()
    first_day_current_month = date(today.year, today.month, 1)

    total_surplus = Decimal("0")

    first_income = Income.objects.filter(user=user).order_by("date").first()
    if first_income:
        cursor = date(first_income.date.year, first_income.date.month, 1)
    else:
        cursor = first_day_current_month

    # ✅ ONLY past months
    while cursor < first_day_current_month:
        total_surplus += calculate_monthly_surplus(
            user, cursor.year, cursor.month
        )
        cursor += relativedelta(months=1)

    total_surplus = max(total_surplus, Decimal("0"))

    # Reset goals
    SavingsGoal.objects.filter(user=user).update(current_amount=0)

    # Allocate accumulated balance to goals
    remaining = total_surplus
    goals = SavingsGoal.objects.filter(
        user=user,
        deadline__gte=today
    ).order_by(
        "deadline",
        Case(
            When(priority="High", then=0),
            When(priority="Medium", then=1),
            When(priority="Low", then=2),
            default=3,
            output_field=IntegerField(),
        ),
        "created_at",
        "id"
    )

    for goal in goals:
        if remaining <= 0:
            break
        allocation = min(remaining, goal.target_amount)
        goal.current_amount = allocation
        goal.save(update_fields=["current_amount"])
        remaining -= allocation

    tracker.last_surplus = remaining
    tracker.save(update_fields=["last_surplus"])

    return {
        "accumulated_balance": tracker.last_surplus,  # ✅ past months only
        "current_balance": calculate_monthly_surplus(
            user, today.year, today.month
        ),  # ✅ current month only
    }


def reallocate_on_new_goal(user):
    """
    Trigger full reallocation when a new goal is added.
    Uses current surplus + all already allocated amounts, reorders goals by priority,
    and distributes money from scratch.
    """


    today = date.today()
    tracker, _ = SurplusTracker.objects.get_or_create(user=user)

    # 1️⃣ Calculate total surplus including already allocated
    total_allocated = SavingsGoal.objects.filter(user=user).aggregate(
        total=Sum("current_amount")
    )["total"] or 0
    total_surplus = tracker.last_surplus + Decimal(total_allocated)

    # 2️⃣ Reset all active goals' current_amount to 0
    goals = SavingsGoal.objects.filter(user=user)
    for goal in goals:
        goal.current_amount = 0
        goal.save()

    # 3️⃣ Order goals by priority rules
    far_future = date(9999, 12, 31)
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    def _effective_deadline(g):
        return g.deadline if g.deadline else far_future

    goal_list = list(goals)
    goal_list.sort(key=lambda g: (
        _effective_deadline(g),
        priority_rank.get(getattr(g, "priority", "Low"), 3),
        getattr(g, "created_at", date.min),
        g.id
    ))

    # 4️⃣ Allocate total_surplus sequentially
    remaining = float(total_surplus)
    for goal in goal_list:
        needed = float(goal.target_amount)
        allocation = min(needed, remaining)
        goal.current_amount += Decimal(allocation)
        goal.save()
        remaining -= allocation
        if remaining <= 0:
            break

    # 5️⃣ Update tracker with leftover
    tracker.last_surplus = Decimal(max(0, remaining))
    tracker.save()
    return {
        "accumulated_balance": tracker.last_surplus,
        "current_balance": total_surplus - Decimal(tracker.last_surplus)  # optional
    }


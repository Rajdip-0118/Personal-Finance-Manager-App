# ml/probability.py

from datetime import date
from dateutil.relativedelta import relativedelta
import math
import numpy as np
from sklearn.linear_model import LinearRegression
from django.db.models import F
from savings.models import SavingsGoal


# Constants
MAX_DISPLAY_YEARS = 30
DEFAULT_LOOKBACK_MONTHS = 12
MIN_REGRESSION_MONTHS = 3
LEEWAY_FACTOR = 1.05


def _get_last_n_months_surplus(user, n=DEFAULT_LOOKBACK_MONTHS):
    """
    Get the last n months of surplus for the user.
    """
    from savings.utils import calculate_monthly_surplus

    today = date.today()
    surpluses = []

    for i in range(n, 0, -1):
        month_date = today - relativedelta(months=i)
        surplus = calculate_monthly_surplus(user, month_date.year, month_date.month)
        surpluses.append(float(surplus))

    return surpluses


def _estimate_monthly_slope(user):
    """
    Estimate the monthly savings slope based on past surplus.
    """
    last = _get_last_n_months_surplus(user)
    if not last:
        return 0.0

    n = len(last)
    avg = float(np.mean(last))

    if n >= MIN_REGRESSION_MONTHS:
        X = np.arange(n).reshape(-1, 1)
        y = np.cumsum(last)
        try:
            model = LinearRegression().fit(X, y)
            slope = float(model.coef_[0])
        except Exception:
            slope = avg
        return max(0.0, max(slope, avg))

    return max(0.0, avg)


def _months_between(a: date, b: date):
    """
    Calculate the number of months between two dates.
    """
    return max((b.year - a.year) * 12 + (b.month - a.month), 0)


def predict_goal_probability(user, goal: SavingsGoal):
    """
    Predict the probability of achieving a savings goal.
    """
    today = date.today()

    # Remaining amount check
    remaining = float(goal.remaining_amount())
    if remaining <= 0:
        return {"probability": 100.0, "suggested_deadline": "--"}

    slope = _estimate_monthly_slope(user)
    if slope <= 0:
        return {"probability": 0.0, "suggested_deadline": "--"}

    # Get all other active goals of the user
    higher_goals = SavingsGoal.objects.filter(
        user=user,
        current_amount__lt=F("target_amount")
    ).exclude(id=goal.id)

    far_future = date(9999, 12, 31)

    def _effective_deadline(g):
        return g.deadline if g.deadline else far_future

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}

    # Sort goals by deadline, priority, creation date, and ID
    goals_list = sorted(
        higher_goals,
        key=lambda g: (
            _effective_deadline(g),
            priority_rank.get(getattr(g, "priority", "Low"), 3),
            getattr(g, "created_at", date.min),
            g.id
        )
    )

    # Filter only goals ahead of the current goal
    priors = [
        h for h in goals_list
        if (_effective_deadline(h),
            priority_rank.get(h.priority, 3),
            getattr(h, "created_at", date.min),
            h.id) < (_effective_deadline(goal),
                     priority_rank.get(goal.priority, 3),
                     getattr(goal, "created_at", date.min),
                     goal.id)
    ]

    # Calculate months until the goal's deadline
    months_to_deadline = _months_between(today, date(goal.deadline.year, goal.deadline.month, 1)) \
        if goal.deadline else 999

    # Account for prior goals
    months_consumed = 0
    for prior in priors:
        prior_remaining = float(prior.target_amount - prior.current_amount)
        if prior_remaining <= 0:
            continue
        months_needed = math.ceil((prior_remaining / slope) * LEEWAY_FACTOR)
        months_consumed += months_needed
        if months_consumed >= months_to_deadline:
            return {"probability": 0.0, "suggested_deadline": "--"}

    # Calculate probability for the current goal
    months_available = max(months_to_deadline - months_consumed, 0)
    projected_total = float(goal.current_amount) + slope * months_available
    prob = round(min(projected_total / float(goal.target_amount), 1.0) * 100, 2)

    # Suggested deadline calculation
    sd = "--"
    if prob < 100:
        months_to_finish = math.ceil((remaining / slope) * LEEWAY_FACTOR) + months_consumed
        try:
            sd = today + relativedelta(months=months_to_finish)
        except Exception:
            sd = "--"

    return {"probability": prob, "suggested_deadline": sd}


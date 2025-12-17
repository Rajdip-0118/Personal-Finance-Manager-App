import pandas as pd
import numpy as np
from django.utils.timezone import now
from sklearn.linear_model import LinearRegression
from finance.models import Expense


# ---- Forecast helper ----
def linear_regression_forecast(df_input, days_in_future):
    """
    Linear regression forecast with 3-tier logic:
    - <1 row  => "Insufficient data"
    - 1–19 rows => average-based forecast
    - >=20 rows => linear regression forecast
    """
    if df_input.empty:
        return "Insufficient data"

    n = len(df_input)
    df_input = df_input.copy()
    df_input["day_index"] = np.arange(n)
    y = df_input["y"].values

    # --- Fallback: use average when data is limited ---
    if n < 20:
        avg_daily = max(float(np.mean(y)), 0)
        return round(avg_daily * days_in_future, 2)

    # --- Linear regression for >=20 samples ---
    X = df_input[["day_index"]].values
    model = LinearRegression()
    model.fit(X, y)

    future_days = np.arange(n, n + days_in_future).reshape(-1, 1)
    preds = model.predict(future_days)

    avg_daily = max(y.mean(), 0)
    preds = np.maximum(preds, avg_daily)

    return round(float(preds.sum()), 2)


# ---- Load and preprocess expenses ----
def get_daily_expenses(user):
    """
    Returns a DataFrame of daily expenses for the given user.
    Columns: ['ds', 'y']
    """
    expenses_qs = Expense.objects.filter(user=user).order_by("date")
    if not expenses_qs.exists():
        return pd.DataFrame(columns=["ds", "y"])

    df = pd.DataFrame(list(expenses_qs.values("date", "amount")))
    df.rename(columns={"date": "ds", "amount": "y"}, inplace=True)
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = df["y"].astype(float)

    # Aggregate daily totals and fill missing days with 0
    df_daily = (
        df.groupby("ds", as_index=False)["y"].sum()
        .set_index("ds")
        .resample("D")
        .sum()
        .fillna(0)
        .reset_index()
    )
    return df_daily


# ---- Helper: Drop missing (zero-activity) months ----
def drop_missing_months(df):
    """
    Removes months where total spending is zero.
    Prevents regression from being skewed by fake 'zero months'.
    """
    df["month"] = df["ds"].dt.to_period("M")
    valid_months = df.groupby("month")["y"].sum()
    valid_months = valid_months[valid_months > 0].index
    cleaned_df = df[df["month"].isin(valid_months)].drop(columns="month")
    return cleaned_df


# ---- Generic month forecast ----
def forecast_month(df_daily_all, current_month, include_current=False):
    """
    Forecasts spending for the current or next month based on historical data.
    include_current=True means use current month data for next month's forecast.
    """
    # Clean data
    df_daily_all = drop_missing_months(df_daily_all)

    # Separate previous and current months
    prev_months_df = df_daily_all[df_daily_all["ds"].dt.to_period("M") < current_month]
    current_month_df = df_daily_all[df_daily_all["ds"].dt.to_period("M") == current_month]

    if include_current:
        # NEXT month forecast: use both previous and current data
        df_train = pd.concat([prev_months_df, current_month_df], ignore_index=True)
        target_month = current_month + 1
    else:
        # THIS month forecast: use only previous months
        df_train = prev_months_df
        target_month = current_month

    if df_train.empty:
        return "Insufficient data"

    days_in_target_month = target_month.days_in_month
    return linear_regression_forecast(df_train, days_in_target_month)


# ---- Spent so far (Current Month) ----
def spent_so_far_this_month(df_daily_all, current_month):
    """
    Returns total spent so far in the current month.
    """
    this_month_df = df_daily_all[df_daily_all["ds"].dt.to_period("M") == current_month]
    if this_month_df.empty:
        return "Nothing spent so far"

    spent_sum = round(this_month_df["y"].sum(), 2)
    return spent_sum if spent_sum > 0 else "Nothing spent so far"


# ---- Wrapper ----
def get_user_expense_forecast(user, forecast_date=None):
    """
    Returns user's expense summary:
    - spent_so_far: amount spent this month
    - this_month_expected: forecast for current month
    - next_month_expected: forecast for next month
    """
    today = forecast_date or now().date()
    current_month = pd.Period(f"{today.year}-{today.month:02d}")

    df_daily_all = get_daily_expenses(user)
    if df_daily_all.empty:
        return {
            "spent_so_far": "Nothing spent so far",
            "this_month_expected": "Insufficient data",
            "next_month_expected": "Insufficient data",
        }

    spent = spent_so_far_this_month(df_daily_all, current_month)
    this_month = forecast_month(df_daily_all, current_month, include_current=False)
    next_month = forecast_month(df_daily_all, current_month, include_current=True)

    return {
        "spent_so_far": spent,
        "this_month_expected": this_month,
        "next_month_expected": next_month,
    }
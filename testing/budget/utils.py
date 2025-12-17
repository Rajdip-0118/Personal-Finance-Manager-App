# # budget/utils.py
# from decimal import Decimal
# from django.contrib import messages
# from django.utils import timezone
# from .models import Budget, BudgetCategory

# def check_budget_warnings(request, expense):
#     """
#     Check budget warnings for the given expense's category.
#     Uses percentage-based BudgetCategory limits.
#     """
#     user = request.user
#     category_name = expense.category
#     today = timezone.now().date()

#     # Find active budgets that include this category
#     active_budgets = Budget.objects.filter(
#         user=user,
#         start_date__lte=today,
#         end_date__gte=today,
#         categories__category=category_name
#     ).distinct()

#     for budget in active_budgets:
#         # Get the category object in this budget
#         cat_obj = budget.categories.filter(category=category_name).first()
#         if not cat_obj:
#             continue  # Category not part of this budget

#         spent = cat_obj.spent()
#         limit = cat_obj.limit_amount()  # compute based on percentage of budget

#         # Category-level warning
#         if spent > limit:
#             messages.warning(
#                 request,
#                 f"⚠️ You have exceeded the limit for category '{category_name}' "
#                 f"in budget '{budget.name}'. Spent: {spent}, Limit: {limit}"
#             )

#         # Total budget warning
#         total_spent = sum(c.spent() for c in budget.categories.all())
#         total_limit = budget.total_amount
#         if total_spent > total_limit:
#             messages.error(
#                 request,
#                 f"🚨 Your total spending ({total_spent}) exceeded the budget '{budget.name}' limit ({total_limit})!"
#             )
# budget/utils.py
from decimal import Decimal
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import Budget, BudgetCategory

def check_budget_warnings(request, expense):
    """
    Check budget warnings for the given expense's category.
    Uses percentage-based BudgetCategory limits.

    Additionally: send an email alert to the user ONLY when the
    total budget spending crosses from <= 100% to > 100% due to this expense.
    """
    user = request.user
    category_name = expense.category
    today = timezone.now().date()

    # Find active budgets that include this category
    active_budgets = Budget.objects.filter(
        user=user,
        start_date__lte=today,
        end_date__gte=today,
        categories__category=category_name
    ).distinct()

    for budget in active_budgets:
        # Get the category object in this budget
        cat_obj = budget.categories.filter(category=category_name).first()
        if not cat_obj:
            continue  # Category not part of this budget

        spent = cat_obj.spent()
        limit = cat_obj.limit_amount()  # compute based on percentage of budget

        # Category-level warning
        if spent > limit:
            messages.warning(
                request,
                f"⚠️ You have exceeded the limit for category '{category_name}' "
                f"in budget '{budget.name}'. Spent: {spent}, Limit: {limit}"
            )

        # Total budget warning
        # total_spent includes this expense (assumes expense is already counted in spent())
        total_spent = sum(c.spent() for c in budget.categories.all())
        total_limit = Decimal(budget.total_amount)

        # Basic error/warning if already over budget
        if total_spent > total_limit:
            messages.error(
                request,
                f"🚨 Your total spending ({total_spent}) exceeded the budget '{budget.name}' limit ({total_limit})!"
            )

        # --- EMAIL ALERT only when crossing 100% because of this expense ---
        try:
            # Ensure expense.amount is Decimal
            expense_amt = Decimal(getattr(expense, "amount", 0) or 0)

            # Compute what the total was before applying this expense
            prev_total_spent = (total_spent - expense_amt)
            # Guard against negative values
            if prev_total_spent < Decimal('0'):
                prev_total_spent = Decimal('0')

            crossed = (prev_total_spent <= total_limit) and (total_spent > total_limit)

            if crossed:
                user_email = getattr(user, "email", None)
                if user_email:
                    subject = f"Personal Finance Manager – Budget '{budget.name}' Exceeded"
                    message = (
                        f"Hello {user.get_full_name() or user.username},\n\n"
                        f"This is an alert from your Personal Finance Manager app.\n\n"
                        f"Your budget \"{budget.name}\" has now exceeded its 100% spending limit.\n\n"
                        f"• Budget Limit: {total_limit}\n"
                        f"• Previous Total: {prev_total_spent}\n"
                        f"• New Expense: {expense_amt} (Category: {category_name})\n"
                        f"• Current Total: {total_spent}\n\n"
                        f"We recommend reviewing your recent expenses to stay on track.\n\n"
                        f"— Personal Finance Manager"
                    )
                    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
                    # send_mail returns the number of successfully delivered messages (1 if OK)
                    send_mail(subject, message, from_email, [user_email], fail_silently=False)
                else:
                    # Optionally: log or add a message if user has no email configured
                    messages.info(request, "Budget exceeded but no user email configured for alert.")
        except Exception:
            # Avoid breaking the flow if email sending fails; add a non-fatal message
            messages.info(request, "Budget exceeded — failed to send email alert (check email settings).")

from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Sum
from .models import Income, Expense


def get_totals(user):
    """Return total income and total expense for a user."""
    total_income = Income.objects.filter(user=user).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_expense = Expense.objects.filter(user=user).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return total_income, total_expense


def can_afford_expense(user, amount):
    """Check if adding this expense keeps (income - expense) ≥ 0."""
    total_income, total_expense = get_totals(user)
    return (total_expense + Decimal(amount)) <= total_income


BULK_INCOME_VIEW_NAMES = {
    "bulk_delete_income",
    "delete_selected_incomes",
}

BYPASS_PATH_KEYWORDS = (
    "upload",           
    "import",           
    "csv",              

)


class BalanceProtectionMiddleware:
    """
    🧠 Global safeguard for income & expense operations.

    ✅ Prevents only operations that worsen the balance:
        - Adding or increasing expenses beyond available income.
        - Deleting or reducing incomes that would make expenses exceed income.
    ✅ Allows:
        - Decreasing expenses.
        - Increasing incomes.
    ✅ Prevents full income deletions if expenses exist.
    ✅ Skips CSV uploads & recurring automation endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _block(self, request, msg):
        messages.error(request, msg)
        return redirect(request.META.get("HTTP_REFERER", "dashboard"))

    def __call__(self, request):
        if not request.user.is_authenticated or request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return self.get_response(request)

        resolver = getattr(request, "resolver_match", None)
        view_name = resolver.view_name if resolver else ""
        path = request.path.lower()

        if any(key in path for key in BYPASS_PATH_KEYWORDS):
            return self.get_response(request)

        if "expense" in path and "amount" in request.POST:
            try:
                new_amount = Decimal(request.POST.get("amount", "0"))
            except Exception:
                new_amount = Decimal("0")

            expense_id = None
            if resolver and hasattr(resolver, "kwargs"):
                expense_id = resolver.kwargs.get("id") or resolver.kwargs.get("pk")
            if not expense_id:
                last = path.rstrip("/").split("/")[-1]
                if last.isdigit():
                    expense_id = int(last)

            if expense_id:
                exp = Expense.objects.filter(id=expense_id, user=request.user).first()
                if exp:
                    if new_amount > exp.amount: 
                        diff = new_amount - exp.amount
                        total_income, total_expense = get_totals(request.user)
                        if (total_expense + diff) > total_income:
                            return self._block(
                                request,
                                "❌ Cannot increase expense — total expenses would exceed total income.",
                            )
            else:
        
                if not can_afford_expense(request.user, new_amount):
                    return self._block(
                        request,
                        "❌ Cannot add this expense — insufficient available balance.",
                    )
        if "investment" in path and "amount" in request.POST:
            try:
                new_amount = Decimal(request.POST.get("amount", "0"))
            except Exception:
                new_amount = Decimal("0")

            total_income, total_expense = get_totals(request.user)
            total_outflow = total_expense + new_amount  

            if total_outflow > total_income:
                return self._block(
                    request,
                    "❌ Cannot add or update this investment — total income would be less than total expenses + investments.",
                )


        if (
            view_name in BULK_INCOME_VIEW_NAMES
            or "bulk_delete_income" in (view_name or "")
            or "income/bulk-delete" in path
        ):
            ids_str = (
                request.POST.get("selected_ids")
                or request.POST.get("ids")
                or request.POST.get("items")
                or request.POST.get("incomes")
                or ""
            )

            ids = []
            if isinstance(ids_str, (list, tuple)):
                ids = [int(i) for i in ids_str if str(i).isdigit()]
            elif isinstance(ids_str, str):
                ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]

   
            if ids:
                total_income, total_expense = get_totals(request.user)
                deleting_total = (
                    Income.objects.filter(user=request.user, id__in=ids)
                    .aggregate(total=Sum("amount"))["total"]
                    or Decimal("0")
                )
                if (total_income - deleting_total) < total_expense:
                    return self._block(
                        request,
                        "⚠️ Cannot delete selected incomes — expenses would exceed remaining income.",
                    )


            else:
                total_income, total_expense = get_totals(request.user)
                if total_expense > 0:
                    return self._block(
                        request,
                        "⚠️ Cannot delete all incomes — expenses would exceed total income.",
                    )

   
        if "income" in path and ("edit" in path or "update" in path or "delete" in path):
            total_income, total_expense = get_totals(request.user)
            try:
                income_id = None
                if resolver and hasattr(resolver, "kwargs"):
                    income_id = resolver.kwargs.get("id") or resolver.kwargs.get("pk")
                if not income_id:
                    last = path.rstrip("/").split("/")[-1]
                    if last.isdigit():
                        income_id = int(last)

                if income_id:
                    inc = Income.objects.filter(id=income_id, user=request.user).first()
                    if inc:
                  
                        if "delete" in path and (total_income - inc.amount) < total_expense:
                            return self._block(
                                request,
                                "⚠️ Cannot delete this income — expenses would exceed total income.",
                            )

                        if "amount" in request.POST:
                            try:
                                new_amount = Decimal(request.POST.get("amount"))
                                if new_amount < inc.amount: 
                                    diff = inc.amount - new_amount
                                    if (total_income - diff) < total_expense:
                                        return self._block(
                                            request,
                                            "⚠️ Cannot reduce this income — expenses would exceed total income.",
                                        )
                               
                            except Exception:
                                pass
            except Exception:
                pass


        return self.get_response(request)

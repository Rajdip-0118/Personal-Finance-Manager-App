
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from datetime import date
from .forms import SavingsGoalForm
from .utils import delete_goals_with_refund,get_goal_probability,SurplusTracker,surplus_rollover
from django.db.models import F
from .models import SavingsGoal
from django.db import transaction

@login_required
def savings_dashboard(request):
    surplus_rollover(request.user)
    # 1️⃣ Auto-update accumulated balance and allocate to goals
    balances = surplus_rollover(request.user)

    # 2️⃣ Filter type from GET parameter (all / active / completed)
    filter_type = request.GET.get("filter", "all")

    # 3️⃣ Fetch goals according to filter
    all_goals = SavingsGoal.objects.filter(user=request.user).order_by("deadline", "id")
    if filter_type == "active":
        all_goals = all_goals.filter(current_amount__lt=F("target_amount"))
    elif filter_type == "completed":
        all_goals = all_goals.filter(current_amount__gte=F("target_amount"))

    # 4️⃣ Pagination
    paginator = Paginator(all_goals, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # 5️⃣ Overall stats
    total_goals = all_goals.count()
    total_target = sum(goal.target_amount for goal in all_goals)
    total_current = sum(goal.current_amount for goal in all_goals)
    overall_progress = (total_current / total_target * 100) if total_target else 0

    # 6️⃣ Labels and progress for charts
    labels = [goal.name for goal in all_goals]
    progress = [float(goal.progress()) for goal in all_goals]

    # 7️⃣ Current month balance and accumulated balance
    current_balance = balances["current_balance"]
    accumulated_balance = balances["accumulated_balance"]

    # 8️⃣ Attach probability & conditional suggested deadline
    today = date.today()
    for goal in page_obj:
        result = get_goal_probability(request.user, goal)
        goal.probability = result["probability"]
        goal.is_numeric_prob = isinstance(goal.probability, (int, float))
        goal.suggested_deadline = result["suggested_deadline"]
        goal.progress_display = "Goal Completed" if goal.is_completed() else f"{goal.progress()}%"

    # 9️⃣ Render template
    return render(request, "savings/dashboard.html", {
        "labels": labels,
        "progress": progress,
        "goals": page_obj,
        "page_obj": page_obj,
        "total_goals": total_goals,
        "total_target": total_target,
        "total_current": total_current,
        "accumulated_balance": accumulated_balance,
        "current_balance": current_balance,
        "overall_progress": overall_progress,
        "filter_type": filter_type,  # pass filter for template
    })
# -------------------------
# CRUD: Goals Form
# -------------------------
@login_required
def goal_form(request, id=None):
    goal = get_object_or_404(SavingsGoal, id=id, user=request.user) if id else None

    if request.method == "POST":
        form = SavingsGoalForm(request.POST, instance=goal)
        if form.is_valid():
            new_goal = form.save(commit=False)
            new_goal.user = request.user

            with transaction.atomic():
                is_new = goal is None
                new_goal.save()

                # Trigger full reallocation for both new and edited goals
                from .utils import reallocate_on_new_goal
                reallocate_on_new_goal(request.user)

                msg = "added" if is_new else "updated"
                messages.success(request, f"Savings goal {msg} successfully!")

            return redirect("savings_dashboard")
    else:
        form = SavingsGoalForm(instance=goal)

    return render(request, "savings/goal_form.html", {"form": form, "goal": goal})

# -------------------------
# DELETE Goals (with refund)
# -------------------------
@login_required
def delete_goal(request, id):
    if request.method == "POST":
        goal = get_object_or_404(SavingsGoal, id=id, user=request.user)
        count, refund = delete_goals_with_refund(request.user, SavingsGoal.objects.filter(id=goal.id))
        messages.success(request, f"Goal '{goal.name}' deleted and {refund} refunded to accumulated balance!")
    return redirect("savings_dashboard")


@login_required
def delete_selected_goals(request):
    if request.method == "POST":
        ids_list = [int(i) for i in request.POST.get("selected_ids", "").split(",") if i.isdigit()]
        if ids_list:
            goals = SavingsGoal.objects.filter(id__in=ids_list, user=request.user)
            count, refund = delete_goals_with_refund(request.user, goals)
            messages.success(request, f"{count} goals deleted and {refund} refunded to accumulated balance!")
        else:
            messages.error(request, "No valid goals selected.")
    return redirect("savings_dashboard")


@login_required
def delete_all_goals(request):
    if request.method == "POST":
        goals = SavingsGoal.objects.filter(user=request.user)
        if goals.exists():
            count, refund = delete_goals_with_refund(request.user, goals)
            messages.success(request, f"All {count} goals deleted and {refund} refunded to accumulated balance!")
        else:
            messages.error(request, "No goals available to delete.")
    return redirect("savings_dashboard")












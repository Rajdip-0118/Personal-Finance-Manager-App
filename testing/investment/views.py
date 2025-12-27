# investment/views.py
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Investment
from .forms import InvestmentForm
from .utils import get_expected_return_by_type
from .utils_refresh import refresh_if_stale
from django.http import JsonResponse
from budget.utils import check_budget_warnings
from finance.models import Expense


@login_required
def get_expected_return(request):
    inv_type = request.GET.get("type")
    if not inv_type:
        return JsonResponse({"expected_return": None})
    rate = get_expected_return_by_type(inv_type)
    return JsonResponse({"expected_return": rate})

def _to_decimal(value):
    """Helper to ensure value is Decimal."""
    if value is None:
        return Decimal('0')
    return value if isinstance(value, Decimal) else Decimal(str(value))


@login_required
def investment_list(request):
    filter_type = request.GET.get('filter', 'all')


    investments = Investment.objects.filter(user=request.user).order_by('-id')


    if filter_type == 'active':
        investments = investments.filter(status__iexact='Active')
    elif filter_type == 'completed':
        investments = investments.filter(status__iexact='Completed')        
    

    paginator = Paginator(investments, 30) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
    }
    return render(request, 'investment/investment_list.html', context)

@login_required
def add_investment(request):
    if request.method == 'POST':
        form = InvestmentForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.user = request.user
            today = timezone.now().date()


            if inv.end_date and inv.end_date <= today:
                inv.status = "Completed"
            else:
                inv.status = "Active"

            inv.save()
            messages.success(request, 'Investment added successfully.')
        
            try:
                expense = Expense.objects.filter(user=request.user, investment=inv).first()
                if expense:
                    check_budget_warnings(request, expense)
            except Exception as e:
                import logging
                logging.warning(f"Budget check skipped: {e}")
            return redirect('investment_list')
        else:
    
            if 'end_date' in form.errors and "End date must be after start date." in form.errors['end_date']:
                messages.error(request, "⚠️ Please ensure the end date is after the start date.")
            else:
                messages.error(request, "⚠️ Please correct the highlighted errors below.")
                
    else:
        form = InvestmentForm()
    return render(request, 'investment/investment_form.html', {'form': form})


@login_required
def edit_investment(request, id):
    investment = get_object_or_404(Investment, id=id, user=request.user)
    if request.method == 'POST':
        form = InvestmentForm(request.POST, instance=investment)
        if form.is_valid():
            inv = form.save(commit=False)
            today = timezone.now().date()

           
            if inv.end_date and inv.end_date <= today:
                inv.status = "Completed"
            else:
                inv.status = "Active"

            inv.save()
            messages.success(request, 'Investment updated successfully.')
   
            try:
                expense = Expense.objects.filter(user=request.user, investment=inv).first()
                if expense:
                    check_budget_warnings(request, expense)
            except Exception as e:
                import logging
                logging.warning(f"Budget check skipped: {e}")
            return redirect('investment_list')
        
        else:

            if 'end_date' in form.errors and "End date must be after start date." in form.errors['end_date']:
                messages.error(request, "⚠️ Please ensure the end date is after the start date.")
            else:
                messages.error(request, "⚠️ Please correct the highlighted errors below.")
    else:
        form = InvestmentForm(instance=investment)
    return render(request, 'investment/investment_form.html', {'form': form})

@login_required
def delete_investment(request, id):
    investment = get_object_or_404(Investment, id=id, user=request.user)
    if request.method == "POST":
        investment.delete()
        messages.success(request, "Investment deleted successfully. Investment amount has been returned to your account.")
    else:
        messages.warning(request, "Please confirm deletion.")
    return redirect("investment_list")

@login_required
def delete_all_investments(request):
    if request.method == "POST":
        investments = Investment.objects.filter(user=request.user)
        count = investments.count()
        investments.delete()
        messages.success(request, f"All ({count}) investments deleted successfully. Investment amount has been returned to your account.")
    else:
        messages.warning(request, "Please confirm deletion of all investments.")
    return redirect("investment_list")

@login_required
@transaction.atomic
def investment_portfolio(request):
    investments = Investment.objects.filter(user=request.user)
    today = date.today()

    total_invested = Decimal('0')
    total_estimated_value = Decimal('0')
    total_profit = Decimal('0')
    total_return_rate = Decimal('0')
    valid_returns = 0
    total_overall_estimated = Decimal('0')
    total_overall_profit = Decimal('0')


    def calculate_compound_value(principal, annual_rate, start, end, investment_type, frequency=None):
        if not start or not end or annual_rate is None:
            return principal

        if not isinstance(annual_rate, Decimal):
            annual_rate = Decimal(str(annual_rate))

        days = (end - start).days
        if days <= 0 or annual_rate == 0:
            return principal

        years = Decimal(days) / Decimal('365')

        type_based_freq = {
            'fd': 'Quarterly',
            'bond': 'Biannual',
            'rd': 'Monthly',
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


        investment_type_lower = investment_type.lower()
        auto_freq = type_based_freq.get(investment_type_lower, 'Yearly')
        final_frequency = frequency or auto_freq
        comp_per_year = freq_map.get(final_frequency, Decimal('1'))

        rate_per_period = (annual_rate / Decimal('100')) / comp_per_year
        periods = comp_per_year * years

    
        if 'fd' in investment_type_lower:
          
            value = principal * ((Decimal('1') + rate_per_period) ** periods)

        elif 'rd' in investment_type_lower:
     
            months = int(years * 12)
            monthly_rate = (annual_rate / Decimal('100')) / Decimal('12')
            value = principal * (((Decimal('1') + monthly_rate) ** months - Decimal('1')) / monthly_rate)

        elif investment_type_lower in ['stock', 'mutual fund', 'etf', 'crypto']:
         
            value = principal * ((Decimal('1') + (annual_rate / Decimal('100'))) ** years)

        elif 'bond' in investment_type_lower:

            coupon_freq = freq_map.get(final_frequency, Decimal('2'))
            coupon_rate = (annual_rate / Decimal('100')) / coupon_freq
            value = principal * ((Decimal('1') + coupon_rate) ** (years * coupon_freq))

        elif 'pension' in investment_type_lower or 'other' in investment_type_lower:
  
            if final_frequency.lower() == 'yearly':
                value = principal * (Decimal('1') + (annual_rate / Decimal('100')) * years)
            else:
                value = principal * ((Decimal('1') + rate_per_period) ** periods)

        elif 'real estate' in investment_type_lower or 'gold' in investment_type_lower:

            value = principal * (Decimal('1') + (annual_rate / Decimal('100')) * years)

        else:

            value = principal * ((Decimal('1') + rate_per_period) ** periods)

        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    REFRESH_INTERVAL_SECONDS = 3600  
    updated_any = False
    for inv in investments:
  
        if not inv.last_updated or (timezone.now() - inv.last_updated).total_seconds() >= REFRESH_INTERVAL_SECONDS:  
            if refresh_if_stale(inv):  
                updated_any = True

        
        amount = _to_decimal(inv.amount)
        expected_return = _to_decimal(inv.expected_return or Decimal('0'))
        
        end_date = inv.end_date or today
        estimated_value = calculate_compound_value(
            amount, expected_return, inv.start_date, end_date, inv.investment_type, inv.frequency
        )

        estimated_value_rounded = estimated_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        profit_estimate = (estimated_value_rounded - amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        inv.estimated_value_display = estimated_value_rounded
        inv.profit_display = profit_estimate

        total_invested += amount
        total_overall_estimated += estimated_value_rounded
        total_overall_profit += profit_estimate
        
        if inv.status == "Completed":
            total_estimated_value += estimated_value_rounded
            total_profit += profit_estimate
            
        if expected_return != 0:
            total_return_rate += expected_return
            valid_returns += 1

        if inv.end_date and inv.end_date <= today and inv.status != "Completed":
            inv.status = "Completed"
            inv.save(update_fields=["status"])
            
    if updated_any:
        messages.info(request, "📊 Live market values have been refreshed for your investments.")

    avg_return = (total_return_rate / valid_returns).quantize(Decimal('0.01')) if valid_returns else Decimal('0')

    monthly_data_invested = {}
    monthly_data_estimated = {}
    for inv in investments:
        if inv.start_date:
            label = inv.start_date.strftime('%b %Y')
            monthly_data_invested[label] = monthly_data_invested.get(label, 0) + float(inv.amount)
            monthly_data_estimated[label] = monthly_data_estimated.get(label, 0) + float(inv.estimated_value_display)

    months = list(monthly_data_invested.keys())
    invested_amounts = list(monthly_data_invested.values())
    estimated_amounts = [monthly_data_estimated.get(m, 0) for m in months]

    category_investments = (
        investments.values('investment_type')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    category_labels = [c['investment_type'] for c in category_investments]
    category_values = [float(c['total']) for c in category_investments]

    context = {
        "investments": investments,
        "total_invested": total_invested.quantize(Decimal('0.01')),
        "total_estimated_value": total_estimated_value.quantize(Decimal('0.01')),
        "total_profit": total_profit.quantize(Decimal('0.01')),
        "avg_return": avg_return,
        "year": today.year,
        "months": json.dumps(months),
        "invested_amounts": json.dumps(invested_amounts),
        "estimated_amounts": json.dumps(estimated_amounts),
        "category_labels": json.dumps(category_labels),
        "category_values": json.dumps(category_values),
        "total_overall_estimated": total_overall_estimated.quantize(Decimal('0.01')),
        "total_overall_profit": total_overall_profit.quantize(Decimal('0.01')),
    }

    return render(request, "investment/investment_portfolio.html", context)

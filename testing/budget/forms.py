# budget/forms.py
from django import forms
from decimal import Decimal
from .models import Budget, BudgetCategory, _calculate_recurring_total
from finance.models import Income, Expense
from django.db.models import Sum

class BudgetForm(forms.ModelForm):
    # user inputs percent instead of amount
    total_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0.01'), max_value=Decimal('100.00'),
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Enter budget as % of available income (e.g. 60)'}),
        label="Budget (% of available income)"
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d-%m-%Y'], required=True, label="Start Date "
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d-%m-%Y'], required=True, label="End Date "
    )

    class Meta:
        model = Budget
        fields = ["name", "total_percent", "start_date", "end_date"]
        labels = {"name": "Budget Name"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter a Budget Name", "class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        total_percent = cleaned.get('total_percent')
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
            # Add a non-field error so it appears at the top
                self.add_error(None, "Start Date cannot be later than End Date.")

        if self.user and total_percent is not None and start_date and end_date:
            qs = Budget.objects.filter(user=self.user, start_date=start_date, end_date=end_date)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)  # ignore self when editing

            if qs.exists():
                self.add_error(None, "You already have a budget with the same start and end date.")
            # compute available income
            income_total = Income.objects.filter(
                user=self.user,
                date__range=[start_date, end_date]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            recurring_total = _calculate_recurring_total(start_date, end_date, self.user)
            available_income = (income_total or Decimal('0.00')) + (recurring_total or Decimal('0.00'))

            budget_amount = (available_income * (Decimal(total_percent) / Decimal('100'))).quantize(Decimal('0.01'))

            if available_income == Decimal('0.00'):
                self.add_error('total_percent', 'Available income for this period is zero; cannot create a percentage-based budget.')

            if total_percent <= Decimal('0'):
                self.add_error('total_percent', 'Budget percent must be greater than 0.')

            if total_percent > Decimal('100.00'):
                self.add_error('total_percent', 'Budget percent cannot exceed 100%.')

            # Optionally, warn if budget_amount is extremely small
            if budget_amount <= Decimal('0.00'):
                self.add_error('total_percent', f'Resulting budget amount ({budget_amount}) is not valid.')

        return cleaned


class BudgetCategoryForm(forms.ModelForm):
    # user will enter percent only (percent of the budget)
    limit_value = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0.01'), max_value=Decimal('100.00'),
        label='Category Limit (% of budget)',
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Enter % of the budget for this category'})
    )

    class Meta:
        model = BudgetCategory
        fields = ['category']

    def __init__(self, *args, **kwargs):
        self.budget = kwargs.pop('budget', None)
        super().__init__(*args, **kwargs)

        # set category choices
        from finance.models import Expense
        if 'category' in self.fields:
            self.fields['category'].choices = Expense.CATEGORY_CHOICES

        if not self.budget:
            return

        # compute remaining percent available
        other_percent = sum(c.percent for c in self.budget.categories.all())
        if self.instance.pk:
            other_percent -= (self.instance.percent or Decimal('0.00'))

        max_allowed_percent = max(Decimal('0.00'), Decimal('100.00') - Decimal(other_percent))
        self.fields['limit_value'].widget.attrs['max'] = str(max_allowed_percent)
        self.fields['limit_value'].help_text = f"Maximum allowed percent of budget: {max_allowed_percent}%."

    def clean(self):
        cleaned = super().clean()
        limit_percent = cleaned.get('limit_value')
        category_name = cleaned.get('category')

        if not self.budget:
            raise forms.ValidationError('Budget context is required for category limits.')

        if limit_percent is None:
            self.add_error('limit_value', 'Please enter a percent value for the category limit.')
         
        # duplicate category check (case-insensitive)
        if category_name:
            qs = self.budget.categories.filter(category__iexact=category_name.strip())
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('category', f"The category '{category_name}' already exists in this budget.")

        # total percent validation
        other_percent = sum(c.percent for c in self.budget.categories.all())
        if self.instance.pk:
            other_percent -= (self.instance.percent or Decimal('0.00'))

        total_with_new = other_percent + Decimal(limit_percent or 0)

        if total_with_new > Decimal('100.00'):
            self.add_error('limit_value', f"Total category percentages ({total_with_new}%) cannot exceed 100% of the budget.")

        # compute monetary amounts and ensure sensible
        budget_amount = Decimal(self.budget.total_amount)
        new_category_amount = (budget_amount * (Decimal(limit_percent) / Decimal('100'))).quantize(Decimal('0.01'))

        if budget_amount <= Decimal('0.00'):
            self.add_error('limit_value', 'Budget amount is zero; cannot assign a category percent.')

        if new_category_amount <= Decimal('0.00'):
            self.add_error('limit_value', f'Resulting category amount ({new_category_amount}) is not valid.')

        # set percent onto cleaned data so save() can use it
        cleaned['percent'] = Decimal(limit_percent)

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.percent = self.cleaned_data.get('percent', Decimal('0.00'))
        if commit:
            instance.save()
        return instance

from django import forms
from .models import Income, Expense, RecurringIncome, RecurringExpense #, Category
from django.utils import timezone

class BaseFinanceForm(forms.ModelForm):
    #Base form for Income and Expense to avoid duplication

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make all fields required
        for field in self.fields:
            if field not in [self._meta.model._meta.pk.name, "end_date"]:
                self.fields[field].required = True

        # Handle category dropdown (remove "---------" and default to first)
        if 'category' in self.fields:
            model = self._meta.model
            self.fields['category'].choices = model.CATEGORY_CHOICES
            
        if 'frequency' in self.fields:
            model = self._meta.model
            self.fields['frequency'].choices = model.FREQUENCY_CHOICES

class IncomeForm(BaseFinanceForm):
    class Meta:
        model = Income
        fields = ['source', 'amount', 'date', 'category']
        labels = {'source': 'Income Source', 'category': 'Income Category'}
        widgets = {
            'source': forms.TextInput(attrs={'placeholder': 'Enter source of income', 'class': 'input-field'}),
            'date': forms.DateInput(attrs={'type': 'date', 'value': timezone.now().date()}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Enter amount'}),
        }

        
class ExpenseForm(BaseFinanceForm):
    class Meta:
        model = Expense
        fields = ['name', 'amount', 'date', 'category']
        labels = {'name': 'Expense Name', 'category': 'Expense Category'}
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter name of expense', 'class': 'input-field'}),
            'date': forms.DateInput(attrs={'type': 'date', 'value': timezone.now().date()}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Enter amount'}),
        }
        
class RecurringIncomeForm(BaseFinanceForm):
    class Meta:
        model = RecurringIncome
        fields = ['source', 'amount', 'frequency', 'category', 'start_date', 'end_date']
        widgets = {
            'source': forms.TextInput(attrs={'placeholder': 'Enter source of recurring income', 'class': 'input-field'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Enter amount'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'value': timezone.now().date()}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'source': 'Income Source',
            'category': 'Income Category',
            'end_date': 'End Date (optional)',
        }
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if end_date and start_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be earlier than start date.')

        return cleaned_data
        
class RecurringExpenseForm(BaseFinanceForm):
    class Meta:
        model = RecurringExpense
        fields = ['name', 'amount', 'frequency', 'category', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter name of recurring expense', 'class': 'input-field'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Enter amount'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'value': timezone.now().date()}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'name': 'Expense Name',
            'category': 'Expense Category',
            'end_date': 'End Date (optional)',
        }
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if end_date and start_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be earlier than start date.')

        return cleaned_data 

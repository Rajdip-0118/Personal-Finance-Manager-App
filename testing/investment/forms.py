from django import forms
from .models import Investment

class InvestmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        model = self._meta.model
        if 'investment_type' in self.fields:
            self.fields['investment_type'].choices = model.INVESTMENT_TYPES
        if 'frequency' in self.fields:
            self.fields['frequency'].choices = model.FREQUENCY_CHOICES

    expected_return = forms.DecimalField(
        label="Expected Return (%)",
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 8 for 8%', 'class': 'form-input', 'step': '0.01', 'min': '0'}))

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input datepicker', 'placeholder': 'Select start date'},format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d-%m-%Y'],
        required=True,
        label="Start Date")

    end_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-input datepicker', 'placeholder': 'Select end date'},format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d-%m-%Y'],
        required=False,
        label="End Date")

    frequency = forms.ChoiceField(
        label="Frequency",
        choices=Investment.FREQUENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Investment
        fields = [
            'name',
            'investment_type',
            'amount',
            'expected_return',
            'start_date',
            'end_date',
            'frequency',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter Name of Investment',}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Enter Amount Invested',}),
        }
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date >= end_date:
            self.add_error("end_date", "End date must be after start date.")

        return cleaned_data

from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import SavingsGoal 

class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ["name", "target_amount", "deadline", "priority"]
        labels = {"name": "Savings Goal Name :", "target_amount": "Target Amount :", "deadline": "Deadline :", "priority": "Priority :"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter Name of a Savings Goal", "class": "form-input"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "target_amount": forms.NumberInput(attrs={"placeholder": "Enter Target Amount", "class": "form-input"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'priority' in self.fields:
            self.fields['priority'].choices = SavingsGoal.PRIORITY_CHOICES

        # Set default deadline to tomorrow if creating a new goal
        if not self.instance.pk:  # New goal
            tomorrow = timezone.localdate() + timedelta(days=1)
            self.fields['deadline'].initial = tomorrow
            self.fields['deadline'].widget.attrs['min'] = tomorrow  # restrict past dates in date picker
        else:
            today = timezone.localdate()
            # prevent selecting past dates for existing goals as well
            self.fields['deadline'].widget.attrs['min'] = today

    def clean_deadline(self):
        deadline = self.cleaned_data.get("deadline")
        today = timezone.localdate()
        if deadline and deadline < today:
            raise forms.ValidationError("Deadline cannot be in the past.")
        return deadline

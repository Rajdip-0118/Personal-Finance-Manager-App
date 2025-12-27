from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

USERNAME_REGEX = r'^[\w\s.@+\-]+$'
USERNAME_VALIDATOR = RegexValidator(
    regex=USERNAME_REGEX,
    message='Enter a valid username. This value may contain letters, numbers, spaces, and @/./+/-/_ characters.'
)

class CreateUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

   
    username = forms.CharField(
        max_length=150,
        required=True,
        validators=[USERNAME_VALIDATOR],
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].validators = [USERNAME_VALIDATOR]

        field_styles = {
            'username': 'Enter username',
            'email': 'Enter email address',
            'password1': 'Enter password',
            'password2': 'Confirm password',
        }
        
        for field, placeholder in field_styles.items():
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholder,
            })

    def _post_clean(self):
        """
        Temporarily replace the model field's validators with our form validators
        while ModelForm does its post-clean (which calls model validation).
        This prevents Django's default UnicodeUsernameValidator from firing.
        """
        model = self._meta.model
        try:
            model_field = model._meta.get_field('username')
        except Exception:
  
            return super()._post_clean()

        original_validators = list(model_field.validators)
        try:
     
            model_field.validators = list(self.fields['username'].validators)
            super()._post_clean()
        finally:
   
            model_field.validators = original_validators

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

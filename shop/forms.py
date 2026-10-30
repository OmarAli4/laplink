from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Review


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, label=_('First name'), help_text=_('Optional.'))
    last_name = forms.CharField(max_length=30, required=False, label=_('Last name'), help_text=_('Optional.'))
    email = forms.EmailField(max_length=254, label=_('Email'), help_text=_('Required. Inform a valid email address.'))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'content']
        widgets = {
            'rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': _('Write your review here...')}),
        }

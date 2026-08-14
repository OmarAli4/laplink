from django import forms
from .models import Order
from django.utils.translation import gettext_lazy as _


class OrderCreateForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=30,
        required=True,
        label=_("Mobile Phone Number"),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 01012345678'})
    )

    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = True

import re
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Order

EGYPT_GOVERNORATES = [
    ('', _('اختر المحافظة / Select Governorate')),
    ('القاهرة - Cairo', _('القاهرة (Cairo)')),
    ('الجيزة - Giza', _('الجيزة (Giza)')),
    ('الإسكندرية - Alexandria', _('الإسكندرية (Alexandria)')),
    ('القليوبية - Qalyubia', _('القليوبية (Qalyubia)')),
    ('الدقهلية - Dakahlia', _('الدقهلية (Dakahlia)')),
    ('الشرقية - Sharqia', _('الشرقية (Sharqia)')),
    ('الغربية - Gharbia', _('الغربية (Gharbia)')),
    ('المنوفية - Monufia', _('المنوفية (Monufia)')),
    ('البحيرة - Beheira', _('البحيرة (Beheira)')),
    ('كفر الشيخ - Kafr El Sheikh', _('كفر الشيخ (Kafr El Sheikh)')),
    ('دمياط - Damietta', _('دمياط (Damietta)')),
    ('بورسعيد - Port Said', _('بورسعيد (Port Said)')),
    ('الإسماعيلية - Ismailia', _('الإسماعيلية (Ismailia)')),
    ('السويس - Suez', _('السويس (Suez)')),
    ('الفيوم - Fayoum', _('الفيوم (Fayoum)')),
    ('بني سويف - Beni Suef', _('بني سويف (Beni Suef)')),
    ('المنيا - Minya', _('المنيا (Minya)')),
    ('أسيوط - Assiut', _('أسيوط (Assiut)')),
    ('سوهاج - Sohag', _('سوهاج (Sohag)')),
    ('قنا - Qena', _('قنا (Qena)')),
    ('الأقصر - Luxor', _('الأقصر (Luxor)')),
    ('أسوان - Aswan', _('أسوان (Aswan)')),
    ('البحر الأحمر - Red Sea', _('البحر الأحمر (Red Sea)')),
    ('مطروح - Matrouh', _('مطروح (Matrouh)')),
    ('شمال سيناء - North Sinai', _('شمال سيناء (North Sinai)')),
    ('جنوب سيناء - South Sinai', _('جنوب سيناء (South Sinai)')),
    ('الوادي الجديد - New Valley', _('الوادي الجديد (New Valley)')),
]


class OrderCreateForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=30,
        required=True,
        label=_("رقم الموبايل (Mobile / WhatsApp)"),
        widget=forms.TextInput(attrs={'placeholder': '01009019079', 'dir': 'ltr'})
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        label=_("المحافظة (Governorate)"),
        widget=forms.Select(choices=EGYPT_GOVERNORATES)
    )

    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'phone',
            'email',
            'city',
            'address',
            'delivery_notes',
            'payment_method',
            'instapay_reference',
            'payment_proof',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = True
        self.fields['city'].required = True
        self.fields['address'].required = True
        self.fields['delivery_notes'].required = False
        self.fields['payment_method'].required = False
        self.fields['instapay_reference'].required = False
        self.fields['payment_proof'].required = False

    def clean_phone(self):
        raw_phone = self.cleaned_data.get('phone', '')
        digits = re.sub(r'\D', '', raw_phone)
        if digits.startswith('0020'):
            digits = '0' + digits[4:]
        elif digits.startswith('20') and len(digits) == 12:
            digits = '0' + digits[2:]
        if not re.match(r'^01[0125][0-9]{8}$', digits):
            raise forms.ValidationError(_("يرجى إدخال رقم موبايل مصري صحيح مكون من 11 رقم (مثال: 01012345678)."))
        return digits

    def clean_payment_method(self):
        pm = self.cleaned_data.get('payment_method')
        if pm not in ('cod', 'instapay'):
            return 'cod'
        return pm

    def save(self, commit=True):
        order = super().save(commit=False)
        # If user typed full name in first_name and left last_name empty, split cleanly
        if order.first_name and not order.last_name:
            parts = order.first_name.strip().split(None, 1)
            order.first_name = parts[0]
            if len(parts) > 1:
                order.last_name = parts[1]
        if commit:
            order.save()
        return order

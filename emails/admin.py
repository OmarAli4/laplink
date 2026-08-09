from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ['recipient', 'subject', 'status_badge', 'timestamp']
    list_filter = ['status', 'timestamp']
    search_fields = ['recipient', 'subject', 'message_id']
    readonly_fields = ['recipient', 'subject', 'status', 'message_id', 'timestamp']

    @admin.display(description="Delivery Status")
    def status_badge(self, obj):
        return obj.status

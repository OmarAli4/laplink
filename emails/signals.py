from django.dispatch import receiver
from anymail.signals import tracking
from .models import EmailLog

@receiver(tracking)
def handle_outbound_email_tracking(sender, event, esp_name, **kwargs):
    if event.message_id:
        try:
            log = EmailLog.objects.get(message_id=event.message_id)
            log.status = event.event_type # e.g. 'delivered', 'opened', 'bounced'
            log.save()
        except EmailLog.DoesNotExist:
            pass

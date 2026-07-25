from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import EmailLog
import logging
import uuid
import threading

logger = logging.getLogger(__name__)

def _send_email_async(email, to_email, subject):
    """
    Sends email in a non-blocking background thread to keep HTTP requests instant.
    """
    try:
        email.send()
        if hasattr(email, 'anymail_status') and email.anymail_status.message_id:
            msg_id = email.anymail_status.message_id
        else:
            msg_id = str(uuid.uuid4())

        EmailLog.objects.create(recipient=to_email, subject=subject, message_id=msg_id)
    except Exception as e:
        logger.error(f"Failed to send email async: {e}")


class NotificationService:
    """
    Handles all outbound email notifications asynchronously.
    """
    
    @staticmethod
    def send_order_confirmation(order):
        """
        Sends an order confirmation email asynchronously and logs it.
        """
        subject = f"Order Confirmation - #{order.id}"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'hello@laplink.com')
        to_email = order.email

        # Render HTML and Text versions
        html_content = render_to_string('emails/order_confirmation.html', {'order': order})
        text_content = f"Dear {order.first_name},\n\nThank you for placing your order at Lap Link!\nYour order ID is {order.id}."
        
        email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        email.attach_alternative(html_content, "text/html")
        
        # Dispatch in background thread for zero-latency UI response
        threading.Thread(target=_send_email_async, args=(email, to_email, subject), daemon=True).start()

    @staticmethod
    def send_welcome_email(user):
        """
        Sends a welcome email upon registration asynchronously.
        """
        subject = "Welcome to Lap Link!"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'hello@laplink.com')
        to_email = user.email

        # Render HTML and Text versions
        html_content = render_to_string('emails/welcome.html', {'user': user})
        text_content = f"Welcome to the Club, {user.first_name or user.username}!\nWe're thrilled to have you here at Lap Link."
        
        email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        email.attach_alternative(html_content, "text/html")
        
        # Dispatch in background thread for zero-latency UI response
        threading.Thread(target=_send_email_async, args=(email, to_email, subject), daemon=True).start()

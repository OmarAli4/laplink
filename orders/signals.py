from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order

@receiver(pre_save, sender=Order)
def order_status_changed(sender, instance, **kwargs):
    """
    Send an email to the customer when the order status changes.
    Also, automatically set status to 'processing' if paid is flipped to True.
    """
    if instance.id:
        try:
            old_order = Order.objects.get(id=instance.id)
            
            # Map paid=True to 'processing' automatically if it was pending
            if instance.paid and not old_order.paid and instance.status == 'pending':
                instance.status = 'processing'
                
            # Increment coupon usage when an order becomes paid
            if instance.paid and not old_order.paid and instance.coupon:
                from django.db.models import F
                instance.coupon.times_used = F('times_used') + 1
                instance.coupon.save()
            
            # If status actually changed, send email
            if old_order.status != instance.status:
                status_messages = {
                    'processing': ('Order Processing', f'Your order {instance.id} is now being processed.'),
                    'shipped': ('Order Shipped', f'Great news! Your order {instance.id} has shipped.'),
                    'delivered': ('Order Delivered', f'Your order {instance.id} has been delivered. Enjoy!'),
                    'cancelled': ('Order Cancelled', f'Your order {instance.id} has been cancelled.'),
                }
                
                if instance.status in status_messages:
                    subject, message = status_messages[instance.status]
                    try:
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[instance.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        # Log error in real app
                        pass
        except Order.DoesNotExist:
            pass
    else:
        # New order being created
        if instance.paid and instance.status == 'pending':
            instance.status = 'processing'

from celery import shared_task
import time

@shared_task
def send_abandoned_cart_email(user_id, cart_details):
    """
    Mock Celery task to send abandoned cart recovery emails.
    In production, this would use Anymail/Resend.
    """
    print(f"Executing Celery task: send_abandoned_cart_email for user_id={user_id}")
    time.sleep(2) # Simulate network delay
    print(f"SUCCESS: Abandoned cart email dispatched to user {user_id} with 5% discount code.")
    return True

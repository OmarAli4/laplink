import datetime

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import Action


def create_action(user, verb, target=None):
    """
    Create an activity stream action, with built-in duplicate prevention.

    Before persisting, this function checks if an identical action
    (same user, same verb, same target) was already created within the
    last 60 seconds. If so, the duplicate is silently skipped.

    Args:
        user: The User instance who performed the action.
        verb: A string describing the action (e.g., 'purchased', 'added to cart').
        target: An optional model instance that is the target of the action.

    Returns:
        True if the action was created, False if it was a duplicate.
    """
    now = timezone.now()
    last_minute = now - datetime.timedelta(seconds=60)

    # Check for identical recent actions to prevent spam
    similar_actions = Action.objects.filter(
        user=user,
        verb=verb,
        created__gte=last_minute,
    )

    if target:
        target_ct = ContentType.objects.get_for_model(target)
        similar_actions = similar_actions.filter(
            target_ct=target_ct,
            target_id=target.pk,
        )

    if not similar_actions.exists():
        action = Action(user=user, verb=verb, target=target)
        action.save()
        return True

    return False

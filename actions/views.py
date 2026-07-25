from django.shortcuts import render
from .models import Action


def activity_feed(request):
    """
    Display the global activity feed using select_related and prefetch_related
    as requested for optimized database queries.
    """
    actions = Action.objects.select_related('user').prefetch_related('target')[:50]
    return render(request, 'actions/feed.html', {'actions': actions})

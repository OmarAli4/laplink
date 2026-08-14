# Generated for adding phone field to Order model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_order_shipping_provider_order_tracking_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]

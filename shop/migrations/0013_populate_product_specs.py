from django.db import migrations


def populate_product_specs(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    ProductSpec = apps.get_model('shop', 'ProductSpec')

    sample_specs = {
        'laptop': [
            ('RAM', '16 GB DDR5', 16.0, 'GB', '💾', 1),
            ('CPU', 'Intel Core i7-13700H', 4.8, 'GHz', '⚡', 2),
            ('Storage', '1 TB NVMe SSD', 1000.0, 'GB', '💿', 3),
            ('Battery', '72 Wh', 72.0, 'Wh', '🔋', 4),
            ('Display', '15.6 Inch 144Hz', 144.0, 'Hz', '🖥️', 5),
        ],
        'macbook': [
            ('RAM', '32 GB Unified', 32.0, 'GB', '💾', 1),
            ('CPU', 'Apple M3 Max', 5.0, 'GHz', '⚡', 2),
            ('Storage', '2 TB SSD', 2000.0, 'GB', '💿', 3),
            ('Battery', '100 Wh', 100.0, 'Wh', '🔋', 4),
            ('Display', '16.2 Inch Liquid Retina XDR', 120.0, 'Hz', '🖥️', 5),
        ],
        'phone': [
            ('RAM', '12 GB', 12.0, 'GB', '💾', 1),
            ('Processor', 'Snapdragon 8 Gen 3', 3.3, 'GHz', '⚡', 2),
            ('Storage', '512 GB', 512.0, 'GB', '💿', 3),
            ('Battery', '5000 mAh', 5000.0, 'mAh', '🔋', 4),
            ('Camera', '200 MP', 200.0, 'MP', '📸', 5),
        ],
        'audio': [
            ('Battery Life', '30 Hours', 30.0, 'hrs', '🔋', 1),
            ('Driver Size', '40 mm', 40.0, 'mm', '🎧', 2),
            ('Bluetooth', 'v5.3', 5.3, 'v', '📡', 3),
            ('Noise Cancellation', '40 dB Active ANC', 40.0, 'dB', '🔇', 4),
        ]
    }

    for p in Product.objects.all():
        if ProductSpec.objects.filter(product=p).exists():
            continue
            
        name_lower = p.name.lower()
        if 'macbook' in name_lower or 'pro' in name_lower:
            template = sample_specs['macbook']
        elif 'phone' in name_lower or 'galaxy' in name_lower or 'iphone' in name_lower:
            template = sample_specs['phone']
        elif 'headphone' in name_lower or 'audio' in name_lower or 'ear' in name_lower or 'sony' in name_lower:
            template = sample_specs['audio']
        else:
            template = sample_specs['laptop']
            
        for sname, sval, numval, unit, icon, order in template:
            ProductSpec.objects.create(
                product=p,
                name=sname,
                value=sval,
                numeric_value=numval,
                unit=unit,
                icon=icon,
                order=order
            )


def reverse_product_specs(apps, schema_editor):
    ProductSpec = apps.get_model('shop', 'ProductSpec')
    ProductSpec.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0012_productspec'),
    ]

    operations = [
        migrations.RunPython(populate_product_specs, reverse_product_specs),
    ]

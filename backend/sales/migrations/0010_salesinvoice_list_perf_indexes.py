from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0009_salesinvoice_tax_enabled_salesinvoice_tax_rate'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='salesinvoice',
            index=models.Index(
                fields=['company', '-created_at'],
                name='si_company_created_idx',
            ),
        ),
    ]

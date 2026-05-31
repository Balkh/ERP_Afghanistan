from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0009_fiscal_period_governance'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='journalentry',
            index=models.Index(
                fields=['company', '-entry_date'],
                name='je_company_entry_date_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='journalentry',
            index=models.Index(
                fields=['-created_at'],
                name='je_created_at_desc_idx',
            ),
        ),
    ]

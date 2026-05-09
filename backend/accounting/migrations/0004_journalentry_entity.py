"""
Migration to add entity_id to JournalEntry for multi-company support.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0003_fix_account_category_null'),
        ('entities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='journalentry',
            name='entity',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name='journal_entries',
                to='entities.Entity',
                verbose_name='Company/Entity'
            ),
        ),
    ]
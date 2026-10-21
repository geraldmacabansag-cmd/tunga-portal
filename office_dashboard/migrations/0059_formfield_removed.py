# Keeps a form field (and citizens' answers to it) when the office removes it
# from the form in the "Make Fillable" builder. See FormField.removed.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('office_dashboard', '0058_alter_service_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='formfield',
            name='removed',
            field=models.BooleanField(default=False),
        ),
    ]
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("offices", "0007_align_to_full_office_list"),
    ]

    operations = [
        migrations.AddField(
            model_name="office",
            name="is_visible",
            field=models.BooleanField(
                default=True,
                help_text="Uncheck to hide this office from the public Offices page.",
            ),
        ),
    ]
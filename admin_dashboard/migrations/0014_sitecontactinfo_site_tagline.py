from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_dashboard", "0013_superadmin_mobile_number_superadmin_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitecontactinfo",
            name="site_tagline",
            field=models.CharField(blank=True, default="Abtik na serbisyo, masulong na bungto.", max_length=120),
        ),
    ]
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Place",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("category", models.CharField(
                    choices=[
                        ("school", "School"), ("health", "Health"), ("government", "Government"),
                        ("church", "Church"), ("market", "Market & stores"), ("food", "Food"),
                        ("safety", "Police & fire"), ("finance", "Bank & remittance"),
                        ("transport", "Transport"), ("infra", "Roads & utilities"),
                        ("recreation", "Parks & sports"), ("other", "Other"),
                    ],
                    db_index=True, default="other", max_length=20,
                )),
                ("barangay", models.CharField(
                    blank=True,
                    choices=[
                        ("Astorga", "Astorga"), ("Balire", "Balire"), ("Banawang", "Banawang"),
                        ("San Antonio", "San Antonio"), ("San Pedro", "San Pedro"), ("San Roque", "San Roque"),
                        ("San Vicente", "San Vicente"), ("Santo Niño", "Santo Niño"),
                    ],
                    max_length=40,
                )),
                ("description", models.TextField(blank=True)),
                ("contact", models.CharField(blank=True, max_length=120)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("is_published", models.BooleanField(default=True, help_text="Unpublished places are only visible to map editors.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="PlaceImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="tungamap/%Y/%m/")),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("place", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="images", to="tungamap.place",
                )),
            ],
            options={"ordering": ["order", "id"]},
        ),
    ]
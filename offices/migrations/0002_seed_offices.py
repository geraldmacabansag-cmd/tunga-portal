from django.db import migrations

OFFICES = [
    "Office of the Mayor",
    "Office of the Vice Mayor",
    "Sangguniang Bayan (SB) Office",
    "Municipal Treasurer's Office",
    "Municipal Assessor's Office",
    "Municipal Accounting Office",
    "Municipal Budget Office",
    "Municipal Planning and Development Office",
    "Municipal Civil Registrar's Office",
    "Municipal Health Office",
    "Municipal Social Welfare and Development Office (MSWDO)",
    "Municipal Engineering Office",
    "Municipal Agriculture Office",
    "Business Permits and Licensing Office (BPLO)",
    "Human Resource Management Office (HRMO)",
]

def seed_offices(apps, schema_editor):
    Office = apps.get_model("offices", "Office")
    for name in OFFICES:
        slug = (
            name.lower()
            .replace("(", "")
            .replace(")", "")
            .replace(",", "")
            .replace(" ", "-")
        )
        Office.objects.get_or_create(slug=slug, defaults={"name": name})

def unseed_offices(apps, schema_editor):
    Office = apps.get_model("offices", "Office")
    Office.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ("offices", "0001_initial"),  # match the exact filename step c) generated
    ]
    operations = [
        migrations.RunPython(seed_offices, unseed_offices),
    ]
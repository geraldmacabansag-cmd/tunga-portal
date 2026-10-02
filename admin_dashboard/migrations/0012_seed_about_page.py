from django.db import migrations

# The original hardcoded content of templates/portal/about.html, now seeded
# as real rows so the public page keeps looking exactly the same the moment
# it switches over to reading from the database, until a Super Admin edits
# it from the new "About Us Page" screen.

MILESTONES = [
    ("1949", "Executive Order No. 266 was signed on September 26, 1949, creating Tunga as an independent municipality.", False),
    ("1950s", "Establishment of the municipal government and initial development of public services.", False),
    ("1970s", "Expansion of infrastructure, schools, and health services in the municipality.", False),
    ("1990s", "Growth of agriculture and local industries, improving the livelihood of residents.", False),
    ("2000s", "Strengthening of governance and community participation in local development.", False),
    ("Present", "Tunga continues to progress towards a more resilient, inclusive, and sustainable future.", True),
]

OFFICIALS = [
    ("Hon. Pedro D. Dela Cruz", "Municipal Mayor"),
    ("Hon. Maria L. Santos", "Vice Mayor"),
    ("Hon. Juanito R. Reyes", "SB Member"),
    ("Hon. Liza M. Alegre", "SB Member"),
    ("Hon. Ricardo P. Torres", "SB Member"),
]

BARANGAYS_POBLACION = ["San Antonio", "San Pedro", "San Roque", "San Vicente", "Santo Niño"]
BARANGAYS_RURAL = ["Astorga", "Balire", "Banawang"]


def seed_about_page(apps, schema_editor):
    AboutPageContent = apps.get_model("admin_dashboard", "AboutPageContent")
    HistoryMilestone = apps.get_model("admin_dashboard", "HistoryMilestone")
    AboutOfficial = apps.get_model("admin_dashboard", "AboutOfficial")
    Barangay = apps.get_model("admin_dashboard", "Barangay")

    # The singleton row's model defaults already match the hardcoded page,
    # so just make sure it exists.
    AboutPageContent.objects.get_or_create(pk=1)

    if not HistoryMilestone.objects.exists():
        for order, (year_label, description, is_present) in enumerate(MILESTONES):
            HistoryMilestone.objects.create(
                year_label=year_label, description=description, is_present=is_present, order=order
            )

    if not AboutOfficial.objects.exists():
        for order, (name, position) in enumerate(OFFICIALS):
            AboutOfficial.objects.create(name=name, position=position, order=order)

    if not Barangay.objects.exists():
        for order, name in enumerate(BARANGAYS_POBLACION):
            Barangay.objects.create(name=name, group="poblacion", order=order)
        for order, name in enumerate(BARANGAYS_RURAL):
            Barangay.objects.create(name=name, group="rural", order=order)


def unseed_about_page(apps, schema_editor):
    AboutPageContent = apps.get_model("admin_dashboard", "AboutPageContent")
    HistoryMilestone = apps.get_model("admin_dashboard", "HistoryMilestone")
    AboutOfficial = apps.get_model("admin_dashboard", "AboutOfficial")
    Barangay = apps.get_model("admin_dashboard", "Barangay")
    AboutPageContent.objects.filter(pk=1).delete()
    HistoryMilestone.objects.all().delete()
    AboutOfficial.objects.all().delete()
    Barangay.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("admin_dashboard", "0011_aboutofficial_aboutpagecontent_barangay_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_about_page, unseed_about_page),
    ]
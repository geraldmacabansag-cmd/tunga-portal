# Adds the official Tunga emergency hotlines (BFP, PNP, MDRRMO) as the default
# emergency contacts and puts them first on the homepage.
# Runs once (on "python manage.py migrate"). If a hotline with the same number
# already exists it is moved to the top instead of being added twice.
from django.db import migrations

DEFAULT_CONTACTS = [
    # name, category, icon, color, phone, detail
    ("BFP – Fire Emergency", "Fire", "fa-fire", "red",
     "09856193119", "Bureau of Fire Protection"),
    ("PNP – Police Emergency", "Police", "fa-user-shield", "navy",
     "09062863422", "Philippine National Police"),
    ("MDRRMO – Disaster Management", "Medical / Rescue", "fa-life-ring", "red",
     "09815519256", "Municipal Disaster Risk Reduction and Management Office"),
]


def add_defaults(apps, schema_editor):
    EmergencyContact = apps.get_model("admin_dashboard", "EmergencyContact")
    numbers = [c[4] for c in DEFAULT_CONTACTS]

    # Move every other contact below the three defaults.
    for c in EmergencyContact.objects.exclude(phone_number__in=numbers):
        c.order = c.order + len(DEFAULT_CONTACTS)
        c.save(update_fields=["order"])

    for position, (name, category, icon, color, phone, detail) in enumerate(DEFAULT_CONTACTS):
        contact = EmergencyContact.objects.filter(phone_number=phone).first() or EmergencyContact(phone_number=phone)
        contact.name = name
        contact.category = category
        contact.icon = icon
        contact.color = color
        contact.carrier_label = ""
        contact.extra_detail = detail
        contact.order = position
        contact.save()


class Migration(migrations.Migration):

    dependencies = [
        ("admin_dashboard", "0014_sitecontactinfo_site_tagline"),
    ]

    operations = [
        migrations.RunPython(add_defaults, migrations.RunPython.noop),
    ]
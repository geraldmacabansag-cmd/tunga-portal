"""Puts one default pin on the Tunga Map for each barangay, on its barangay
hall (the map has no barangay boundaries to show instead). The About Us page
links each barangay to its pin (/tunga-map/#barangay=<name>).

The places are ordinary map places: the Super Admin can move a pin onto the
exact building, add photos, or rename it in the map editor. A barangay that
already has a "Barangay Hall" place is skipped, so nothing is added twice.
Coordinates: approximate barangay locations from PhilAtlas — check each pin
on the map and drag it onto the hall if needed."""
from django.db import migrations

BARANGAY_HALLS = [
    # (barangay, latitude, longitude)
    ("Astorga", 11.2628, 124.7661),
    ("Balire", 11.2619, 124.7419),
    ("Banawang", 11.2534, 124.7830),
    ("San Antonio", 11.2447, 124.7494),
    ("San Pedro", 11.2514, 124.7550),
    ("San Roque", 11.2512, 124.7483),
    ("San Vicente", 11.2447, 124.7527),
    ("Santo Niño", 11.2473, 124.7528),
]


def hall_name(barangay):
    return f"Barangay Hall of {barangay}"


def add_halls(apps, schema_editor):
    Place = apps.get_model("tungamap", "Place")
    for barangay, lat, lng in BARANGAY_HALLS:
        if Place.objects.filter(barangay=barangay, name__icontains="barangay hall").exists():
            continue
        Place.objects.create(
            name=hall_name(barangay),
            category="government",
            barangay=barangay,
            description=f"Barangay hall of {barangay}, Tunga, Leyte.",
            latitude=lat,
            longitude=lng,
            is_published=True,
        )


def remove_halls(apps, schema_editor):
    Place = apps.get_model("tungamap", "Place")
    Place.objects.filter(name__in=[hall_name(b) for b, _, _ in BARANGAY_HALLS],
                         created_by__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tungamap", "0002_place_label_only"),
    ]

    operations = [
        migrations.RunPython(add_halls, remove_halls),
    ]
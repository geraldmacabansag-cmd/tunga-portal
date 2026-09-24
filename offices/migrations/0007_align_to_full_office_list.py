from django.db import migrations
from django.utils.text import slugify

# current real name (from live admin) -> target full name
RENAMES = {
    "Human Resource Management Office (HRMO)": "Human Resource Management Office",
    "Municipal Social Welfare and Development Office (MSWDO)": "Office of the MSWDO",
    "Municipal Agriculture Office": "Office of the Municipal Agriculture",
    "Business Permits and Licensing Office (BPLO)": "Business Permit and Licensing Office",
    "Municipal Engineering Office": "Municipal Engineer\u2019s Office (Office of the Building Official)",
    "Municipal Accounting Office": "Office of the Municipal Accountant",
    "Municipal Civil Registrar\u2019s Office": "Office of the Municipal Civil Registrar",
}

# genuinely missing from the current 15 — need to be created
NEW_OFFICES = [
    "Municipal Environment and Natural Resources Office",
    "Local Youth Development Office",
    "Municipal Tourism Office",
    "Office of the BAC and the BAC Secretariat",
    "Office of the General Services",
]


def rename_and_create(apps, schema_editor):
    Office = apps.get_model("offices", "Office")

    for old_name, new_name in RENAMES.items():
        Office.objects.filter(name=old_name).update(name=new_name)

    existing_slugs = set(Office.objects.values_list("slug", flat=True))
    for name in NEW_OFFICES:
        if Office.objects.filter(name=name).exists():
            continue
        base_slug = slugify(name)
        slug = base_slug
        n = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{n}"
            n += 1
        Office.objects.create(name=name, slug=slug)
        existing_slugs.add(slug)


def reverse_rename(apps, schema_editor):
    Office = apps.get_model("offices", "Office")
    for old_name, new_name in RENAMES.items():
        Office.objects.filter(name=new_name).update(name=old_name)
    Office.objects.filter(name__in=NEW_OFFICES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("offices", "0006_merge_20260918_2028"),
    ]
    operations = [
        migrations.RunPython(rename_and_create, reverse_rename),
    ]
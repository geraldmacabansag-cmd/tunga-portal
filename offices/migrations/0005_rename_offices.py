from django.db import migrations

# old name -> new name
RENAMES = {
    "Office of the Mayor": "Mayor's Office",
    "Office of the Sangguniang Bayan": "Sangguniang Bayan (SB)",
    "Office of the Municipal Planning and Development Coordinator": "Municipal Planning and Development Coordinator",
    "Human Resource Management Office": "Human Resource Management Office",
    "Office of the Municipal Treasurer": "Municipal Treasurer's Office",
    "Office of the MSWDO": "Municipal Social Welfare and Development Office",
    "Office of the Municipal Agriculture ": "Municipal Agriculture",
    "Municipal Disaster Risk Reduction Management Office": "Municipal Disaster Risk Reduction Management",
    "Municipal Environment and Natural Resources Office": "Municipal Environment and Natural Resources",
    "Business Permit and Licensing Office": "Business Permit and Licensing",
    "Municipal Assessor’s Office": "Municipal Assessor’s",
    "Municipal Health Office": "Municipal Health Office",
    "Municipal Budget Office": "Municipal Budget Office",
    "Municipal Engineer’s Office (Office of the Building Official) ": "Municipal Engineer’s Office",
    "Office of the Municipal Accountant": "Municipal Accountant",
    "Local Youth Development Office": "Local Youth Development",
    "Municipal Tourism Office ": "Municipal Tourism",
    "Office of the Municipal Civil Registrar": "Municipal Civil Registrar",
    "Office of the BAC and the BAC Secretariat": "BAC and the BAC Secretariat",
    "Office of the General Services": "General Services",
    
    # ...add every office you want renamed
}

def rename_offices(apps, schema_editor):
    Office = apps.get_model("offices", "Office")
    for old_name, new_name in RENAMES.items():
        Office.objects.filter(name=old_name).update(name=new_name)

def reverse_rename(apps, schema_editor):
    Office = apps.get_model("offices", "Office")
    for old_name, new_name in RENAMES.items():
        Office.objects.filter(name=new_name).update(name=old_name)

class Migration(migrations.Migration):
    dependencies = [
        ("offices", "0004_alter_office_slug"),  # whatever your latest offices migration currently is
    ]
    operations = [
        migrations.RunPython(rename_offices, reverse_rename),
    ]
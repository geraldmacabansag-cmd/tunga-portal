from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_dashboard', '0008_emailprovidersettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailprovidersettings',
            name='api_key_encrypted',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='emailprovidersettings',
            name='email_address',
            field=models.EmailField(blank=True, help_text='The verified sender email in Brevo', max_length=254),
        ),
    ]
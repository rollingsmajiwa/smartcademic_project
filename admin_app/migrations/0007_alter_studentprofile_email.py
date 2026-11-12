from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0006_studentprofile_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprofile',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]

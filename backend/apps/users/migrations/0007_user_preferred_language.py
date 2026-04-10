# F2 M7 — add preferred_language field for dashboard i18n groundwork

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_alter_user_daily_collection_target_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                choices=[("es", "Español"), ("en", "English")],
                default="es",
                help_text="Preferred UI language for the dashboard",
                max_length=5,
            ),
        ),
    ]

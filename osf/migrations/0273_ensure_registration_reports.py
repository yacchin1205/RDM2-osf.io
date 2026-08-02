from django.db import migrations


def ensure_registration_reports(*args):
    from addons.metadata.report_format import REPORT_FORMATS
    from addons.metadata.utils import ensure_registration_report

    for schema_name, report_name, csv_template in REPORT_FORMATS:
        ensure_registration_report(schema_name, report_name, csv_template)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0272_alter_brand_options_alter_collectionprovider_options_and_more'),
    ]

    operations = [
        migrations.RunPython(ensure_registration_reports, migrations.RunPython.noop),
    ]

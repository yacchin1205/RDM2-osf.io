import importlib

import pytest

from addons.metadata.models import RegistrationReportFormat
from osf.models import RegistrationSchema


pytestmark = pytest.mark.django_db

ensure_registration_reports = importlib.import_module(
    'osf.migrations.0273_ensure_registration_reports'
).ensure_registration_reports


def test_ensure_registration_reports_is_idempotent():
    registration_schema_ids = {
        schema_name: RegistrationSchema.objects.filter(name=schema_name)
        .order_by('-schema_version')
        .first()
        ._id
        for schema_name in [
            '公的資金による研究データのメタデータ登録',
            'ムーンショット目標2データベース（未病DB）のメタデータ登録',
        ]
    }
    expected_formats = {
        (
            registration_schema_ids['公的資金による研究データのメタデータ登録'],
            'メタデータ共通項目2024版CSV形式 (日本語)',
            0,
        ),
        (
            registration_schema_ids['公的資金による研究データのメタデータ登録'],
            'Common Metadata Elements 2024 edition CSV format (English)',
            1,
        ),
        (
            registration_schema_ids['ムーンショット目標2データベース（未病DB）のメタデータ登録'],
            'メタデータ共通項目2024版CSV形式 (日本語)',
            0,
        ),
        (
            registration_schema_ids['ムーンショット目標2データベース（未病DB）のメタデータ登録'],
            'Common Metadata Elements 2024 edition CSV format (English)',
            1,
        ),
    }

    RegistrationReportFormat.objects.all().delete()

    ensure_registration_reports()
    ensure_registration_reports()

    report_formats = RegistrationReportFormat.objects.all()
    assert set(report_formats.values_list('registration_schema_id', 'name', 'order')) == expected_formats
    assert all(report_format.csv_template for report_format in report_formats)

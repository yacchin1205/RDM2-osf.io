import pytest
from celery.states import SUCCESS
from unittest.mock import patch

from admin.rdm_custom_storage_location.export_data.views.restore import ProcessError
from admin.rdm_custom_storage_location.tasks import (
    run_export_data_process,
    run_export_data_rollback_process,
    run_restore_export_data_process,
)


@pytest.mark.feature_202210
@pytest.mark.django_db
@patch('admin.rdm_custom_storage_location.tasks.export.export_data_process')
def test_run_export_data_process(mock_export_data_process):
    mock_export_data_process.return_value = None
    process = run_export_data_process.delay(None, 1, 1, 1)
    assert (process.task_id) is not None
    assert (process.state) == (SUCCESS)


@pytest.mark.feature_202210
@pytest.mark.django_db
@patch('admin.rdm_custom_storage_location.tasks.export.export_data_rollback_process')
def test_run_export_data_rollback_process(mock_export_data_rollback_process):
    mock_export_data_rollback_process.return_value = None
    process = run_export_data_rollback_process.delay(None, 1, 1, 1)
    assert (process.task_id) is not None
    assert (process.state) == (SUCCESS)


@pytest.mark.feature_202210
@pytest.mark.django_db
@patch('admin.rdm_custom_storage_location.tasks.restore.restore_export_data_process')
def test_run_restore_export_data_process(mock_restore_export_data_process):
    mock_restore_export_data_process.return_value = None
    process = run_restore_export_data_process.delay(None, 1, 1, [])
    assert (process.task_id) is not None
    assert (process.state) == ('SUCCESS')


@pytest.mark.feature_202210
@pytest.mark.django_db
@patch('admin.rdm_custom_storage_location.tasks.restore.restore_export_data_process')
def test_run_restore_export_data_process_exception(mock_restore_export_data_process):
    mock_restore_export_data_process.side_effect = ProcessError(f'Mock test abort task.')
    with pytest.raises(ProcessError):
        process = run_restore_export_data_process.delay(None, 1, 1, [])
        assert (process.task_id) is not None
        assert (process.state) == ('FAILURE')

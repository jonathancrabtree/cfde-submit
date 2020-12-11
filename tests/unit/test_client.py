import pytest
from cfde_submit import client, exc


def test_logged_out(logged_out):
    assert client.CfdeClient().is_logged_in() is False


def test_logged_in(logged_in):
    assert client.CfdeClient().is_logged_in() is True


def test_start_deriva_flow_while_logged_out(logged_out):
    with pytest.raises(exc.NotLoggedIn):
        client.CfdeClient().start_deriva_flow('path_to_executable.zip', 'my_dcc')


def test_client_invalid_version(logged_in, mock_remote_config):
    mock_remote_config.return_value['MIN_VERSION'] = '9.9.9'
    with pytest.raises(exc.OutdatedVersion):
        client.CfdeClient().check()


def test_client_permission_denied(logged_in, mock_remote_config, mock_flows_client,
                                  mock_globus_api_error):
    mock_globus_api_error.http_status = 405
    mock_flows_client.get_flow.side_effect = mock_globus_api_error
    with pytest.raises(exc.PermissionDenied):
        client.CfdeClient().check()

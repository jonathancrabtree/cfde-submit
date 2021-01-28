import pytest
from globus_automate_client.flows_client import ALL_FLOW_SCOPES
from cfde_submit import client, exc


def test_logged_out(logged_out):
    assert client.CfdeClient().is_logged_in() is False


def test_logged_in(logged_in):
    assert client.CfdeClient().is_logged_in() is True


def test_scopes(mock_remote_config):
    cfde = client.CfdeClient()
    for service in ["dev", "staging", "prod"]:
        # Ensure all automate scopes are present
        cfde.service_instance = service
        assert not set(ALL_FLOW_SCOPES).difference(cfde.scopes)
        assert f'{service}_cfde_ep_id' in cfde.gcs_https_scope
        assert cfde.flow_scope == (f'https://auth.globus.org/scopes/'
                                   f'{service}_flow_id/flow_{service}_flow_id_user')


def test_start_deriva_flow_while_logged_out(logged_out):
    with pytest.raises(exc.NotLoggedIn):
        client.CfdeClient().start_deriva_flow("path_to_executable.zip", "my_dcc")


def test_client_invalid_version(logged_in, mock_remote_config):
    mock_remote_config.return_value["MIN_VERSION"] = "9.9.9"
    with pytest.raises(exc.OutdatedVersion):
        client.CfdeClient().check()


def test_client_no_flow_id(logged_in, mock_remote_config):
    mock_remote_config.return_value["FLOWS"]["prod"]["flow_id"] = ""
    with pytest.raises(exc.SubmissionsUnavailable):
        client.CfdeClient().check()


def test_client_permission_denied(logged_in, mock_remote_config, mock_flows_client,
                                  mock_globus_api_error):
    mock_globus_api_error.http_status = 405
    mock_flows_client.get_flow.side_effect = mock_globus_api_error
    with pytest.raises(exc.PermissionDenied):
        client.CfdeClient().check()

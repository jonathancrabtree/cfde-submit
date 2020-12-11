from unittest.mock import Mock, PropertyMock
import pytest
import fair_research_login
import globus_sdk

from cfde_submit import CONFIG, version
import cfde_submit

# Maximum output logging!
CONFIG['LOGGING']['handlers']['console']['class'] = 'logging.StreamHandler'
CONFIG['LOGGING']['handlers']['console']['level'] = 'DEBUG'


@pytest.fixture(autouse=True)
def mock_login(monkeypatch):
    """Unit tests should never need to call login() or logout(), as doing so
    would use real developer credentials"""
    monkeypatch.setattr(fair_research_login.NativeClient, "login", Mock())
    monkeypatch.setattr(fair_research_login.NativeClient, "logout", Mock())
    return fair_research_login.NativeClient


@pytest.fixture(autouse=True)
def mock_remote_config(monkeypatch):
    """Ensure no actual remote fetching of config stuff is used
    For the day you want to test fetching remote configs:
    https://stackoverflow.com/questions/38748257/disable-autouse-fixtures-on-specific-pytest-marks
    """
    catalog_keys = ["flow_id", "success_step", "failure_step", "error_step", "cfde_ep_id",
                    "cfde_ep_path", "cfde_ep_url"]
    mock_catalog = {
        "CATALOGS": {
            "prod": "prod",
            "staging": "staging",
            "dev": "dev"
        },
        "FLOWS": {
            "prod": {k: f"prod_{k}" for k in catalog_keys},
            "staging": {k: f"staging_{k}" for k in catalog_keys},
            "dev": {k: f"dev_{k}" for k in catalog_keys},
        },
        "MIN_VERSION": version.__version__
    }
    remote_config = PropertyMock(return_value=mock_catalog)
    monkeypatch.setattr(cfde_submit.CfdeClient, 'remote_config', remote_config)
    return remote_config


@pytest.fixture(autouse=True)
def mock_flows_client(monkeypatch):
    """Ensure there are no calls out to the Globus Automate Client"""
    monkeypatch.setattr(cfde_submit.CfdeClient, 'flow_client', PropertyMock())
    return cfde_submit.CfdeClient.flow_client


@pytest.fixture
def logged_out(monkeypatch):
    load = Mock(side_effect=fair_research_login.LoadError())
    monkeypatch.setattr(fair_research_login.NativeClient, "load_tokens_by_scope", load)
    return fair_research_login.NativeClient


@pytest.fixture
def logged_in(monkeypatch):
    mock_tokens = {
        scope: dict(access_token=f"{scope}_access_token")
        for scope in CONFIG["ALL_SCOPES"]
    }
    load = Mock(return_value=mock_tokens)
    monkeypatch.setattr(fair_research_login.NativeClient, "load_tokens_by_scope", load)
    return fair_research_login.NativeClient


@pytest.fixture
def mock_globus_api_error(monkeypatch):
    class MockGlobusAPIError(Exception):
        pass
    monkeypatch.setattr(globus_sdk, 'GlobusAPIError', MockGlobusAPIError)
    return globus_sdk.GlobusAPIError

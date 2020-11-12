import globus_automate_client


CONFIG = {
    # Files with dynamic config information in JSON
    # Contains:
    #   CATALOGS (dict): keyword: catalog_name
    #   FLOWS (dict): keyword: flow_id
    #   MIN_VERSION (str): The minimum version of the client required
    "DYNAMIC_CONFIG_LINKS": {
        "prod": "https://g-13bbb9.aa98d.08cc.data.globus.org/CFDE/cfde_client_config.json",
        "staging": "",
        "dev": ""
    },
    # TODO: Remove when dynamic config fetching works again (see client.py)
    # Temporary hardcoded value for "dynamic" config
    "TEMP_HARDCODED_CONFIG": {
        "CATALOGS": {
            "prod": "prod",
            "staging": "staging",
            "dev": "dev"
        },
        "FLOWS": {
            "prod": {
                "flow_id": "",
                "success_step": "SuccessState",
                "failure_step": "FailureState",
                "error_step": "ErrorState"
            },
            "staging": {
                "flow_id": "",
                "success_step": "SuccessState",
                "failure_step": "FailureState",
                "error_step": "ErrorState"
            },
            "dev": {
                "flow_id": "ef08993d-2768-4bf5-a98b-9bc261bf9751",
                # TODO: Enable current endpoint for data transfers when practical
                # Temporarily use previous development endpoint for data transfers
                # "cfde_ep_id": "78e2f2f2-1e1d-49e4-a1ef-11552876d517",
                # "cfde_ep_path": "/CFDE/data/",
                # "cfde_ep_url": "https://g-6e4a3.f19a4.5898.data.globus.org",
                "cfde_ep_id": "0e57d793-f1ac-4eeb-a30f-643b082d68ec",
                "cfde_ep_path": "/public/CFDE/metadata/",
                "cfde_ep_url": "https://317ec.36fe.dn.glob.us",

                "success_step": "SuccessState",
                "failure_step": "FailureState",
                "error_step": "ErrorState"
            }
        },
        "MIN_VERSION": "0.0.4"
    },
    # Translations for Automate states into nicer language
    "STATE_MSGS": {
        "ACTIVE": "is still in progress",
        "INACTIVE": "has stalled, and may need help to resume",
        "SUCCEEDED": "has completed successfully",
        "FAILED": "has failed"
    },
    # Automate Scopes
    "HTTPS_SCOPE": "https://auth.globus.org/scopes/0e57d793-f1ac-4eeb-a30f-643b082d68ec/https",
    "AUTOMATE_SCOPES": list(globus_automate_client.flows_client.ALL_FLOW_SCOPES),
    # Format for BDBag archives
    "ARCHIVE_FORMAT": "zip"
}
# Add all necessary scopes together for Auth call
CONFIG["ALL_SCOPES"] = CONFIG["AUTOMATE_SCOPES"] + [CONFIG["HTTPS_SCOPE"]]

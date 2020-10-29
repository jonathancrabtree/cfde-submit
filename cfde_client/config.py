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
                "flow_id": "751c9d70-96c5-48a1-b0b7-3038a2731946",
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
                "flow_id": "751c9d70-96c5-48a1-b0b7-3038a2731946",
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
    # FAIR Research Endpoint destination directory and HTTPS URL
    "EP_DIR": "/public/CFDE/metadata/",
    "EP_UUID": "0e57d793-f1ac-4eeb-a30f-643b082d68ec",
    "EP_URL": "https://317ec.36fe.dn.glob.us",
    # Format for BDBag archives
    "ARCHIVE_FORMAT": "zip"
}
# Add all necessary scopes together for Auth call
CONFIG["ALL_SCOPES"] = CONFIG["AUTOMATE_SCOPES"] + [CONFIG["HTTPS_SCOPE"]]

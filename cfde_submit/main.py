import json
import os
import logging

import click

from cfde_submit import CfdeClient, exc

logger = logging.getLogger(__name__)
DEFAULT_STATE_FILE = os.path.expanduser("~/.cfde_client.json")


@click.group()
def cli():
    """Client to interact with the DERIVA Action Provider and associated Flows."""
    pass


@cli.command()
@click.argument("data-path", nargs=1, type=click.Path(exists=True))
@click.option("--dcc-id", "--dcc", default=None, show_default=True)
@click.option("--catalog", default=None, show_default=True)
@click.option("--schema", default=None, show_default=True)
@click.option("--output-dir", default=None, show_default=True, type=click.Path(exists=False))
@click.option("--delete-dir/--keep-dir", is_flag=True, default=False, show_default=True)
@click.option("--ignore-git/--handle-git", is_flag=True, default=False, show_default=True)
@click.option("--dry-run", is_flag=True, default=False, show_default=True)
@click.option("--test-submission", "--test-sub", "--test-drive", is_flag=True,
              default=False, show_default=True)
@click.option("--verbose", "-v", is_flag=True, default=False, show_default=True)
@click.option("--server", default=None)  # , hidden=True)
@click.option("--force-http", is_flag=True, default=False)  # , hidden=True)
@click.option("--bag-kwargs-file", type=click.Path(exists=True), default=None)  # , hidden=True)
@click.option("--client-state-file", type=click.Path(exists=True), default=None)  # , hidden=True)
def run(data_path, dcc_id, catalog, schema, output_dir, delete_dir, ignore_git,
        dry_run, test_submission, verbose, server, force_http,
        bag_kwargs_file, client_state_file):
    """Start the Globus Automate Flow to ingest CFDE data into DERIVA."""
    # Get any saved parameters
    if not client_state_file:
        client_state_file = DEFAULT_STATE_FILE
    try:
        with open(client_state_file) as f:
            state = json.load(f)
        if verbose:
            print("Loaded previous state")
    except FileNotFoundError:
        state = {}
        if verbose:
            print("No previous state found")

    # Read bag_kwargs_file if provided
    if bag_kwargs_file:
        with open(bag_kwargs_file) as f:
            bag_kwargs = json.load(f)
    else:
        bag_kwargs = {}

    # Determine DCC ID to use
    if verbose:
        print("Determining DCC")
    # If user supplies DCC as option, will always use that
    # If supplied DCC is different from previously saved DCC, prompt to save,
    #   unless user has not saved DCC or disabled the save prompt
    state_dcc = state.get("dcc_id")
    never_save = state.get("never_save")
    if not never_save and dcc_id is not None and state_dcc is not None and state_dcc != dcc_id:
        if verbose:
            print("Saved DCC '{}' mismatch with provided DCC '{}'".format(state_dcc, dcc_id))
        save_dcc = (input("Would you like to save '{}' as your default DCC ID ("
                          "instead of '{}')? y/n: ".format(dcc_id, state_dcc))
                    .strip().lower() in ["y", "yes"])
        if not save_dcc:
            if (input("Would you like to disable this prompt permanently? y/n:").strip().lower()
                    in ["y", "yes"]):
                state["never_save_dcc"] = True
    elif dcc_id is None and state_dcc is not None:
        dcc_id = state_dcc
        save_dcc = False
        print("Using saved DCC '{}'".format(dcc_id))
    elif dcc_id is None and state_dcc is None:
        if verbose:
            print("No saved DCC ID found and no DCC provided")
        dcc_id = input("Please enter the CFDE identifier for your "
                       "Data Coordinating Center: ").strip()
        save_dcc = input("Thank you. Would you like to save '{}' for future submissions? "
                         "y/n: ".format(dcc_id)).strip().lower() in ["y", "yes"]
        # Save DCC ID in state if requested
        if save_dcc:
            state["dcc_id"] = dcc_id
            if verbose:
                print("DCC ID '{}' will be saved if the Flow initialization is successful "
                      "and this is not a dry run"
                      .format(dcc_id))
    try:
        if verbose:
            print("Initializing Flow")
        cfde = CfdeClient()
        if cfde.service_instance != "prod":
            click.secho(f"Running on service '{cfde.service_instance}'", fg="yellow")
        if not cfde.is_logged_in():
            cfde.login()
        if verbose:
            print("CfdeClient initialized, starting Flow")
        resp = input(f"Submit datapackage {os.path.basename(data_path)} using {dcc_id}? (y/N)? > ")
        if resp in ["y", "yes", "Y", "Yes", "aye", "yarr"]:
            start_res = cfde.start_deriva_flow(data_path, dcc_id=dcc_id, catalog_id=catalog,
                                               schema=schema,
                                               output_dir=output_dir, delete_dir=delete_dir,
                                               handle_git_repos=(not ignore_git),
                                               server=server, dry_run=dry_run,
                                               test_sub=test_submission, verbose=verbose,
                                               force_http=force_http, **bag_kwargs)
        else:
            click.secho("Aborted. No data submitted.", fg="yellow")
            return
    except exc.SubmissionsUnavailable as su:
        click.secho(str(su), fg='red')
        return
    except Exception as e:
        logger.exception(e)
        print("Error while starting Flow: {}".format(repr(e)))
        return
    else:
        if not start_res["success"]:
            print("Error during Flow startup: {}".format(start_res["error"]))
        else:
            print(start_res["message"])
            if not dry_run:
                state["service_instance"] = cfde.service_instance
                state["flow_id"] = start_res["flow_id"]
                state["flow_instance_id"] = start_res["flow_instance_id"]
                state["http_link"] = start_res["http_link"]
                state["globus_web_link"] = start_res["globus_web_link"]
                with open(client_state_file, 'w') as out:
                    json.dump(state, out)
                if verbose:
                    print("State saved to '{}'".format(client_state_file))

                filename = os.path.basename(start_res["cfde_dest_path"])
                print("\nThe BDBag with your data is named '{}', and will be available through "
                      "Globus here:\n{}\n".format(filename, state["globus_web_link"]))
                print("You BDBag will also be available via direct HTTP download here:\n{}"
                      .format(state["http_link"]))


@cli.command()
@click.option("--flow-id", default=None, show_default=True)
@click.option("--flow-instance-id", default=None, show_default=True)
@click.option("--raw", is_flag=True, default=False)
@click.option("--client-state-file", type=click.Path(exists=True), default=None)  # , hidden=True)
def status(flow_id, flow_instance_id, raw, client_state_file):
    """Check the status of a Flow."""
    if not flow_id or not flow_instance_id:
        if not client_state_file:
            client_state_file = DEFAULT_STATE_FILE
        try:
            with open(client_state_file) as f:
                client_state = json.load(f)
            flow_id = flow_id or client_state.get("flow_id")
            flow_instance_id = flow_instance_id or client_state.get("flow_instance_id")
            if not flow_id or not flow_instance_id:
                raise ValueError("flow_id or flow_instance_id not found")
        except (FileNotFoundError, ValueError):
            print("Flow not started and flow-id or flow-instance-id not specified")
            return
    try:
        cfde = CfdeClient()
        if cfde.service_instance != "prod":
            click.secho(f"Running on service '{cfde.service_instance}'", fg="yellow")
        status_res = cfde.check_status(flow_id, flow_instance_id, raw=True)
    except Exception as e:
        if raw:
            err = repr(e)
        else:
            err = str(e)
        print("Error checking status for Flow '{}': {}".format(flow_instance_id, err))
        return
    else:
        if raw:
            print(json.dumps(status_res, indent=4, sort_keys=True))
        else:
            print(status_res["clean_status"])


@cli.command()
@click.option("--force-login", is_flag=True, default=False, show_default=True)
@click.option("--no_browser", is_flag=True, default=False)
@click.option("--no_local_server", is_flag=True, default=False)
def login(force_login, no_browser, no_local_server):
    """Perform the login step (which saves credentials) by initializing
    a CfdeClient. The Client is then discarded.
    """
    cfde = CfdeClient()
    if cfde.service_instance != "prod":
        click.secho(f"Running on service '{cfde.service_instance}'", fg="yellow")
    if cfde.is_logged_in():
        click.secho("You are already logged in")
    else:
        cfde.login(force=force_login, no_browser=no_browser, no_local_server=no_local_server)
        click.secho("You are authenticated and your tokens have been cached.", fg='green')
    try:
        cfde.check()
    except exc.CfdeClientException as ce:
        click.secho(str(ce), fg='red')


@cli.command()
def logout():
    """Log out and revoke your tokens."""
    cfde = CfdeClient()
    if cfde.is_logged_in():
        cfde.logout()
        click.secho("You have been logged out", fg='green')
    else:
        click.secho("You are not logged in")

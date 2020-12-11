import json
import os
import logging.config
from packaging.version import parse as parse_version
import shutil

from bdbag import bdbag_api
from datapackage import Package
import fair_research_login
import git
import globus_automate_client
import globus_sdk
import requests
from tableschema.exceptions import CastError

from cfde_submit import CONFIG, exc
from .version import __version__ as VERSION

logging.config.dictConfig(CONFIG["LOGGING"])
logger = logging.getLogger(__name__)


def ts_validate(data_path, schema=None):
    """Validate a given TableSchema using the Datapackage package.

    Arguments:
        data_path (str): Path to the TableSchema JSON or BDBag directory
                or BDBag archive to validate.
        schema (str): The schema to validate against. If not provided,
                the data is only validated against the defined TableSchema.
                Default None.

    Returns:
        dict: The validation results.
            is_valid (bool): Is the TableSchema valid?
            raw_errors (list): The raw Exceptions generated from any validation errors.
            error (str): A formatted error message about any validation errors.
    """
    # If data_path is BDBag archive, unarchive to temp dir
    try:
        data_path = bdbag_api.extract_bag(data_path, temp=True)
    # data_path is not archive
    except RuntimeError:
        pass
    # If data_path is dir (incl. if was unarchived), find JSON desc
    if os.path.isdir(data_path):
        # If 'data' dir present, search there instead
        if "data" in os.listdir(data_path):
            data_path = os.path.join(data_path, "data")
        # Find .json file (cannot be hidden)
        desc_file_list = [filename for filename in os.listdir(data_path)
                          if filename.endswith(".json") and not filename.startswith(".")]
        if len(desc_file_list) < 1:
            return {
                "is_valid": False,
                "raw_errors": [FileNotFoundError("No TableSchema JSON file found.")],
                "error": "No TableSchema JSON file found."
            }
        elif len(desc_file_list) > 1:
            return {
                "is_valid": False,
                "raw_errors": [RuntimeError("Multiple JSON files found in directory.")],
                "error": "Multiple JSON files found in directory."
            }
        else:
            data_path = os.path.join(data_path, desc_file_list[0])
    # data_path should/must be file now (JSON desc)
    if not os.path.isfile(data_path):
        return {
            "is_valid": False,
            "raw_errors": [ValueError("Path '{}' does not refer to a file".format(data_path))],
            "error": "Path '{}' does not refer to a file".format(data_path)
        }

    # Read into Package (identical to DataPackage), return error on failure
    try:
        pkg = Package(descriptor=data_path, strict=True)
    except Exception as e:
        return {
            "is_valid": False,
            "raw_errors": e.errors,
            "error": "\n".join([str(err) for err in pkg.errors])
        }
    # Check and return package validity based on non-Exception-throwing Package validation
    if not pkg.valid:
        return {
            "is_valid": pkg.valid,
            "raw_errors": pkg.errors,
            "error": "\n".join([str(err) for err in pkg.errors])
        }
    # Perform manual validation as well
    for resource in pkg.resources:
        try:
            resource.read()
        except CastError as e:
            return {
                "is_valid": False,
                "raw_errors": e.errors,
                "error": "\n".join([str(err) for err in e.errors])
            }
        except Exception as e:
            return {
                "is_valid": False,
                "raw_errors": repr(e),
                "error": str(e)
            }
    return {
        "is_valid": True,
        "raw_errors": [],
        "error": None
    }


class CfdeClient():
    """The CfdeClient enables easily using the CFDE tools to ingest data."""
    client_id = "417301b1-5101-456a-8a27-423e71a2ae26"
    scopes = CONFIG["ALL_SCOPES"]
    app_name = "CfdeClient"
    archive_format = "tgz"

    def __init__(self, service_instance="prod", tokens=None):
        """Create a CfdeClient.

        Keyword Arguments:
            service_instance (str): The instance of the Globus Automate Flow
                    and/or the DERIVA ingest Action Provider to use. Unless directed otherwise,
                    this should be left to the default. **Default**: ``prod``.
            tokens (dict): A dict keyed by scope, of active Globus Tokens. token keys MUST be a
                    subset of self.scopes. Each token value must contain an additional dict, and
                    have an active "access_token". setting tokens=None will require .login() to
                    be called instead.
                    **Default**: ``None``.
        """
        self.__remote_config = {}  # managed by property
        self.__tokens = {}
        self.__flow_client = None
        self.__native_client = fair_research_login.NativeClient(
            client_id=self.client_id, app_name=self.app_name,
            default_scopes=self.scopes)
        self.last_flow_run = {}
        # Fetch dynamic config info
        self.service_instance = service_instance
        self.tokens = tokens or {}
        # Set to true when self.check() passes
        self.ready = False

    @property
    def version(self):
        return VERSION

    @property
    def tokens(self):
        if not self.__tokens:
            try:
                self.__tokens = self.__native_client.load_tokens_by_scope()
            except fair_research_login.LoadError:
                raise exc.NotLoggedIn("Client has no tokens, either call login() "
                                      "or supply tokens to client on init.")
        return self.__tokens

    @tokens.setter
    def tokens(self, new_tokens):
        # Check tokens, if supplied outside of client
        if new_tokens and set(new_tokens) != set(self.scopes):
            raise exc.NotLoggedIn("Tokens supplied to CfdeClient are invalid, "
                                  f"They MUST match {self.scopes}")

    def login(self, **login_kwargs):
        """Login to the cfde-submit client. This will ensure the user has the correct
        tokens configured but it DOES NOT guarantee they are in the correct group to
        run a flow. Can be run both locally and on a server.
        See help(fair_research_login.NativeClient.login) for a full list of kwargs.
        """
        logger.info("Initiating Native App Login...")
        self.__native_client.login(**login_kwargs)
        logger.debug(f"Logged in with tokens: {self.tokens.keys()}")

    def logout(self):
        """Log out and revoke this client's tokens. This object will no longer
        be usable; to submit additional data or check the status of previous submissions,
        you must create a new CfdeClient.
        """
        self.__native_client.logout()

    def is_logged_in(self):
        try:
            return bool(self.tokens)
        except exc.NotLoggedIn:
            return False

    @property
    def remote_config(self):
        if self.__remote_config:
            return self.__remote_config
        try:
            dconf_res = requests.get(CONFIG["DYNAMIC_CONFIG_LINKS"][self.service_instance])
            if dconf_res.status_code >= 300:
                raise ValueError("Unable to download required configuration: Error {}: {}"
                                 .format(dconf_res.status_code, dconf_res.content))
            self.__remote_config = dconf_res.json()
            return self.__remote_config
        except KeyError as e:
            raise ValueError("Flow configuration for service_instance '{}' not found"
                             .format(self.service_instance)) from e
        except json.JSONDecodeError:
            if b"<!DOCTYPE html>" in dconf_res.content:
                raise ValueError("Unable to authenticate with Globus: "
                                 "HTML authentication flow detected")
            else:
                raise ValueError("Flow configuration not JSON: \n{}".format(dconf_res.content))
        except Exception:
            # TODO: Are there other exceptions that need to be handled/translated?
            raise

    @property
    def flow_client(self):
        if self.__flow_client:
            return self.__flow_client
        flows_token_map = {scope: token["access_token"] for scope, token in self.tokens.items()}
        automate_authorizer = self.__native_client.get_authorizer(
            self.tokens[globus_automate_client.flows_client.MANAGE_FLOWS_SCOPE])
        # The flows client requires both a token map of flows it can call, in addition to
        # its own authorizer to talk to the core automate service. Ideally, this would be
        # cleaner so we wouldn't have to track the tokens and authorizer separately.
        self.__flow_client = globus_automate_client.FlowsClient(
            flows_token_map, self.client_id, "flows_client",
            app_name=self.app_name,
            base_url="https://flows.automate.globus.org",
            authorizer=automate_authorizer
        )
        return self.__flow_client

    @property
    def https_authorizer(self):
        try:
            return self.__native_client.get_authorizers_by_scope()[CONFIG["HTTP_SCOPE"]]
        except (fair_research_login.LoadError, KeyError):
            at = self.tokens[CONFIG["HTTPS_SCOPE"]]["access_token"]
            return globus_sdk.AccessTokenAuthorizer(at)

    def check(self, raise_exception=True):
        if self.ready:
            return True
        try:
            if not self.tokens:
                logger.debug('No tokens for client, attempting load...')
                self.tokens = self.__native_client.load_tokens_by_scope()
            # Verify client version is compatible with service
            if parse_version(self.remote_config["MIN_VERSION"]) > parse_version(VERSION):
                raise exc.OutdatedVersion(
                    "This CFDE Client is not up to date and can no longer make "
                    "submissions. Please update the client and try again."
                )

            if not self.remote_config["FLOWS"][self.service_instance]["flow_id"]:
                logger.critical(f"Service {self.service_instance} has no flow ID! "
                                f"Submissions will be disabled until that is set!")
                raise exc.SubmissionsUnavailable(
                    "Submissions to nih-cfde.org are temporarily offline. Please check "
                    "with out administrators for further details.")
            # Verify user has permission to view Flow
            try:
                flow_info = self.remote_config["FLOWS"][self.service_instance]
                self.flow_client.get_flow(flow_info["flow_id"])
            except globus_sdk.GlobusAPIError as e:
                logger.debug(str(e))
                if e.http_status == 405:
                    raise exc.PermissionDenied(
                                "Unable to view ingest Flow. Are you in the CFDE DERIVA "
                                "Demo Globus Group? Check your membership or apply for access "
                                "here: \nhttps://app.globus.org/groups/a437abe3-c9a4-11e9-b441-"
                                "0efb3ba9a670/about")
                else:
                    raise
            self.ready = True
            logger.info('Check PASSED, client is ready use flows.')
        except Exception:
            logger.info('Check FAILED, client lacks permissions or is not logged in.')
            self.ready = False
            if raise_exception is True:
                raise

    def start_deriva_flow(self, data_path, dcc_id, catalog_id=None,
                          schema=None, server=None, dataset_acls=None,
                          output_dir=None, delete_dir=False, handle_git_repos=True,
                          dry_run=False, test_sub=False, verbose=False, **kwargs):
        """Start the Globus Automate Flow to ingest CFDE data into DERIVA.

        Arguments:
            data_path (str): The path to the data to ingest into DERIVA. The path can be:
                    1) A directory to be formatted into a BDBag
                    2) A Git repository to be copied into a BDBag
                    3) A premade BDBag directory
                    4) A premade BDBag in an archive file
            dcc_id (str): The CFDE-recognized DCC ID for this submission.
            catalog_id (int or str): The ID of the DERIVA catalog to ingest into.
                    Default None, to create a new catalog.
            schema (str): The named schema or schema file link to validate data against.
                    Default None, to only validate against the declared TableSchema.
            server (str): The DERIVA server to ingest to.
                    Default None, to use the Action Provider-set default.
            dataset_acls (dict): The DERIVA ACL(s) to set on the final dataset.
                    Default None, to use the CFDE default ACLs.
            output_dir (str): The path to create an output directory in. The resulting
                    BDBag archive will be named after this directory.
                    If not set, the directory will be turned into a BDBag in-place.
                    For Git repositories, this is automatically set, but can be overridden.
                    If data_path is a file, this has no effect.
                    This dir MUST NOT be in the `data_path` directory or any subdirectories.
                    Default None.
            delete_dir (bool): Should the output_dir be deleted after submission?
                    Has no effect if output_dir is not specified.
                    For Git repositories, this is always True.
                    Default False.
            handle_git_repos (bool): Should Git repositories be detected and handled?
                    When this is False, Git repositories are handled as simple directories
                    instead of Git repositories.
                    Default True.
            dry_run (bool): Should the data be validated and bagged without starting the Flow?
                    When True, does not ingest into DERIVA or start the Globus Automate Flow,
                    and the return value will not have valid DERIVA Flow information.
                    Default False.
            test_sub (bool): Should the submission be run in "test mode" where
                    the submission will be inegsted into DERIVA and immediately deleted?
                    When True, the data wil not remain in DERIVA to be viewed and the
                    Flow will terminate before any curation step.
            verbose (bool): Should intermediate status messages be printed out?
                    Default False.

        Keyword Arguments:
            force_http (bool): Should the data be sent using HTTP instead of Globus Transfer,
                    even if Globus Transfer is available? Because Globus Transfer is more
                    robust than HTTP, it is highly recommended to leave this False.
                    Default False.

        Other keyword arguments are passed directly to the ``make_bag()`` function of the
        BDBag API (see https://github.com/fair-research/bdbag for details).
        """
        self.check()
        if verbose:
            print("Startup: Validating input")
        data_path = os.path.abspath(data_path)
        if not os.path.exists(data_path):
            raise FileNotFoundError("Path '{}' does not exist".format(data_path))

        catalogs = self.remote_config['CATALOGS']
        if catalog_id in catalogs.keys():
            if schema:
                raise ValueError("You may not specify a schema ('{}') when ingesting to "
                                 "a named catalog ('{}'). Retry without specifying "
                                 "a schema.".format(schema, catalog_id))
            schema = catalogs[catalog_id]
        # Pull out known kwargs
        force_http = kwargs.pop("force_http", False)

        if handle_git_repos:
            if verbose:
                print("Checking for a Git repository")
            # If Git repo, set output_dir appropriately
            try:
                repo = git.Repo(data_path, search_parent_directories=True)
            # Not Git repo
            except git.InvalidGitRepositoryError:
                if verbose:
                    print("Not a Git repo")
            # Path not found, turn into standard FileNotFoundError
            except git.NoSuchPathError:
                raise FileNotFoundError("Path '{}' does not exist".format(data_path))
            # Is Git repo
            else:
                if verbose:
                    print("Git repo found, collecting metadata")
                # Needs to not have slash at end - is known Git repo already, slash
                # interferes with os.path.basename/dirname
                if data_path.endswith("/"):
                    data_path = data_path[:-1]
                # Set output_dir to new dir named with HEAD commit hash
                new_dir_name = "{}_{}".format(os.path.basename(data_path), str(repo.head.commit))
                output_dir = os.path.join(os.path.dirname(data_path), new_dir_name)
                # Delete temp dir after archival
                delete_dir = True

        # If dir and not already BDBag, make BDBag
        if os.path.isdir(data_path) and not bdbag_api.is_bag(data_path):
            if verbose:
                print("Creating BDBag out of directory '{}'".format(data_path))
            # If output_dir specified, copy data to output dir first
            if output_dir:
                if verbose:
                    print("Copying data to '{}' before creating BDBag".format(output_dir))
                output_dir = os.path.abspath(output_dir)
                # If shutil.copytree is called when the destination dir is inside the source dir
                # by more than one layer, it will recurse infinitely.
                # (e.g. /source => /source/dir/dest)
                # Exactly one layer is technically okay (e.g. /source => /source/dest),
                # but it's easier to forbid all parent/child dir cases.
                # Check for this error condition by determining if output_dir is a child
                # of data_path.
                if os.path.commonpath([data_path]) == os.path.commonpath([data_path, output_dir]):
                    raise ValueError("The output_dir ('{}') must not be in data_path ('{}')"
                                     .format(output_dir, data_path))
                try:
                    shutil.copytree(data_path, output_dir)
                except FileExistsError:
                    raise FileExistsError(("The output directory must not exist. "
                                           "Delete '{}' to submit.\nYou can set delete_dir=True "
                                           "to avoid this issue in the future.").format(output_dir))
                # Process new dir instead of old path
                data_path = output_dir
            # If output_dir not specified, never delete data dir
            else:
                delete_dir = False
            # Make bag
            bdbag_api.make_bag(data_path, **kwargs)
            if not bdbag_api.is_bag(data_path):
                raise ValueError("Failed to create BDBag from {}".format(data_path))
            elif verbose:
                print("BDBag created at '{}'".format(data_path))

        # If dir (must be BDBag at this point), archive
        if os.path.isdir(data_path):
            if verbose:
                print("Archiving BDBag at '{}' using '{}'"
                      .format(data_path, CONFIG["ARCHIVE_FORMAT"]))
            new_data_path = bdbag_api.archive_bag(data_path, CONFIG["ARCHIVE_FORMAT"])
            if verbose:
                print("BDBag archived to file '{}'".format(new_data_path))
            # If requested (e.g. Git repo copied dir), delete data dir
            if delete_dir:
                if verbose:
                    print("Removing old directory '{}'".format(data_path))
                shutil.rmtree(data_path)
            # Overwrite data_path - don't care about dir for uploading
            data_path = new_data_path

        # Validate TableSchema in BDBag
        if verbose:
            print("Validating TableSchema in BDBag '{}'".format(data_path))
        validation_res = ts_validate(data_path, schema=schema)
        if not validation_res["is_valid"]:
            return {
                "success": False,
                "error": ("TableSchema invalid due to the following errors: \n{}\n"
                          .format(validation_res["error"]))
            }
        elif verbose:
            print("Validation successful")

        # Now BDBag is archived file
        # Set path on destination
        flow_info = self.remote_config["FLOWS"][self.service_instance]
        dest_path = "{}{}".format(flow_info["cfde_ep_path"], os.path.basename(data_path))

        # If doing dry run, stop here before making Flow input
        if dry_run:
            return {
                "success": True,
                "message": "Dry run validated successfully. No data was transferred."
            }

        # Set up Flow
        if verbose:
            print("Creating input for Flow")
        # If local EP exists (and not force_http), can use Transfer
        # Local EP fetched now in case GCP started after Client creation
        local_endpoint = globus_sdk.LocalGlobusConnectPersonal().endpoint_id
        if local_endpoint and not force_http:
            if verbose:
                print("Using local Globus Connect Personal Endpoint '{}'".format(local_endpoint))
            # Populate Transfer fields in Flow
            flow_id = flow_info["flow_id"]
            flow_input = {
                "source_endpoint_id": local_endpoint,
                "source_path": data_path,
                "cfde_ep_id": flow_info["cfde_ep_id"],
                "cfde_ep_path": dest_path,
                "cfde_ep_url": flow_info["cfde_ep_url"],
                "is_directory": False,
                "test_sub": test_sub,
                "dcc_id": dcc_id
            }
            if catalog_id:
                flow_input["catalog_id"] = str(catalog_id)
            if server:
                flow_input["server"] = server
        # Otherwise, we must PUT the BDBag on the server
        else:
            if verbose:
                print("No Globus Endpoint detected; using HTTP upload instead")
            headers = {}
            https_authorizer = self.https_authorizer
            https_authorizer.set_authorization_header(headers)
            data_url = "{}{}".format(flow_info["cfde_ep_url"], dest_path)

            with open(data_path, 'rb') as bag_file:
                bag_data = bag_file.read()

            put_res = requests.put(data_url, data=bag_data, headers=headers)

            # Regenerate headers on 401
            if put_res.status_code == 401:
                https_authorizer.handle_missing_authorization()
                https_authorizer.set_authorization_header(headers)
                put_res = requests.put(data_url, data=bag_data, headers=headers)

            # Error message on failed PUT or any unexpected response
            if put_res.status_code >= 300:
                return {
                    "success": False,
                    "error": ("Could not upload BDBag to server (error {}):\n{}"
                              .format(put_res.status_code, put_res.content))
                }
            elif put_res.status_code != 200:
                print("Warning: HTTP upload returned status code {}, which was unexpected."
                      .format(put_res.status_code))

            if verbose:
                print("Upload successful to '{}': {} {}".format(data_url, put_res.status_code,
                                                                put_res.content))

            flow_id = flow_info["flow_id"]
            flow_input = {
                "source_endpoint_id": False,
                "data_url": data_url,
                "test_sub": test_sub,
                "dcc_id": dcc_id
            }
            if catalog_id:
                flow_input["catalog_id"] = str(catalog_id)
            if server:
                flow_input["server"] = server

        if verbose:
            print("Flow input populated:\n{}".format(json.dumps(flow_input, indent=4,
                                                                sort_keys=True)))
        # Get Flow scope
        flow_def = self.flow_client.get_flow(flow_id)
        flow_scope = flow_def["globus_auth_scope"]
        # Start Flow
        if verbose:
            print("Starting Flow - Submitting data")
        try:
            flow_res = self.flow_client.run_flow(flow_id, flow_scope, flow_input)
        except globus_sdk.GlobusAPIError as e:
            if e.http_status == 404:
                return {
                    "success": False,
                    "error": ("Could not access ingest Flow. Are you in the CFDE DERIVA "
                              "Demo Globus Group? Check your membership or apply for access "
                              "here: https://app.globus.org/groups/a437abe3-c9a4-11e9-b441-"
                              "0efb3ba9a670/about")
                }
            else:
                raise
        self.last_flow_run = {
            "flow_id": flow_id,
            "flow_instance_id": flow_res["action_id"]
        }
        if verbose:
            print("Flow started successfully.")

        return {
            "success": True,
            "message": ("Started DERIVA ingest Flow\nFlow ID: {}\nFlow Instance ID: {}"
                        .format(flow_id, flow_res["action_id"])),
            "flow_id": flow_id,
            "flow_instance_id": flow_res["action_id"],
            "cfde_dest_path": dest_path,
            "http_link": "{}{}".format(flow_info["cfde_ep_url"], dest_path),
            "globus_web_link": ("https://app.globus.org/file-manager?origin_id={}&origin_path={}"
                                .format(flow_info["cfde_ep_id"], os.path.dirname(dest_path)))
        }

    def check_status(self, flow_id=None, flow_instance_id=None, raw=False):
        """Check the status of a Flow. By default, check the status of the last
        Flow run with this instantiation of the client.

        Arguments:
            flow_id (str): The ID of the Flow run. Default: The last run Flow ID.
            flow_instance_id (str): The ID of the Flow to check.
                    Default: The last Flow instance run with this client.
            raw (bool): Should the status results be returned?
                    Default: False, to print the results instead.
        """
        self.check()
        if not flow_id:
            flow_id = self.last_flow_run.get("flow_id")
        if not flow_instance_id:
            flow_instance_id = self.last_flow_run.get("flow_instance_id")
        if not flow_id or not flow_instance_id:
            raise ValueError("Flow not started and IDs not specified.")

        # Get Flow scope and status
        flow_def = self.flow_client.get_flow(flow_id)
        flow_status = self.flow_client.flow_action_status(flow_id, flow_def["globus_auth_scope"],
                                                          flow_instance_id).data
        flow_info = self.remote_config["FLOWS"][self.service_instance]

        clean_status = ("\nStatus of {} (Flow ID {})\nThis instance ID: {}\n\n"
                        .format(flow_def["title"], flow_id, flow_instance_id))
        # Flow overall status
        # NOTE: Automate Flows do NOT fail automatically if an Action fails.
        #       Any "FAILED" Flow has an error in the Flow itself.
        #       Therefore, "SUCCEEDED" Flows are not guaranteed to have actually succeeded.
        if flow_status["status"] == "ACTIVE":
            clean_status += "This Flow is still in progress.\n"
        elif flow_status["status"] == "INACTIVE":
            clean_status += "This Flow has stalled, and may need help to resume.\n"
        elif flow_status["status"] == "SUCCEEDED":
            clean_status += "This Flow has completed.\n"
        elif flow_status["status"] == "FAILED":
            clean_status += "This Flow has failed.\n"
        # "Details"
        if flow_status["details"].get("details"):
            if flow_status["details"]["details"].get("state_name"):
                clean_status += ("Current Flow Step: {}"
                                 .format(flow_status["details"]["details"]["state_name"]))
            # "cause" indicates a failure mode
            if flow_status["details"]["details"].get("cause"):
                cause = flow_status["details"]["details"]["cause"]
                # Try to pretty-print massive blob of state
                try:
                    str_cause, dict_cause = cause.split(" '{")
                    dict_cause = "{" + dict_cause.strip("'")
                    dict_cause = json.loads(dict_cause)["UserState"]
                    dict_cause.pop("prevars", None)
                    dict_cause.pop("vars", None)
                    dict_cause = json.dumps(dict_cause, indent=4, sort_keys=True)
                    cause = str_cause + "\n" + dict_cause
                except Exception:
                    pass
                clean_status += "Error: {}\n".format(cause)
        # Too onerous to pull out results of each step (when even available),
        # also would defeat dynamic config and tie client to Flow.
        # Instead, print out whatever is provided in `details` if Flow FAILED,
        # or print out the appropriate field(s) for the "SUCCEEDED" Flow.
        if flow_status["status"] == "SUCCEEDED":
            flow_output = flow_status["details"]["output"]
            # Each Step is only present in exactly one "SUCCEEDED" Flow result,
            # and they are mutually exclusive
            success_step = flow_info["success_step"]
            failure_step = flow_info["failure_step"]
            error_step = flow_info["error_step"]
            if success_step in flow_output.keys():
                clean_status += flow_output[success_step]["details"]["message"]
            elif failure_step in flow_output.keys():
                clean_status += flow_output[failure_step]["details"]["error"]
            elif error_step in flow_output.keys():
                clean_status += flow_output[error_step]["details"]["error"]
            else:
                clean_status += ("Submission errored: The Flow has finished, but no final "
                                 "details are available.")
        elif flow_status["status"] == "FAILED":
            # Every Flow step can supply failure messages differently, so unfortunately
            # printing out the entire details block is the only way to actually get
            # the error message out.
            # "cause" is printed earlier when available, so avoid double-printing it
            if flow_status["details"].get("details", {}).get("cause"):
                clean_status += "Submission Flow failed."
            else:
                details = flow_status.get("details", "No details available")
                # Try to pretty-print JSON blob
                try:
                    details = json.dumps(details, indent=4, sort_keys=True)
                except Exception:
                    pass
                clean_status += "Submission Flow failed: {}".format(details)

        # Extra newline for cleanliness
        clean_status += "\n"
        # Return or print status
        if raw:
            return {
                "success": True,
                "status": flow_status,
                "clean_status": clean_status
            }
        else:
            print(clean_status)

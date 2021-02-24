import os
import logging

from bdbag import bdbag_api
from datapackage import Package
from tableschema.exceptions import CastError

from cfde_submit import exc

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


def validate_user_submission(data_path, schema, output_dir=None, delete_dir=False,
                             handle_git_repos=True, bdbag_kwargs=None):
    """
    Arguments:
        data_path (str): The path to the data to ingest into DERIVA. The path can be:
                1) A directory to be formatted into a BDBag
                2) A Git repository to be copied into a BDBag
                3) A premade BDBag directory
                4) A premade BDBag in an archive file
        schema (str): The named schema or schema file link to validate data against.
                Default None, to only validate against the declared TableSchema.
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
        bdbag_kwargs (dict): Extra args to pass to bdbag
    """

    # Validate TableSchema in BDBag
    logger.debug("Validating TableSchema in BDBag '{}'".format(data_path))
    validation_res = ts_validate(data_path, schema=schema)
    if not validation_res["is_valid"]:
        raise exc.ValidationException("TableSchema invalid due to the following errors: "
                                      "\n{}\n".format(validation_res["error"]))

    logger.debug("Validation successful")
    return data_path

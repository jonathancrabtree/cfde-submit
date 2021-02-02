import logging
import requests


logger = logging.getLogger(__name__)


def upload(data_path, destination_url, authorizer):
    logger.debug("No Globus Endpoint detected; using HTTP upload instead")
    headers = {}
    # https_authorizer = https_authorizer
    authorizer.set_authorization_header(headers)
    # data_url = "{}{}".format(flow_info["cfde_ep_url"], dest_path)

    with open(data_path, 'rb') as bag_file:
        put_res = requests.put(destination_url, data=bag_file, headers=headers)

    # Regenerate headers on 401
    if put_res.status_code == 401:
        authorizer.handle_missing_authorization()
        authorizer.set_authorization_header(headers)
        with open(data_path, 'rb') as bag_file:
            put_res = requests.put(destination_url, data=bag_file, headers=headers)
    # Error message on failed PUT or any unexpected response
    if put_res.status_code >= 300:
        return {
            "success": False,
            "error": ("Could not upload BDBag to server (error {}):\n{}"
                      .format(put_res.status_code, put_res.content))
        }
    elif put_res.status_code != 200:
        logger.warning("Warning: HTTP upload returned status code {}, "
                       "which was unexpected.".format(put_res.status_code))

    logger.info("Upload successful to '{}': {} {}".format(destination_url, put_res.status_code,
                                                           put_res.content))
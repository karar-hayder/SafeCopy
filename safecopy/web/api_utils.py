import logging

from flask import jsonify

logger = logging.getLogger("safecopy.web.api")


def standard_response(
    success: bool,
    message: str = "",
    data: any = None,
    error: str = "",
    status_code: int = 200,
):
    """
    Returns a standardized JSON response format.
    """
    if not success:
        logger.error("API error: %s (status: %d)", error, status_code)
    elif message:
        logger.info("API success: %s", message)

    response = {"success": success, "message": message, "data": data, "error": error}
    return jsonify(response), status_code

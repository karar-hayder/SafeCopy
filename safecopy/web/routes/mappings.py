from flask import request
from flask_login import current_user, login_required
from pydantic import ValidationError

from safecopy.db.dtos.mappingsDTOs import MappingsCreateDTO, MappingsUpdateDTO
from safecopy.db.services.mappingsService import MappingsService
from safecopy.web.api_utils import standard_response

service = MappingsService()


@login_required
def get_mappings():
    """Get all mappings for the current user."""
    try:
        mappings = service.get_all(user_uuid=current_user.uuid)
        data = {"mappings": [m.model_dump() for m in mappings]}
        return standard_response(
            True, message="Mappings retrieved successfully", data=data
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def save_mappings():
    """Save/update mappings for the current user."""
    try:
        data = request.get_json()
        if not data or "mappings" not in data:
            return standard_response(
                False, error="Invalid request data", status_code=400
            )

        for mapping_data in data["mappings"]:
            uuid = mapping_data.get("uuid")
            if uuid:
                service.update(uuid, MappingsUpdateDTO(**mapping_data))
            else:
                mapping_data["user_uuid"] = current_user.uuid
                service.create(MappingsCreateDTO(**mapping_data))

        return standard_response(True, message="Mappings saved successfully")
    except (ValueError, ValidationError) as e:
        return standard_response(False, error=str(e), status_code=400)
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def delete_mapping():
    """Delete a mapping by UUID."""
    try:
        data = request.get_json() if request.is_json else request.form
        uuid = data.get("uuid") or request.args.get("uuid")

        if not uuid:
            return standard_response(False, error="UUID is required", status_code=400)

        if service.delete(uuid):
            return standard_response(True, message="Mapping deleted successfully")
        return standard_response(False, error="Mapping not found", status_code=404)
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)

from flask import request
from flask_login import current_user, login_required

from safecopy.db.dtos.backupSchedulesDTOs import BackupSchedulesCreateDTO
from safecopy.db.services.backupSchedulesService import BackupSchedulesService
from safecopy.scheduler import engine as advanced_scheduler
from safecopy.web.api_utils import standard_response

service = BackupSchedulesService()


@login_required
def get_schedules():
    """Get all schedules for a mapping."""
    try:
        mapping_uuid = request.args.get("mapping_uuid")
        if not mapping_uuid:
            return standard_response(
                False, error="mapping_uuid is required", status_code=400
            )

        schedules = service.get_all(
            mapping_uuid=mapping_uuid, user_uuid=current_user.uuid
        )
        data = {"schedules": [s.model_dump() for s in schedules]}
        return standard_response(
            True, message="Schedules retrieved successfully", data=data
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def add_schedule():
    """Add a schedule for a mapping."""
    try:
        data = request.get_json()
        data["user_uuid"] = current_user.uuid
        dto = BackupSchedulesCreateDTO(**data)
        schedule = service.create(dto)
        advanced_scheduler.setup_all_schedules()
        return standard_response(
            True,
            message="Schedule added successfully",
            data={"schedule_uuid": schedule.uuid},
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def delete_schedule(schedule_uuid):
    """Delete a schedule."""
    try:
        if service.delete(schedule_uuid):
            advanced_scheduler.setup_all_schedules()
            return standard_response(True, message="Schedule deleted successfully")
        return standard_response(False, error="Schedule not found", status_code=404)
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)

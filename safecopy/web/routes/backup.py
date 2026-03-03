from flask import request
from flask_login import current_user, login_required

from safecopy import notifications
from safecopy.backup.dtos import BackupConfig
from safecopy.backup.enums import CompressionType as BackupCompressionType
from safecopy.backup.runner import run_backups_parallel
from safecopy.db.services.backupHistoryService import BackupHistoryService
from safecopy.db.services.userService import UserService
from safecopy.web.api_utils import standard_response

history_service = BackupHistoryService()
user_service = UserService()


@login_required
def run_backup():
    """Run configured backups."""
    try:
        data = request.get_json()
        mappings = data.get("mappings", [])
        if not mappings:
            return standard_response(
                False, error="No mappings provided", status_code=400
            )

        # Convert to BackupConfig DTOs
        configs = []
        user_info = user_service.get_by_uuid(current_user.uuid)
        user_settings = (
            user_info.settings if user_info and hasattr(user_info, "settings") else {}
        )

        for m in mappings:
            # Handle compression enum conversion
            comp_str = m.get("compression", user_settings.get("compression", "none"))
            try:
                # Find matching backup enum member by its first tuple value
                comp_type = next(
                    c for c in BackupCompressionType if c.value[0] == comp_str.lower()
                )
            except StopIteration:
                comp_type = BackupCompressionType.NONE

            config_data = {
                "uuid": m.get("uuid", ""),
                "user_uuid": current_user.uuid,
                "source": m.get("source"),
                "destination": m.get("destination"),
                "compression": comp_type,
                "encrypted": (
                    m.get("encrypted")
                    if m.get("encrypted") is not None
                    else m.get("encryption", user_settings.get("encrypted", False))
                ),
                "passwd": m.get("encrypt_key") or m.get("password") or "",
                "max_versions": m.get("max_versions")
                or user_settings.get("maxVersions", 3),
            }
            configs.append(BackupConfig(**config_data))

        results = run_backups_parallel(configs)
        return standard_response(
            True, message="Backups triggered successfully", data={"results": results}
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def get_history():
    """Get backup history for the current user."""
    try:
        limit = int(request.args.get("limit", 50))
        history = history_service.get_all(user_uuid=current_user.uuid, page_size=limit)
        data = {"history": [h.model_dump() for h in history]}
        return standard_response(
            True, message="History retrieved successfully", data=data
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def get_backup_settings():
    """Get user-specific backup settings."""
    try:
        user = user_service.get_by_uuid(current_user.uuid)
        settings = user.settings if user and hasattr(user, "settings") else {}
        return standard_response(
            True, message="Settings retrieved successfully", data={"settings": settings}
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def save_backup_settings():
    """Save user-specific backup settings."""
    try:
        data = request.get_json()
        settings = data.get("settings", {})
        from safecopy.db.dtos.userDTOs import UserUpdateDTO

        user_service.update(current_user.uuid, UserUpdateDTO(settings=settings))
        return standard_response(True, message="Settings saved successfully")
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def email_settings():
    """Get or save email notification settings."""
    try:
        if request.method == "GET":
            settings = notifications.get_email_settings()
            return standard_response(
                True,
                message="Email settings retrieved",
                data={"settings": settings or {}},
            )
        else:
            data = request.get_json()
            success = notifications.save_email_settings(
                smtp_server=data.get("smtp_server"),
                smtp_port=int(data.get("smtp_port", 587)),
                from_email=data.get("from_email"),
                to_email=data.get("to_email"),
                smtp_username=data.get("smtp_username"),
                smtp_password=data.get("smtp_password"),
                use_tls=data.get("use_tls", True),
                enabled=data.get("enabled", True),
            )
            if success:
                return standard_response(
                    True, message="Email settings saved successfully"
                )
            return standard_response(
                False, error="Failed to save email settings", status_code=400
            )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)

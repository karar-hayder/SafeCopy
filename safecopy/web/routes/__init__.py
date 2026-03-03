from .auth import (
    change_password,
    create_user,
    get_users,
    login_route,
    logout_route,
    users_route,
)
from .backup import (
    email_settings,
    get_backup_settings,
    get_history,
    run_backup,
    save_backup_settings,
)
from .main import index_route, settings_route
from .mappings import delete_mapping, get_mappings, save_mappings
from .schedules import add_schedule, delete_schedule, get_schedules
from .utils import browse_folders, folder_preview

auth_routes = [
    ("/login", login_route, "login", ["GET", "POST"]),
    ("/logout", logout_route, "logout", ["GET"]),
    ("/users", users_route, "users", ["GET"]),
    ("/get_users", get_users, "get_users", ["GET"]),
    ("/create_user", create_user, "create_user", ["POST"]),
    ("/change_password", change_password, "change_password", ["POST"]),
]

main_routes = [
    ("/", index_route, "index", ["GET"]),
    ("/settings", settings_route, "settings", ["GET"]),
    ("/run_backup", run_backup, "run_backup", ["POST"]),
    ("/get_backup_history", get_history, "get_backup_history", ["GET"]),
    ("/get_backup_settings", get_backup_settings, "get_backup_settings", ["GET"]),
    ("/save_backup_settings", save_backup_settings, "save_backup_settings", ["POST"]),
    ("/email_settings", email_settings, "email_settings", ["GET", "POST"]),
    ("/get_mappings", get_mappings, "get_mappings", ["GET"]),
    ("/save_mappings", save_mappings, "save_mappings", ["POST"]),
    ("/delete_mapping", delete_mapping, "delete_mapping", ["POST"]),
    ("/get_schedules", get_schedules, "get_schedules", ["GET"]),
    ("/add_schedule", add_schedule, "add_schedule", ["POST"]),
    (
        "/delete_schedule/<string:schedule_uuid>",
        delete_schedule,
        "delete_schedule",
        ["DELETE"],
    ),
    ("/browse_folders", browse_folders, "browse_folders", ["GET"]),
    ("/folder_preview", folder_preview, "folder_preview", ["GET"]),
]

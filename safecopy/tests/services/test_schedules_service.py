import pytest

from safecopy.db.dtos.backupSchedulesDTOs import BackupSchedulesCreateDTO
from safecopy.db.dtos.mappingsDTOs import MappingsCreateDTO
from safecopy.db.dtos.userDTOs import UserCreateDTO
from safecopy.db.enums import (
    CompressionType,
    PasswdMode,
    ScheduleIntervalType,
    ScheduleType,
    UserRole,
)
from safecopy.db.services.backupSchedulesService import BackupSchedulesService
from safecopy.db.services.mappingsService import MappingsService
from safecopy.db.services.userService import UserService


@pytest.fixture
def setup_mapping(db_session):
    user_s = UserService()
    map_s = MappingsService()

    user_s.register(
        UserCreateDTO(
            username="sched_user",
            password="password123",
            role=UserRole.USER,
            settings={},
        )
    )
    u_obj = user_s.get_user_by_username("sched_user")

    mapping = map_s.create(
        MappingsCreateDTO(
            user_uuid=u_obj.uuid,
            source="/s",
            destination="/d",
            max_versions=1,
            compression=CompressionType.NONE,
            enabled=True,
            encrypted=False,
            passwd_mode=PasswdMode.NONE,
        )
    )
    return u_obj, mapping


def test_backup_schedules_crud(db_session, setup_mapping):
    user_obj, mapping_obj = setup_mapping
    service = BackupSchedulesService()

    create_dto = BackupSchedulesCreateDTO(
        user_uuid=user_obj.uuid,
        mapping_uuid=mapping_obj.uuid,
        schedule_type=ScheduleType.DAILY,
        schedule_value="14:30",
        schedule_interval=1,
        schedule_interval_type=ScheduleIntervalType.DAYS,
        enabled=True,
    )

    schedule = service.create(create_dto)
    assert schedule.uuid is not None
    assert schedule.schedule_value == "14:30"

    # Get by mapping
    all_schedules = service.get_schedules_by_mapping(mapping_obj.uuid)
    assert len(all_schedules) == 1
    assert all_schedules[0].uuid == schedule.uuid


def test_backup_schedules_new_types(db_session, setup_mapping):
    user_obj, mapping_obj = setup_mapping
    service = BackupSchedulesService()

    # Minute type
    min_dto = BackupSchedulesCreateDTO(
        user_uuid=user_obj.uuid,
        mapping_uuid=mapping_obj.uuid,
        schedule_type=ScheduleType.MINUTE,
        schedule_value="15",  # every 15 mins
        enabled=True,
    )
    min_sched = service.create(min_dto)
    assert min_sched.schedule_type == ScheduleType.MINUTE
    assert min_sched.schedule_value == "15"

    # Hourly type
    hour_dto = BackupSchedulesCreateDTO(
        user_uuid=user_obj.uuid,
        mapping_uuid=mapping_obj.uuid,
        schedule_type=ScheduleType.HOURLY,
        schedule_value="30",  # at :30 past
        enabled=True,
    )
    hour_sched = service.create(hour_dto)
    assert hour_sched.schedule_type == ScheduleType.HOURLY
    assert hour_sched.schedule_value == "30"

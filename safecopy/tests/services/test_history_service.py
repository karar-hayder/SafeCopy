import pytest

from safecopy.db.dtos.backupHistoryDTOs import BackupHistoryCreateDTO
from safecopy.db.dtos.mappingsDTOs import MappingsCreateDTO
from safecopy.db.dtos.userDTOs import UserCreateDTO
from safecopy.db.enums import BackupStatus, CompressionType, PasswdMode, UserRole
from safecopy.db.services.BackupHistoryService import BackupHistoryService
from safecopy.db.services.mappingsService import MappingsService
from safecopy.db.services.userService import UserService


@pytest.fixture
def setup_data(db_session):
    user_s = UserService()
    map_s = MappingsService()

    _ = user_s.register(
        UserCreateDTO(
            username="history_user",
            password="password123",
            role=UserRole.USER,
            settings={},
        )
    )
    u_obj = user_s.get_user_by_username("history_user")

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


def test_backup_history_crud(db_session, setup_data):
    user_obj, mapping_obj = setup_data
    service = BackupHistoryService()

    create_dto = BackupHistoryCreateDTO(
        user_uuid=user_obj.uuid,
        mapping_uuid=mapping_obj.uuid,
        status=BackupStatus.SUCCESS,
        message="Total success",
        duration=10.5,
        size_bytes=1024,
        backup_path="/backups/b1.zip",
    )

    history = service.create(create_dto)
    assert history.uuid is not None
    assert history.status == BackupStatus.SUCCESS

    # Retrieve by mapping
    results = service.get_by_mapping_uuid(mapping_obj.uuid)
    assert results.uuid == history.uuid

    # Retrieve all
    all_history = service.get_all(mapping_uuid=mapping_obj.uuid)
    assert len(all_history) == 1
    assert all_history[0].uuid == history.uuid

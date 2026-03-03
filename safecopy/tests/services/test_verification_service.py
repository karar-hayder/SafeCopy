from datetime import datetime

import pytest

from safecopy.db.dtos.backupHistoryDTOs import BackupHistoryCreateDTO
from safecopy.db.dtos.backupVerificationDTOs import BackupVerificationCreateDTO
from safecopy.db.dtos.mappingsDTOs import MappingsCreateDTO
from safecopy.db.dtos.userDTOs import UserCreateDTO
from safecopy.db.enums import (
    BackupStatus,
    BackupVerificationStatus,
    CompressionType,
    HashType,
    PasswdMode,
    UserRole,
)
from safecopy.db.services.backupHistoryService import BackupHistoryService
from safecopy.db.services.backupVerificationService import BackupVerificationService
from safecopy.db.services.mappingsService import MappingsService
from safecopy.db.services.userService import UserService


@pytest.fixture
def setup_history(db_session):
    user_s = UserService()
    map_s = MappingsService()
    hist_s = BackupHistoryService()

    user_s.register(
        UserCreateDTO(
            username="verif_user",
            password="password123",
            role=UserRole.USER,
            settings={},
        )
    )
    u_obj = user_s.get_user_by_username("verif_user")

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

    history = hist_s.create(
        BackupHistoryCreateDTO(
            user_uuid=u_obj.uuid,
            mapping_uuid=mapping.uuid,
            status=BackupStatus.SUCCESS,
            message="ok",
            duration=1.0,
            size_bytes=100,
            backup_path="/p",
        )
    )
    return history


def test_backup_verification_crud(db_session, setup_history):
    service = BackupVerificationService()

    create_dto = BackupVerificationCreateDTO(
        backup_history_uuid=setup_history.uuid,
        checksum_type=HashType.MD5,
        source_checksum="abc",
        backup_checksum="abc",
        verification_status=BackupVerificationStatus.SUCCESS,
        verified_at=datetime.now(),
        verification_msg="Checksum matches",
    )

    verification = service.create(create_dto)
    assert verification.uuid is not None

    # Get by history
    results = service.get_verifications_by_history(setup_history.uuid)
    assert len(results) == 1
    assert results[0].uuid == verification.uuid

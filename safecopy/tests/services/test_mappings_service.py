import pytest

from safecopy.db.dtos.mappingsDTOs import MappingsCreateDTO
from safecopy.db.dtos.userDTOs import UserCreateDTO
from safecopy.db.enums import CompressionType, PasswdMode, UserRole
from safecopy.db.services.mappingsService import MappingsService
from safecopy.db.services.userService import UserService


@pytest.fixture
def test_user(db_session):
    user_service = UserService()
    user_dto = UserCreateDTO(
        username="mapper", password="password123", role=UserRole.USER, settings={}
    )
    user_service.register(user_dto)
    return user_service.get_user_by_username("mapper")


def test_mappings_crud(db_session, test_user):
    service = MappingsService()

    create_dto = MappingsCreateDTO(
        user_uuid=test_user.uuid,
        source="/src",
        destination="/dst",
        max_versions=5,
        compression=CompressionType.NONE,
        enabled=True,
        encrypted=False,
        passwd_mode=PasswdMode.NONE,
    )

    # Create
    mapping = service.create(create_dto)
    assert mapping.uuid is not None
    assert mapping.source == "/src"

    # Read
    retrieved = service.get_by_uuid(mapping.uuid)
    assert retrieved.source == "/src"

    # Get by source and destination
    found = service.get_by_source_and_destination("/src", "/dst")
    assert found.uuid == mapping.uuid

    # Delete
    assert service.delete(mapping.uuid) is True
    assert service.get_by_uuid(mapping.uuid) is None

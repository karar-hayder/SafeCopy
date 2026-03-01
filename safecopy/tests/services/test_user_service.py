from safecopy.db.dtos.userDTOs import UserCreateDTO, UserLoginDTO, UserUpdateDTO
from safecopy.db.enums import UserRole
from safecopy.db.services.userService import UserService


def test_user_registration_and_login(db_session):
    service = UserService()

    create_dto = UserCreateDTO(
        username="testuser", password="password123", role=UserRole.USER, settings={}
    )

    # Register
    assert service.register(create_dto) is True

    # Login success
    login_dto = UserLoginDTO(username="testuser", password="password123")
    assert service.login(login_dto) is True

    # Login failure
    bad_login = UserLoginDTO(username="testuser", password="wrongpassword")
    assert service.login(bad_login) is False


def test_user_change_password(db_session):
    service = UserService()
    create_dto = UserCreateDTO(
        username="pwuser", password="oldpassword", role=UserRole.USER, settings={}
    )
    service.register(create_dto)

    update_dto = UserUpdateDTO(
        username="pwuser", password="newpassword", role=UserRole.USER, settings={}
    )
    assert service.change_password(update_dto) is True

    # Login with new password
    assert (
        service.login(UserLoginDTO(username="pwuser", password="newpassword")) is True
    )
    assert (
        service.login(UserLoginDTO(username="pwuser", password="oldpassword")) is False
    )


def test_get_user_by_username(db_session):
    service = UserService()
    create_dto = UserCreateDTO(
        username="findme",
        password="password123",
        role=UserRole.USER,
        settings={"theme": "dark"},
    )
    service.register(create_dto)

    user = service.get_user_by_username("findme")
    assert user is not None
    assert user.username == "findme"
    assert user.settings["theme"] == "dark"
    assert (
        hasattr(user, "password") is False or user.password is None
    )  # Ensure DTO doesn't expose password

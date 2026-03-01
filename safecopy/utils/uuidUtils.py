import uuid


def is_valid_uuid(uuid_str: str) -> bool:
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def is_valid_uuid_list(uuid_list: list[str]) -> bool:
    return all(is_valid_uuid(uuid_str) for uuid_str in uuid_list)

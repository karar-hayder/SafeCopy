from enum import Enum


class CompressionType(str, Enum):
    ZIP = "zip"
    TAR = "tar"
    NONE = "none"


class PasswdMode(str, Enum):
    NONE = "none"
    PASSWORD = "password"
    SYSTEM = "system"


class ScheduleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ScheduleIntervalType(str, Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class BackupStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    CANCELLED = "cancelled"


class BackupVerificationStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    NOT_VERIFIED = "not_verified"
    IN_PROGRESS = "in_progress"


class HashType(str, Enum):
    MD5 = "md5"
    # SHA1 = "sha1"
    # SHA256 = "sha256"
    # SHA512 = "sha512"


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import (
    BackupStatus,
    BackupVerificationStatus,
    CompressionType,
    HashType,
    PasswdMode,
    ScheduleIntervalType,
    ScheduleType,
    UserRole,
)


class Mappings(Base):
    __tablename__ = "mappings"

    user_uuid: Mapped[str] = mapped_column(ForeignKey("user.uuid"))
    source: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    max_versions: Mapped[int] = mapped_column(Integer, default=3)
    compression: Mapped[CompressionType] = mapped_column(
        Enum(CompressionType), default=CompressionType.NONE
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    passwd_mode: Mapped[PasswdMode] = mapped_column(
        Enum(PasswdMode), default=PasswdMode.NONE
    )
    backup_history: Mapped[list["BackupHistory"]] = relationship(
        "BackupHistory", back_populates="mapping"
    )


class BackupHistory(Base):
    __tablename__ = "backup_history"

    user_uuid: Mapped[str] = mapped_column(ForeignKey("user.uuid"))
    mapping_uuid: Mapped[str] = mapped_column(ForeignKey("mappings.uuid"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[BackupStatus] = mapped_column(
        Enum(BackupStatus), nullable=False, default=BackupStatus.PENDING
    )
    message: Mapped[str] = mapped_column(String)
    duration: Mapped[float] = mapped_column(Float)
    size_bytes: Mapped[int] = mapped_column(Integer)
    backup_path: Mapped[str] = mapped_column(String)
    mapping: Mapped["Mappings"] = relationship(
        "Mappings", back_populates="backup_history"
    )


class BackupSchedules(Base):
    __tablename__ = "backup_schedules"

    user_uuid: Mapped[str] = mapped_column(ForeignKey("user.uuid"))
    mapping_uuid: Mapped[str] = mapped_column(ForeignKey("mappings.uuid"))
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), nullable=False
    )
    schedule_interval: Mapped[int] = mapped_column(Integer, nullable=True)
    schedule_interval_type: Mapped[ScheduleIntervalType] = mapped_column(
        Enum(ScheduleIntervalType), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class BackupVerification(Base):
    __tablename__ = "backup_verification"

    backup_history_uuid: Mapped[str] = mapped_column(ForeignKey("backup_history.uuid"))
    checksum_type: Mapped[HashType] = mapped_column(String, default=HashType.MD5)
    source_checksum: Mapped[str] = mapped_column(String)
    backup_checksum: Mapped[str] = mapped_column(String)
    verification_status: Mapped[BackupVerificationStatus] = mapped_column(
        Enum(BackupVerificationStatus), default=BackupVerificationStatus.NOT_VERIFIED
    )
    verified_at: Mapped[datetime] = mapped_column(DateTime)
    verification_msg: Mapped[str] = mapped_column(String)


class User(Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default={})

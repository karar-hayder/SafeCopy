from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Mappings(Base):
    __tablename__ = "mappings"

    source: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    max_versions: Mapped[int] = mapped_column(Integer, default=3)
    compression: Mapped[str] = mapped_column(String, default="none")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    encrypted: Mapped[int] = mapped_column(Integer, default=0)
    passwd_mode: Mapped[str] = mapped_column(String, default="none")
    backup_history: Mapped[list["BackupHistory"]] = relationship(
        "BackupHistory", back_populates="mapping"
    )


class BackupHistory(Base):
    __tablename__ = "backup_history"

    mapping_uuid: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    success: Mapped[int] = mapped_column(Integer, default=1)
    message: Mapped[str] = mapped_column(String)
    duration: Mapped[float] = mapped_column(Float)
    size_bytes: Mapped[int] = mapped_column(Integer)
    backup_path: Mapped[str] = mapped_column(String)
    mapping: Mapped["Mappings"] = relationship(
        "Mappings", back_populates="backup_history"
    )


class BackupSchedules(Base):
    __tablename__ = "backup_schedules"

    mapping_uuid: Mapped[str] = mapped_column(String, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String, nullable=False)
    schedule_value: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class EmailSettings(Base):
    __tablename__ = "email_settings"

    smtp_server: Mapped[str] = mapped_column(String, nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    smtp_username: Mapped[str] = mapped_column(String)
    smtp_password: Mapped[str] = mapped_column(String)
    from_email: Mapped[str] = mapped_column(String, nullable=False)
    to_email: Mapped[str] = mapped_column(String, nullable=False)
    use_tls: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[int] = mapped_column(Integer, default=0)


class BackupVerification(Base):
    __tablename__ = "backup_verification"

    backup_history_uuid: Mapped[str] = mapped_column(String, nullable=False)
    checksum_type: Mapped[str] = mapped_column(String, default="md5")
    source_checksum: Mapped[str] = mapped_column(String)
    backup_checksum: Mapped[str] = mapped_column(String)
    verification_status: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[datetime] = mapped_column(DateTime)
    verification_msg: Mapped[str] = mapped_column(String)


class WebAuth(Base):
    __tablename__ = "web_auth"

    username: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user")


class BackupSettings(Base):
    __tablename__ = "backup_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)

from typing import List, Optional

from safecopy.db.models import BackupSchedules
from safecopy.db.repos.backupSchedulesRepo import BackupSchedulesRepo
from safecopy.db.session import get_session


class BackupSchedulesService:
    def create_schedule(self, **kwargs) -> BackupSchedules:
        with get_session() as session:
            schedule = BackupSchedules(**kwargs)
            session.add(schedule)
            session.flush()
            return schedule

    def get_all_schedules(self) -> List[BackupSchedules]:
        with get_session() as session:
            repo = BackupSchedulesRepo(session)
            return repo.get_all()

    def get_schedule(self, uuid: str) -> Optional[BackupSchedules]:
        with get_session() as session:
            repo = BackupSchedulesRepo(session)
            return repo.get_by_uuid(uuid)

    def get_schedules_by_mapping(self, mapping_uuid: str) -> List[BackupSchedules]:
        with get_session() as session:
            repo = BackupSchedulesRepo(session)
            return repo.get_by_mapping_uuid(mapping_uuid)

    def update_schedule(self, uuid: str, **kwargs) -> Optional[BackupSchedules]:
        with get_session() as session:
            repo = BackupSchedulesRepo(session)
            schedule = repo.get_by_uuid(uuid)
            if schedule:
                for key, value in kwargs.items():
                    if hasattr(schedule, key):
                        setattr(schedule, key, value)
                return schedule
            return None

    def delete_schedule(self, uuid: str) -> bool:
        with get_session() as session:
            repo = BackupSchedulesRepo(session)
            schedule = repo.get_by_uuid(uuid)
            if schedule:
                session.delete(schedule)
                return True
            return False

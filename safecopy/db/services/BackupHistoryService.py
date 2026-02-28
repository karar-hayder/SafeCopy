from typing import List, Optional

from safecopy.db.models import BackupHistory
from safecopy.db.repos.backupHistoryRepo import BackupHistoryRepo
from safecopy.db.session import get_session


class BackupHistoryService:
    def create_backup_history(self, **kwargs):
        with get_session() as session:
            backup_history = BackupHistory(**kwargs)
            session.add(backup_history)
            session.flush()
            return backup_history

    def get_all_backup_histories(self) -> List[BackupHistory]:
        with get_session() as session:
            repo = BackupHistoryRepo(session)
            return repo.get_all()

    def get_backup_history(self, uuid: str) -> Optional[BackupHistory]:
        with get_session() as session:
            repo = BackupHistoryRepo(session)
            return repo.get_by_uuid(uuid)

    def update_backup_history(self, uuid: str, **kwargs):
        with get_session() as session:
            repo = BackupHistoryRepo(session)
            backup_history = repo.get_by_uuid(uuid)
            if backup_history:
                for key, value in kwargs.items():
                    setattr(backup_history, key, value)
                session.flush()
            return backup_history

    def delete_backup_history(self, uuid: str):
        with get_session() as session:
            repo = BackupHistoryRepo(session)
            backup_history = repo.get_by_uuid(uuid)
            if backup_history:
                session.delete(backup_history)
                session.flush()
            return True

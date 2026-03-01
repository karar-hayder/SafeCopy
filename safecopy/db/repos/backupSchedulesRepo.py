from safecopy.db.models import BackupSchedules
from safecopy.db.repos.baseRepo import BaseRepo


class BackupSchedulesRepo(BaseRepo):
    def __init__(self, session, model=BackupSchedules):
        super().__init__(session, model)

from safecopy.db.models import Mappings
from safecopy.db.repos.baseRepo import BaseRepo


class MappingsRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session, Mappings)

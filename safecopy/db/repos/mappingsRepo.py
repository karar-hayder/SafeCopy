from safecopy.db.models import Mappings
from safecopy.db.repos.baseRepo import BaseRepo


class MappingsRepo(BaseRepo):
    def __init__(self, session, model=Mappings):
        super().__init__(session, model)

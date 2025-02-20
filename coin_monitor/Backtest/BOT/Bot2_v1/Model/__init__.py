from django.db.backends.base.base import BaseDatabaseWrapper

def _cursor(self, name=None):
    if(self.connection and not self.is_usable()):
        self.close()
    if(hasattr(self, 'close_if_health_check_failed')): self.close_if_health_check_failed()
    self.ensure_connection()
    with self.wrap_database_errors:
        return self._prepare_cursor(self.create_cursor(name))
BaseDatabaseWrapper._cursor = _cursor 

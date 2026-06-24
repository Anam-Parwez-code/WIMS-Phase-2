from threading import local
from django.conf import settings
from django.db import connections

_thread_locals = local()

def set_client_db(db_key):
    _thread_locals.DB_KEY = db_key

def get_client_db():
    return getattr(_thread_locals, "DB_KEY", None)

class ClientDBRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label in settings.TENANT_APPS:
            return get_client_db() or "default"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in settings.TENANT_APPS:
            return get_client_db() or "default"
        return "default"

    
    def allow_relation(self, obj1, obj2, **hints):
        # 1. Allow if they are in the same database
        if obj1._state.db == obj2._state.db:
            return True
        
        # 2. Fix the ValueError: Allow relations for auth and contenttypes 
        # because they are shared/synced across databases
        allowed_apps = ['auth', 'contenttypes']
        if obj1._meta.app_label in allowed_apps or obj2._meta.app_label in allowed_apps:
            return True

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):

        # Tenant apps go ONLY to tenant DBs
        if app_label in settings.TENANT_APPS:
            return db != "default"

        # Shared apps go ONLY to default DB
        if app_label in settings.SHARED_APPS:
            return db == "default"

        return None
        
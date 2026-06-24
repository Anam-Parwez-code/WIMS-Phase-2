from django.conf import settings
from django.db import connections
from django.core.management import call_command

def create_tenant_database(database_name: str):
    db_name = database_name.lower()

    admin_conn = connections["default"]
    admin_conn.ensure_connection()

    with admin_conn.cursor() as cursor:
        cursor.execute(f'CREATE DATABASE "{db_name}" OWNER wims_user;')

    return db_name


def migrate_tenant_database(db_name: str):
    settings.DATABASES[db_name] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_name,
        "USER": "wims_user",
        "PASSWORD": "wims_pass",
        "HOST": "localhost",
        "PORT": "5432",
    }

    call_command(
        "migrate",
        database=db_name,
        app_label=None,
        verbosity=1,
        interactive=False,
    )

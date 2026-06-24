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

def migrate_tenant_database(tenant_db_name):
    """
    Dynamically configures the connection using settings.py parameters
    and runs migrations for a specific tenant database.
    """
    # 1. Pull the base configuration from settings.py
    base_config = settings.DATABASES['default'].copy()
    
    # 2. Update only the database name for this specific tenant
    base_config['NAME'] = tenant_db_name
    
    # 3. Inject this configuration into Django's connection handler temporarily
    connections.databases[tenant_db_name] = base_config
    
    try:
        print(f"Starting dynamic migration for: {tenant_db_name}")
        # 4. Run the migration pointing to our new dynamic key
        call_command('migrate', database=tenant_db_name, interactive=False)
        print(f"Successfully migrated {tenant_db_name}")
    except Exception as e:
        print(f"Migration failed for {tenant_db_name}: {str(e)}")
        raise e
    finally:
        # 5. Clean up the temporary connection to prevent memory leaks
        if tenant_db_name in connections.databases:
            del connections.databases[tenant_db_name]


# def migrate_tenant_database(db_name: str):
#     settings.DATABASES[db_name] = {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": db_name,
#         "USER": "wims_user",
#         "PASSWORD": "wims_pass",
#         "HOST": "localhost",
#         "PORT": "5432",
#     }
# 
#     call_command(
#         "migrate",
#         database=db_name,
#         app_label=None,
#         verbosity=1,
#         interactive=False,
#     )

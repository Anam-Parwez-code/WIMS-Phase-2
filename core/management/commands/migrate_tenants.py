from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connections
from psycopg2 import OperationalError
from core.models import Client
from core.dbrouter import set_client_db

class Command(BaseCommand):
    help = 'Run migrations for all client databases'

    def add_arguments(self, parser):
        parser.add_argument("client_code", nargs="?", type=str, help="Run for a specific client only")

    def handle(self, *args, **options):
        tenant_apps = getattr(settings, "TENANT_APPS", [])
        client_qs = Client.objects.filter(is_active=True)

        # Optional: limit to one client if code passed
        if options["client_code"]:
            client_qs = client_qs.filter(client_code=options["client_code"])

        for client in client_qs:
            db_key = f"tenant_{client.client_code}"

            # Inject DB config
            if db_key not in settings.DATABASES:
                settings.DATABASES[db_key] = {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": client.database_name,
                    "USER": client.db_user,
                    "PASSWORD": client.db_password,
                    "HOST": client.db_host,
                    "PORT": client.db_port,
                }

            # Test DB connection
            try:
                connections[db_key].ensure_connection()
            except OperationalError:
                self.stdout.write(
                    self.style.ERROR(f"❌ Database {client.database_name} does not exist. Please create it first.")
                )
                continue

            self.stdout.write(self.style.SUCCESS(f"Running migrations for {db_key}..."))
            set_client_db(db_key)

            try:
                # Run migrations for tenant apps
                for app in tenant_apps:
                    self.stdout.write(self.style.SUCCESS(f'Applying migrations for {app} on {db_key}...'))
                    call_command('migrate', app, database=db_key)
            finally:
                set_client_db(None)

            self.stdout.write(self.style.SUCCESS(f"Migrations complete for {db_key}"))

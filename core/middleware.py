from django.utils.deprecation import MiddlewareMixin
from django.db import connections
from core.models import Client
from core.dbrouter import set_client_db
import jwt
from django.conf import settings
from django.http import JsonResponse


class ClientMiddleware(MiddlewareMixin):


    def process_request(self, request):

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header.startswith("Bearer "):
            set_client_db(None)
            return

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            client_code = payload.get("client_code")
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except Exception:
            set_client_db(None)
            return

        if not client_code:
            set_client_db(None)
            return
        
        try:
            client = Client.objects.get(client_code=client_code, is_active=True)
        except Client.DoesNotExist:
            set_client_db(None)
            return

        db_key = f"client_{client.client_code}"
        print("DB Key:", db_key)
        if db_key not in connections.databases:
            connections.databases[db_key] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': client.database_name,
                'USER': client.db_user,
                'PASSWORD': client.db_password,
                'HOST': client.db_host,
                'PORT': client.db_port,
            }

        set_client_db(db_key)
        from django.db import connection
        print("Current DB used:", connection.alias)


    def process_response(self, request, response):
        # Clean up thread-local after request is finished
        set_client_db(None)
        return response
    
    
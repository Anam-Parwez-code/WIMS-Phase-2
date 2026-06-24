from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    """
    Allows access only to super_admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "super_admin"
        )

import jwt
from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed

class HasClientSelectionToken(BasePermission):
    """
    Requires a valid client selection token from SelectClient API.
    """

    def has_permission(self, request, view):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed("Missing or invalid Authorization header")

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Client selection token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid client selection token")

        client_code = payload.get("client_code")
        if not client_code:
            raise AuthenticationFailed("Token missing client_code")

        # attach to request for serializer use
        request.client_code_from_token = client_code
        return True


class IsClientAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user and getattr(request.user, "role", None) == "client_admin"



class IsSuperAdminOrClientAdmin(BasePermission):
    """
    Allows access to both super_admin and client_admin.
    """

    def has_permission(self, request, view):
        role = getattr(request.user, "role", None)
        return request.user and request.user.is_authenticated and role in [
            "super_admin",
            "client_admin",
        ]
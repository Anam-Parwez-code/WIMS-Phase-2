


# users/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from .models import UserSession

User = get_user_model()


class SessionJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        """
        Override the base authenticate() to validate session_id against DB.
        """
        auth_tuple = super().authenticate(request)
        if auth_tuple is None:
            return None

        user, validated_token = auth_tuple

        # Get session_id from token payload
        session_id = validated_token.get("session_id")
        if not session_id:
            raise AuthenticationFailed("Session ID missing in token")

        # Check session in DB
        if not UserSession.objects.filter(session_id=session_id, is_active=True).exists():
            raise AuthenticationFailed("Session has been logged out")

        return (user, validated_token)


class JWTWithSessionAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Override get_user to support both integer IDs and email-based tokens.
        """
        user_id = validated_token.get("user_id")
        if user_id is None:
            raise exceptions.AuthenticationFailed("Token contained no user_id claim")

        # Try integer lookup first
        try:
            return User.objects.get(id=int(user_id))
        except (ValueError, User.DoesNotExist):
            # If it wasn't an int or not found, try email
            try:
                return User.objects.get(email=user_id)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed("User not found")

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        session_id = validated_token.get("session_id")
        if not session_id:
            raise exceptions.AuthenticationFailed("Session ID missing in token")

        if not UserSession.objects.filter(session_id=session_id, is_active=True).exists():
            raise exceptions.AuthenticationFailed("Session has been logged out")

        # ✅ return user and validated token
        return user, validated_token









from datetime import datetime, timezone
from rest_framework import serializers
from .models import User, UserSession
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import uuid
from django.conf import settings
from django.contrib.auth import authenticate

class SuperAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password", "role"]

    def create(self, validated_data):
        validated_data["role"] = "super_admin"  # enforce role
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=validated_data["role"],
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user, client=None):
        token = super().get_token(user)

        # Add custom claims
        token["role"] = user.role
        token["client_code"] = user.client_code

        # Add session_id
        token["session_id"] = str(uuid.uuid4())

        # Add login and expiry time
        login_time = datetime.now(timezone.utc)
        expiry_time = datetime.fromtimestamp(token["exp"], tz=timezone.utc)

        token["login_time"] = login_time.isoformat()
        token["expiry_time"] = expiry_time.isoformat()

        # 🔑 Only add client info if NOT super_admin
        if user.role != "super_admin" and user.client_code:
            from core.models import Client
            client = Client.objects.filter(client_code=user.client_code).first()
            if client:
                token["client_id"] = str(client.id)
                token["client_name"] = client.client_name
                token["client_code"] = client.client_code
                token["database_name"] = client.database_name
                token["expiry_date"] = (
                    client.expiry_date.isoformat() if client.expiry_date else None
                )
                token["client_logo"] = client.client_logo
                token["is_active"] = client.is_active
                token["user_type"] = client.user_type

        return token

    def validate(self, attrs):
        # ✅ Step 1: Authenticate user
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        user = authenticate(**authenticate_kwargs)

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # ✅ Step 2: Check client selection (only for non-superadmin)
        request = self.context.get("request")
        selected_client = request.session.get("client_code") if request else None

        if not selected_client and user.role != "super_admin":
            raise serializers.ValidationError("Please select a client before login.")

        # ✅ Step 3: Run normal JWT validation
        data = super().validate(attrs)

        # Generate token with user (not self.user!)
        token = self.get_token(user)
        access = token.access_token
        refresh = str(token)

        # ✅ Save session in DB
        from .models import UserSession
        UserSession.objects.create(
            user=user,
            session_id=token["session_id"],
            is_active=True
        )

        # ✅ Step 4: Build response
        data.update({
            "access": str(access),
            "refresh": refresh,
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "client_code": user.client_code,
            "session_id": token["session_id"],
            "login_time": token["login_time"],
            "expiry_time": token["expiry_time"],
        })

        # Add client fields only for non-super_admin
        if user.role != "super_admin":
            data.update({
                "client_id": token.get("client_id"),
                "client_name": token.get("client_name"),
                "client_code": token.get("client_code"),
                "database_name": token.get("database_name"),
                "expiry_date": token.get("expiry_date"),
                "client_logo": token.get("client_logo"),
                "is_active": token.get("is_active"),
                "user_type": token.get("user_type"),
            })

        return data
    




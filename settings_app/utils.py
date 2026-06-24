from django.db import transaction
from .models import CodePrefix

from django.apps import apps
from django.conf import settings
from users.models import User

def get_tenant_modules_and_forms():
    data = {}

    for app_config in apps.get_app_configs():
        # Only tenant apps
        if app_config.label not in settings.TENANT_APPS:
            continue

        models = []
        for model in app_config.get_models():
            models.append(model.__name__)

        if models:
            data[app_config.label] = models

    return data

@transaction.atomic
def generate_code(module, form):
    prefix_obj = CodePrefix.objects.select_for_update().get(
        module__iexact=module,
        form__iexact=form,
        is_active=True
    )

    prefix_obj.current_number += 1
    prefix_obj.save()

    return f"{prefix_obj.prefix}{prefix_obj.current_number:05d}"


def send_sms_to_all_users():
    users = User.objects.all()
    for user in users:
        # send_sms(user.phone_number, "Hello")
        pass

    return f'send sms to all users successfully'
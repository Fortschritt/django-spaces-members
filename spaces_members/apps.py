from django.apps import AppConfig


class SpacesMembersConfig(AppConfig):
    name = 'spaces_members'

    def ready(self):
        # activate activity streams for 
        from actstream import registry
        from django.contrib.auth import get_user_model
        User = get_user_model()
        registry.register(User)

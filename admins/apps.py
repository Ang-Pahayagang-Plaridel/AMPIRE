from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AdminsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admins'

    def ready(self):

        from decouple import config
        from django.contrib.auth.hashers import make_password
        from django.contrib.auth.models import User

        from .models import Section

        def create_initial_users(sender, **kwargs):
            if not User.objects.exists():
                User.objects.create(
                    password=make_password(config('SUPER_USER_PASSWORD')),
                    is_superuser=True,
                    username=config('SUPER_USER_USERNAME'),
                    first_name='Jonathan',
                    last_name='Lin',
                    email='lj021803@gmail.com',
                    is_staff=True,
                    is_active=True,
                )
                User.objects.create(
                    password=make_password(config('APP_USER_PASSWORD')),
                    is_superuser=False,
                    username=config('APP_USER_USERNAME'),
                    first_name='',
                    last_name='',
                    email='app@dlsu.edu.ph',
                    is_staff=False,
                    is_active=True,
                )
        def create_initial_sections(sender, **kwargs):
            if not Section.objects.exists():
                Section.objects.create(
                    name='Balita',
                    full_name='Balita',
                    section_color='#6aa84f',
                )
                Section.objects.create(
                    name='Isports',
                    full_name='Isports',
                    section_color='#674ea7',
                )
                Section.objects.create(
                    name='Bayan',
                    full_name='Bayan',
                    section_color='#999999',
                )
                Section.objects.create(
                    name='BNK',
                    full_name='Buhay at Kultura',
                    section_color='#c17aa0',
                )
                Section.objects.create(
                    name='Retrato',
                    full_name='Retrato',
                    section_color='#3c78d8',
                )
                Section.objects.create(
                    name='Sining',
                    full_name='Sining',
                    section_color='#ffd966',
                )
                Section.objects.create(
                    name='IT',
                    full_name='Impormasyong Panteknolohiya',
                    section_color='#ff9900',
                )
        post_migrate.connect(create_initial_users)
        post_migrate.connect(create_initial_sections)
        
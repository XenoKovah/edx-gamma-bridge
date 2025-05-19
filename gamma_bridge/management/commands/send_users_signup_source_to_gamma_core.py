import json
import requests

from urllib.parse import urljoin
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Management command that sends users signup source to Gamma Core for updating the game profile.

    The command accepts options to filter users by site (tenant-name)
    and to set the number of users to send in one package (chunk-size).
    For each user that meets the filter criteria, a data package containing
    their username and signup source is generated. Data packages are sent
    to Gamma Core in chunks of size chunk-size until all users have been
    processed. The command also checks if gamification is enabled on the site,
    and if yes, sends data according to the configuration in the settings file.
    
    Data structure:
        {
            "tenant": "site.com",
            "uids": [
                "username1",
                "username2",
                "username3",
                ...
            ]
        }

    Example usage:
        # define the `--tenant-name` for the update of the specific microsite
        python manage.py lms send_users_signup_source_to_gamma_core --tenant-name=RG --chunk-size=50
        # don't use the `--tenant-name` to update users' profiles for the main site
        python manage.py lms send_users_signup_source_to_gamma_core

    """
    MAIN_SITE_NAME = 'main'
    help = 'Send users\' data to Gamma Core for the profiles\' signup_source update.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-name',
            dest='tenant-name',
            default=None,
            help='Site to filter users by (default: None)'
        )
        parser.add_argument(
            '--chunk-size',
            dest='chunk-size',
            type=int,
            default=100,
            help='Number of users to send in one package (default: 100)'
        )

    def handle(self, *args, **options):
        tenant_name = options['tenant-name']
        chunk_size = options['chunk-size']

        uids = User.objects.filter(usersignupsource__site=tenant_name).values_list('username', flat=True)
        tenant = tenant_name if tenant_name else self.MAIN_SITE_NAME

        count = len(uids)
        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                f'The signup_source "{tenant}" has no users for update.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Processing {count} users for signup_source "{tenant}"...'))

        # Send users in packages to Gamma Core
        current_index = 0
        while current_index < count:
            package = {
                'uids': uids[current_index:current_index+chunk_size],
                'tenant': tenant
            }
            if response := self._send_users_data(package):
                if response.status_code == 200:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated {response.json().get("count")} game profiles in Gamma Core.'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to send users to Gamma Core. Response code: {response.status_code}'
                        )
                    )
                    break
            # This case occurs when trying to execute management command without Gamma Core enabled.
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to send users to Gamma Core. Gamification is not enabled.'
                    )
                )
                break

            current_index += chunk_size

    def _send_users_data(self, data):
        """
        Send the users signup source to Gamma Core.
        """
        GAMIFICATION_CONF = settings.FEATURES.get('RG_GAMIFICATION', {})

        enabled=GAMIFICATION_CONF.get('ENABLED'),
        endpoint=GAMIFICATION_CONF.get('RG_GAMIFICATION_ENDPOINT')
        secret=GAMIFICATION_CONF.get('SECRET')
        key=GAMIFICATION_CONF.get('KEY')
        response = None
        headers = {
            'App-key': key,
            'App-secret': secret
        }

        if all((enabled, endpoint, key, secret)):
            suffix = settings.GAMMA_API_UPDATE_USERS_DATA_SUFFIX
            response = requests.post(
                urljoin(endpoint, suffix),
                json=data,
                headers=headers,
                verify=False
            )

        return response

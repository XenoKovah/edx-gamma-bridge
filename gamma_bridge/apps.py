from django.apps import AppConfig
from openedx.core.djangoapps.plugins.constants import (
    ProjectType, SettingsType, PluginURLs, PluginSettings
)
from openedx.core.release import RELEASE_LINE


class GamificationTrackingConfig(AppConfig):
    name = 'gamma_bridge'
    verbose_name = "RaccoonGang Gamification Tracking"

    SETTINGS_CONF_TYPE = SettingsType.AWS if RELEASE_LINE == 'hawthorn' else SettingsType.PRODUCTION

    # Class attribute that configures and enables this app as a Plugin App.
    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: 'gamma_bridge',
                PluginURLs.APP_NAME: 'gamma_bridge',
                PluginURLs.REGEX: '^gamma_bridge/api/',
                PluginURLs.RELATIVE_PATH: 'api.urls',
            }
        },

        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SETTINGS_CONF_TYPE: {
                    PluginSettings.RELATIVE_PATH: 'settings',
                },
            }
        },
    }

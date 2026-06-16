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
                SETTINGS_CONF_TYPE: {  # aws is used because we need variables from lms.env.json
                    PluginSettings.RELATIVE_PATH: 'settings.production',
                },
                SettingsType.DEVSTACK: {
                    PluginSettings.RELATIVE_PATH: 'settings.devstack',
                }
            }
        },
    }

    def ready(self):
        """Connect the BlockCompletion -> rgg.block.completed emitter (LMS only)."""
        super().ready()
        try:
            from django.db.models.signals import post_save
            from completion.models import BlockCompletion

            from gamma_bridge.handlers import emit_block_completion
            post_save.connect(
                emit_block_completion,
                sender=BlockCompletion,
                dispatch_uid='gamma_bridge.emit_block_completion',
            )
        except Exception:  # completion app not installed (e.g. CMS / tests) -> no-op
            pass

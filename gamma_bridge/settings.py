"""
Settings for RG Gamification tracking app known as GAMMA.
"""

GAMMA_API_VERSION = 'v0'

RG_GAMIFICATION_TRACKING_PROCESSOR = 'gamma_bridge.processor.GamificationProcessor'

RG_GAMIFICATION_TRACKING_BACKENDS = {
    'logger': {
        'ENGINE': RG_GAMIFICATION_TRACKING_PROCESSOR,
        'OPTIONS': {
            'name': 'tracking'
        }
    }
}

GAMMA_API_SUFFIX = '/api/{}/gamma-profile/'.format(GAMMA_API_VERSION)


def plugin_settings(settings):
    GAMIFICATION_CONF = settings.FEATURES.get('RG_GAMIFICATION', {})
    settings.GAMMA_FIRST_SLEEP_INTERVAL = GAMIFICATION_CONF.get('GAMMA_FIRST_SLEEP_INTERVAL', 2)
    settings.GAMMA_CELERY_MAX_RETRIES = GAMIFICATION_CONF.get('GAMMA_CELERY_MAX_RETRIES', 10)

    if (GAMIFICATION_CONF and GAMIFICATION_CONF.get('ENABLED') == True and
        GAMIFICATION_CONF.get('RG_GAMIFICATION_ENDPOINT')):
        """
        Add GamificationProcessor to event tracking backends list.
        """
        if hasattr(settings, 'EVENT_TRACKING_BACKENDS'):
            settings.EVENT_TRACKING_BACKENDS['tracking_logs']['OPTIONS']['processors'] += [
                {'ENGINE': RG_GAMIFICATION_TRACKING_PROCESSOR}
            ]

        if hasattr(settings, 'TRACKING_BACKENDS'):
            settings.TRACKING_BACKENDS['gamma_bridge'] = {'ENGINE': RG_GAMIFICATION_TRACKING_PROCESSOR}

RG Gamification Tracking
=========================

Parse the edX tracking log, convert the events to Gamma format, and publish them to an RG Gamification storage known Gamma.


# Configuration

Add the following configuration to the lms settings:

```python
FEATURES.update({
    "RG_GAMIFICATION": {
        "ENABLED": True,
        "RG_GAMIFICATION_ENDPOINT": "https://gamma.domain.in/",
        "KEY": "key",
        "SECRET": "secret",
        "IGNORED_EVENT_TYPES": []
    }
})
```

# OneSignal SDK
Since version 0.0.8, OneSignal SDK is added.

If platform is run with devstack settings, OneSignal service workers could be
accessed form urls '<LMS_ROOT>/gamma_bridge/api/OneSignalSDKWorker.js' and
'<LMS_ROOT>/gamma_bridge/api/OneSignalSDKUpdaterWorker.js'
Header 'service-worker-allowed: /' for OneSignal workers that are not accessible
from site root will be auto-added. Details at https://documentation.onesignal.com/docs/onesignal-service-worker-faq#method-1-add-an-additional-http-header.


If platform is run with production settings, OneSignal service workers could be
accessed form urls '<LMS_ROOT>/<STATIC_ROOT>/OneSignalSDKWorker.js' and
'<LMS_ROOT>/<STATIC_ROOT>/api/OneSignalSDKUpdaterWorker.js'. It should become
accessible from site root or got header 'service-worker-allowed: /' with static
server options.
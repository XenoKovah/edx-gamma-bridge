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

To get the values for KEY and SECRET settings, you need:
1. open a terminal window, change directory to the **gamma app** location, type `make shell`. 
Type `python manage.py createsuperuser` in the shell and provide credentials you will use when log in.
2. log in gamma, add new app client with an arbitrary name on the admin panel. The key and secret are generated 
automatically.

### For local installation:

If you deploy gamma bridge locally, you need to complete the FEATURES settings in the /edx/etc/lms.yml configuration 
file inside the lms container. So, this file should contain the section like the following one:

```yml
FEATURES:
    ...
    RG_GAMIFICATION:
        ENABLED: true
        RG_GAMIFICATION_ENDPOINT: http://<LOCAL_IP_ADDRESS>:9000/
        KEY: key
        SECRET: secret
        IGNORED_EVENT_TYPES: []
```

IP address in the RG_GAMIFICATION_ENDPOINT setting must be your private IP address. You can find how to get your private 
IP here: https://www.avg.com/en/signal/find-ip-address. For example, the value may be http://192.168.140.191:9000/.  
Note that the private ip can be changed because it is issued by a router, so it will be necessary to change this setting 
in the future.

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
# Changelog

## 1.0.1 (2021-05-21)
- Add daily learning event
- Add completion event
- Upgrade to Koa and Juniper releases

## 0.0.10 (2020-07-07)
- Change the log level for missing converter

## 0.0.9 (2020-06-23)
- Add static folder to a builded wheel

## 0.0.8 (2020-06-05)
- Add OneSignal SDK

## 0.0.7 (2020-04-15)
- Add API for courses/orgs lists
- Remove unnecessary events
- Handling events for forum actions, openassesment, student notes and bookmarks

## 0.0.6 (2020-03-06)
- Fix GammaStorage init params

## 0.0.5 (2020-03-03)
- Fix pypi packaging

## 0.0.4 (2020-02-28)

### Features
- Change gamma-bridge to work as edx plugin
- Add endpoint for getting events list

## 0.0.3 (2020-01-13)

### Features
- Add default UID strategy using SHA1 hexdigest

### Fixes
- Fix swapped key/secret for gamma api
- Fix uniqueness for events uid (#4)


## 0.0.2 (2019-12-06)

### Features
- Move Event posting logic to the Celery task.


## 0.0.1 (2019-08-29)

### Features
- Handling Video interaction events
- Handling Course related events (enrollment)
- Handling Problem related events (submissions, problem_check etc.)

### TODO
- Add dynamic analisis for different activities
 
   - Submission correctnes
   - Video fully played

- Add context not only in debug mode
- Add CI flow

## [Known issues]
- Lack of any tests
- There are no checks for problem submisions - any correctness anylysis

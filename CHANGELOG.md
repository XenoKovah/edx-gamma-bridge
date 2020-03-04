# Changelog

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
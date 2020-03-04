#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0111,W6005,W6100
from __future__ import absolute_import, print_function

import os
import re
import sys

from setuptools import setup, find_packages


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


VERSION = get_version('gamma_bridge', '__init__.py')

if sys.argv[-1] == 'tag':
    print("Tagging the version on github:")
    os.system("git tag -a %s -m 'version %s'" % (VERSION, VERSION))
    os.system("git push --tags")
    sys.exit()

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
# CHANGELOG = open(os.path.join(os.path.dirname(__file__), 'CHANGELOG.rst')).read()

setup(
    name='edx-gamma-bridge',
    version=VERSION,
    description="""Open-edx event tracking processos to handle and convert/save
    them as RG Gammification statements to an external Gamma service.""",
    long_description=README,
    author='Max K / RG',
    author_email='cmltaWt0@gmail.com',
    url='https://github.com/cmltaWt0/edx-gamma-bridge',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
    ],
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='Gamification gamma edx',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    entry_points={
        "lms.djangoapp": [
            "gamma_bridge = gamma_bridge.apps:GamificationTrackingConfig",
        ],
        "cms.djangoapp": [
        ],
    }
)

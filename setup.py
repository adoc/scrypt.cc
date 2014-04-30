

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = '' #open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'requests',
    'beautifulsoup4',
    'pytz'
    ]

setup(name='scryptcc',
      version='0.0.1',
      author='adoc',
      author_email='adoc@code.webmob.net',
      url='https://code.webmob.net/scryptcc'
      download_url='https://github.com/adoc',
      license='http://opensource.org/licenses/MIT',
      description='scrypt.cc Scraper/API Wrapper',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python :: 3.3",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: Pyramid",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English"
        ],
      keywords='scrypt.cc scrape api',
      packages=('scryptcc',),
      scripts=('bin/tracker.py',),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="tests",
      )
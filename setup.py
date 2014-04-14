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
      version='0.1',
      description='scrypt.cc Scrape API',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        ],
      author='adoc',
      author_email='adoc@code.webmob.net',
      url='https://github.com/adoc',
      keywords='scrypt.cc scrape api',
      packages=('scryptcc',),
      scripts=('bin/tracker.py',),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="tests",
      )
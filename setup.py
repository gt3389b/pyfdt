#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages, Command

class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys,subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)

def read_readme(fname):
   try:
      import pypandoc
      return pypandoc.convert('README.md','rst')
   except (IOError, ImportError):
      return ''

setup(
    name = "pyfdt",
    version = "1.0.0",
    url = '',
    download_url = '',
    license = 'Public',
    description = "Python library for flattened device trees",
    author = 'Russell Leake',
    author_email = 'leaker@cisco.com',
    py_modules = ['pyfdt'],
    tests_require=['pytest'],
    cmdclass={'test':PyTest},
    entry_points = {
       'console_scripts' : [
          'pyfdt = pyfdt:main'
         ]
       },
    long_description = read_readme('README.md'),
    include_package_data = True,
    zip_safe = False,
    install_requires = ['ordered-set' ],
    keywords = 'flattened device tree devicetree'
)

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
    name = "cisco_packaging",
    version = "1.0.1",
    url = '',
    download_url = '',
    license = 'Commercial',
    description = "Python library for build images",
    author = 'Russell Leake',
    author_email = 'leaker@cisco.com',
    #packages = find_packages('.', exclude=['tests']),
    py_modules = ['dt'],
    entry_points = {
       'console_scripts' : [
          'g_pack = cisco_packaging.g8:main'
          ]
       },
    tests_require=['pytest'],
    cmdclass={'test':PyTest},
    long_description = read_readme('README.md'),
    include_package_data = True,
    zip_safe = False,
    install_requires = ['python_cson>=1.0.7' ],
    keywords = 'cisco package pack packaging'
)

''' Setuptools Config for TAED API.
	'''
from setuptools import setup

setup(
    name='TAED',
    version='0.12',
    long_description=__doc__,
    packages=['TAED_API'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
		'flask_cors',
		'numpy',
		'jsonpickle',
		'biopython',
		'ruamel.yaml',
		'mysqlclient',
		'flask',
		'mod_wsgi',
		'requests'
	]
)

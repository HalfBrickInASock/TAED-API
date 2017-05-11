""" Fabric Installer File
	Used by fabric for remote deployment of project.
	"""
from fabric.api import env, local, put, run

# the user to use for the remote commands
env.user = 'fabdeploy'

# the servers where the commands are executed  #liberlesBox
env.hosts = ['127.0.0.1']

# previously created install and virtual env package paths.
WEB_PATH = '/usr/local/www/taed/'
PKG_PATH = '/usr/local/www/taed/pyenv/lib/python3.5/site-packages/TAED_API/'

def pack():
	""" Builds Fabric Package.
		"""

	# build the package
	local('python3 setup.py sdist --formats=gztar', capture=False)

def deploy():
	""" Deploys Fabric Package to remote server.
		Includes config file copy.
		"""
	# figure out the package name and version
	dist = local('python3 setup.py --fullname', capture=True).strip()
	filename = '%s.tar.gz' % dist

	# upload the package to the temporary folder on the server
	put('dist/%s' % filename, '/tmp/%s' % filename)

	# install the package in the application's virtualenv with pip
	run(WEB_PATH + 'pyenv/bin/pip3 install --upgrade /tmp/%s' % filename)

	# remove the uploaded package
	run('rm -r /tmp/%s' % filename)

	# copy the config file
	run('sudo cp ' + PKG_PATH + 'config.yaml ' + WEB_PATH + '.')

	# touch the .wsgi file to trigger a reload in mod_wsgi
	run('sudo touch /usr/local/www/taed/taed.wsgi')

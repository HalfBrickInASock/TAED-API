from fabric.api import *

# the user to use for the remote commands
env.user = 'dnorthover'

# the servers where the commands are executed  #liberlesBox
env.hosts = ['dolphin.cst.temple.edu']

def pack():
    # build the package
    local('python3 setup.py sdist --formats=gztar', capture=False)

def deploy():
    # figure out the package name and version
    dist = local('python3 setup.py --fullname', capture=True).strip()
    filename = '%s.tar.gz' % dist

    # upload the package to the temporary folder on the server
    put('dist/%s' % filename, '/tmp/%s' % filename)

    # install the package in the application's virtualenv with pip
    run('/usr/local/www/taed/env/bin/pip install /tmp/%s' % filename)

    # remove the uploaded package
    run('rm -r /tmp/%s' % filename)

    # touch the .wsgi file to trigger a reload in mod_wsgi
    run('touch /usr/local/www/taed/yourapplication.wsgi')
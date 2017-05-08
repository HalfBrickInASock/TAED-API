# Python3 and virtualenv should already be installed.
# Deployment using fabric?
# May need to add python3-venv / python3-pip if missing.

# First, create the virtual enviornment and install packages.
if [ ! -d "/usr/local/venvs" ]; then
	mkdir /usr/local/venvs
fi
/usr/bin/python3 -m venv /usr/local/venvs/taed
. /usr/local/venvs/taed/bin/activate
pip3 install --upgrade setuptools
pip3 install jsonpickle
pip3 install flask
pip3 install biopython
pip3 install ruamel.yaml
pip3 install mysqlclient
pip3 install requests
deactivate
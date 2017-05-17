# Python3 and virtualenv should already be installed.
# May need to add python3-venv / python3-pip if missing.

# First, create the virtual enviornment and install packages.
if [ ! -d "/usr/local/venvs" ]; then
	mkdir /usr/local/venvs
fi
echo "Enter Binary Path"
read binary

$binary/virtualenv -p $binary/python3 /usr/local/venvs/taed

. /usr/local/venvs/taed/bin/activate
pip install --upgrade setuptools
pip install numpy
pip install jsonpickle
pip install flask
pip install biopython
pip install ruamel.yaml
pip install mysqlclient
pip install requests
pip install fabric3
deactivate
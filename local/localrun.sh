# Runs API on flask locally.
# Ensure virtual environment is already setup (add-venv.sh)

# Flask Exporting
export FLASK_APP=TAED_API
export FLASK_DEBUG=true

. /usr/local/venvs/taed/bin/activate
pip install -e ..
cp TAED_API/config.yaml /usr/local/venvs/taed/.
cd /usr/local/venvs/taed
flask run
# Install into /usr/local/www
if [ ! -d "/usr/local/www" ]; thens
	mkdir /usr/local/www
fi
if [ ! -d "/usr/local/www/taed" ]; then
	mkdir /usr/local/www/taed
fi
/usr/bin/python3 -m venv /usr/local/www/taed/pyenv

cp -r apache_conf/taed.wsgi /usr/local/www/taed/.

# Setup the host conf file
read -p "Enter Hostname for Use" host
cp apache_conf/httpd.conf "/etc/apache2/sites-available/${host}.conf"
sed -i -e "s/vulpes/${host}/g" "/etc/apache2/sites-available/${host}.conf"

# Permissions
chown -R $USER:$USER /usr/local/www/taed/ 

# Restart Apache
service apache2 restart
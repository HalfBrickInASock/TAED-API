# Install into /usr/local/www
if [ ! -d "/usr/local/www" ]; then
	mkdir /usr/local/www
fi
if [ ! -d "/usr/local/www/taed" ]; then
	mkdir /usr/local/www/taed
fi
umask 002
virtualenv -p /usr/bin/python3 /usr/local/www/taed/pyenv

cp -r apache_conf/taed.wsgi /usr/local/www/taed/.
sudo chmod g+w /usr/local/www/taed/taed.wsgi

# Get hostname for site enable/disable/conf
echo "Enter Hostname for Use"
read host

# Disable existing sites
sudo a2dissite ${host}.taed

# Setup the host conf file
cp apache_conf/httpd.conf "/etc/apache2/sites-available/${host}.taed.conf"
sed -i -e "s/vulpes/${host}/g" "/etc/apache2/sites-available/${host}.taed.conf"

# Permissions
chown -R www-data:www-data /usr/local/www/taed/ 

# Enable
sudo a2ensite ${host}.taed
systemctl reload apache2

# Restart Apache
service apache2 restart
# Install php7.2-fpm
    sudo apt-get install software-properties-common
    sudo add-apt-repository ppa:ondrej/php
    sudo apt-get install php7.2-cli php7.2-fpm php7.2-curl php7.2-gd php7.2-mysql php7.2-mbstring zip unzip
    sudo service php7.2-fpm status
    sudo service php7.2-fpm start  # (if the service isn't running already)

# Install nginx
    sudo apt-get install -y nginx
    sudo ufw allow 'Nginx HTTP'
    sudo service nginx status # Check status
    sudo service nginx start # Start nginx if it is not already running

# Install mysql
    sudo apt install mysql-server
    sudo mysql_secure_installation

    # Set password root
    mysql
    ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
    FLUSH PRIVILEGES;

# Install phpmyadmin
    sudo apt install wget
    sudo apt install php7.2-zip php7.2-json php7.2-mbstring php7.2-xml

    wget https://files.phpmyadmin.net/phpMyAdmin/5.1.1/phpMyAdmin-5.1.1-all-languages.zip 
    unzip phpMyAdmin-5.1.1-all-languages.zip 
    mv phpMyAdmin-5.1.1-all-languages /usr/share/phpmyadmin 

    mkdir /usr/share/phpmyadmin/tmp 
    chown -R www-data:www-data /usr/share/phpmyadmin 
    chmod 777 /usr/share/phpmyadmin/tmp 

# Import Databases
    coin_binance, coin_db

# Config nginx virtual host
    #coin_controller
    server {
        listen 8080;
        root /home/ubuntu/coins/coin_controller/public; #path to coin_controller
        index index.php index.html index.htm index.nginx-debian.html;
        server_name _;

        #error_log /var/log/nginx/error.log
        location / {
                try_files $uri $uri/ /index.php?$query_string;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php7.2-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
    }
    
    #phpmyadmin
    server {
        listen 3000;
        root /usr/share/phpmyadmin;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name _;

        location / {
                try_files $uri $uri/ /index.php?$query_string;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php7.2-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
    }

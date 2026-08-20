# PHP 7.4 cho portal Laravel 5.5 (chạy song song, không đụng PHP 8.4 của hệ thống)
# Build:  docker build -t norabt-portal-php74 -f coins/docker/php74.Dockerfile coins/docker
# Chạy:   xem start_portal.sh ở root repo
FROM php:7.4-cli

# composer.lock ghim mongodb/mongodb 1.16.1 -> cần ext-mongodb ^1.16 (1.16.x vẫn hỗ trợ PHP 7.4)
# GD (freetype+jpeg) bắt buộc: captcha login dùng imagecreate()/imagettftext()
RUN apt-get update \
    && apt-get install -y --no-install-recommends git unzip libssl-dev pkg-config \
        libpng-dev libjpeg62-turbo-dev libfreetype6-dev \
    && pecl install mongodb-1.16.2 \
    && docker-php-ext-enable mongodb \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install pdo_mysql bcmath gd \
    && rm -rf /var/lib/apt/lists/* /tmp/pear

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Chạy dưới uid của user ubuntu để file vendor/ tạo ra thuộc về host user
ENV COMPOSER_HOME=/tmp/composer COMPOSER_CACHE_DIR=/tmp/composer-cache
WORKDIR /app

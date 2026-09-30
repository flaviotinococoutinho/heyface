FROM php:8.4-cli-alpine AS base
COPY --from=mlocati/php-extension-installer:2.12.0 /usr/bin/install-php-extensions /usr/local/bin/
RUN IPE_PROCESSOR_COUNT=1 install-php-extensions mbstring pcntl sockets redis opcache
RUN apk add --no-cache --virtual .swoole-build $PHPIZE_DEPS linux-headers openssl-dev \
    && MAKEFLAGS="-j1" pecl install -D 'enable-sockets="yes" enable-openssl="yes" enable-brotli="no"' swoole-6.2.3 \
    && docker-php-ext-enable swoole \
    && apk del .swoole-build
RUN apk add --no-cache libstdc++ && php --ri swoole > /dev/null
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --prefer-dist --no-progress
COPY artisan ./artisan
COPY app ./app
COPY bootstrap ./bootstrap
COPY config ./config
COPY lang ./lang
COPY routes ./routes
COPY public ./public
COPY resources ./resources
RUN mkdir -p bootstrap/cache storage/logs storage/framework/cache storage/framework/views && composer dump-autoload --no-dev --classmap-authoritative && php artisan octane:install --server=swoole --no-interaction
COPY php.ini /usr/local/etc/php/conf.d/heyface.ini

FROM base AS runtime
RUN chown -R www-data:www-data /app/bootstrap/cache /app/storage
USER www-data
EXPOSE 8000
CMD ["sh", "-c", "php artisan config:cache && php artisan route:cache && exec php artisan octane:start --server=swoole --host=0.0.0.0 --port=8000 --workers=${OCTANE_WORKERS:-2} --task-workers=0 --max-requests=500"]

FROM base AS test
COPY tests ./tests
COPY phpunit.xml ./phpunit.xml
RUN composer install --prefer-dist --no-progress
CMD ["sh", "-c", "vendor/bin/pint --test && vendor/bin/phpunit"]

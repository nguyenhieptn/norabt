<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Default Database Connection Name
    |--------------------------------------------------------------------------
    |
    | Here you may specify which of the database connections below you wish
    | to use as your default connection for all database work. Of course
    | you may use many connections at once using the Database library.
    |
    */

    'default' => env('DB_CONNECTION', 'mysql'),

    /*
    |--------------------------------------------------------------------------
    | Database Connections
    |--------------------------------------------------------------------------
    |
    | Here are each of the database connections setup for your application.
    | Of course, examples of configuring each database platform that is
    | supported by Laravel is shown below to make development simple.
    |
    |
    | All database work in Laravel is done through the PHP PDO facilities
    | so make sure you have the driver for your particular database of
    | choice installed on your machine before you begin development.
    |
    */

    'connections' => [

        'mysql' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '127.0.0.1'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_db'),
            'username' => env('DB_USERNAME', 'phoenix'),
            'password' => env('DB_PASSWORD', 'Phoenix@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'binance' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '127.0.0.1'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_binance'),
            'username' => env('DB_USERNAME', 'phoenix'),
            'password' => env('DB_PASSWORD', 'Phoenix@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'lab' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '127.0.0.1'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab'),
            'username' => env('DB_USERNAME', 'phoenix'),
            'password' => env('DB_PASSWORD', 'Phoenix@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'lab_1y_full' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '127.0.0.1'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_1y_full_20211128'),
            // 'database' => env('DB_DATABASE', 'coin_1y_full_20201231'),
            'username' => env('DB_USERNAME', 'ngsi'),
            'password' => env('DB_PASSWORD', 'ngsi@123'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_chart' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '127.0.0.1'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_chart'),
            'username' => env('DB_USERNAME', 'ngsi'),
            'password' => env('DB_PASSWORD', 'ngsi@123'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_crawler' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_crawler'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],


        'coin_analytics' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '127.0.0.1'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_analytics'),
            'username' => env('DB_USERNAME', 'ngsi'),
            'password' => env('DB_PASSWORD', 'ngsi@123'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],


        'coin_lab_1_year' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_1_year'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],
        'coin_lab_2021' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_2021'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_2020' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_2020'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_2019' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_2019'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_2018' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_2018'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_2017' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_2017'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],


        'coin_lab_future_2021' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_future_2021'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_future_2020' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_future_2020'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_future_2019' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_future_2019'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_future_2018' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_future_2018'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_lab_future_2017' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_lab_future_2017'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_future' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_future'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        'coin_spot' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST', '192.168.68.25'),
            'port' => env('DB_PORT', '3306'),
            'database' => env('DB_DATABASE', 'coin_spot'),
            'username' => env('DB_USERNAME', 'crypto'),
            'password' => env('DB_PASSWORD', 'crypto@1235'),
            'unix_socket' => env('DB_SOCKET', ''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'strict' => true,
            'engine' => null,
        ],

        // 'mongo_crawler' => [
        //     'driver' => 'mongodb',
        //     'host' => '192.168.68.25',
        //     'port' => 27017,
        //     'database' => 'WMA45',
        //     'username' => 'crawler',
        //     'password' => 'crawler@1235',
        //     'options' => [
        //         'authSource' => 'WMA45'
        //     ]
        // ],

        'mongo_crawler' => [
            'driver' => 'mongodb',
            'host' => '192.168.68.25',
            'port' => 27017,
            'database' => 'raw_data',
            'username' => 'crawler',
            'password' => 'crawler@1245',
            'options' => [
                'database' => 'raw_data'
            ]
        ],

        'backtest_data' => [
            'driver' => 'mongodb',
            'host' => '103.48.194.149',
            'port' => 27017,
            'database' => 'backtest_data',
            'username' => 'crawler',
            'password' => 'crawler@1245',
            'options' => [
                'database' => 'backtest_data'
            ]
        ],
        'backtest_data_1m' => [
            'driver' => 'mongodb',
            'host' => '103.48.194.149',
            'port' => 27017,
            'database' => 'backtest_data_1m',
            'username' => 'crawler',
            'password' => 'crawler@1245',
            'options' => [
                'database' => 'backtest_data_1m'
            ]
        ],

        'backtest_data_1m_full' => [
            'driver' => 'mongodb',
            'host' => '103.48.194.149',
            'port' => 27018,
            'database' => 'backtest_data_1m',
            'username' => 'crawler',
            'password' => 'crawler@1245',
            'options' => [
                'database' => 'backtest_data_1m'
            ]
        ],
        'backtest_data_1m_custom' => [
            'driver' => 'mongodb',
            'host' => '103.48.194.149',
            'port' => 27018,
            'database' => 'backtest_data_1m_custom',
            'username' => 'crawler',
            'password' => 'crawler@1245',
            'options' => [
                'database' => 'backtest_data_1m_custom'
            ]
        ],

        'backtest_data_1m_spot' => [
            'driver' => 'mongodb',
            'host' => '103.48.194.149',
            'port' => 27018,
            'database' => 'backtest_data_1m_spot',
            'username' => 'crawler',
            'password' => 'crawler@1245',
            'options' => [
                'database' => 'backtest_data_1m_spot'
            ]
        ],

        'realtime_data' => [
            'driver' => 'mongodb',
            'host' => '192.168.68.25',
            'port' => 27017,
            'database' => 'realtime_data',
            'username' => 'crawler',
            'password' => 'crawler@1235',
            'options' => [
                'database' => 'realtime_data'
            ]
        ],

        'ftx_backtest_data' => [
            'driver' => 'mongodb',
            'host' => '103.48.194.149',
            'port' => 27018,
            'database' => 'ftx_backtest_data',
            'username' => 'crawler',
            'password' => 'crawler@1235',
            'options' => [
                'database' => 'ftx_backtest_data'
            ]
        ],




    ],

    /*
    |--------------------------------------------------------------------------
    | Migration Repository Table
    |--------------------------------------------------------------------------
    |
    | This table keeps track of all the migrations that have already run for
    | your application. Using this information, we can determine which of
    | the migrations on disk haven't actually been run in the database.
    |
    */

    'migrations' => 'migrations',

    /*
    |--------------------------------------------------------------------------
    | Redis Databases
    |--------------------------------------------------------------------------
    |
    | Redis is an open source, fast, and advanced key-value store that also
    | provides a richer set of commands than a typical key-value systems
    | such as APC or Memcached. Laravel makes it easy to dig right in.
    |
    */

    'redis' => [

        'client' => 'predis',

        'default' => [
            'host' => env('REDIS_HOST', '127.0.0.1'),
            'password' => env('REDIS_PASSWORD', null),
            'port' => env('REDIS_PORT', 6379),
            'database' => 0,
        ],

    ],

];

<?php

namespace App\Helpers\Customer;

use App\Helpers\DB\Models;

class Customer_helper
{
    private static $customer = null;

    public static function get()
    {
        return self::$customer;
    }
    public static function set($customer)
    {
        self::$customer = $customer;
    }
}

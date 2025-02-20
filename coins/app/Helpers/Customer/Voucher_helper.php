<?php

namespace App\Helpers\Customer;

use App\Helpers\DB\Models;

class Voucher_helper
{

    public static function create()
    {
        $voucherModel = Models::get('Admin/Vouchers');
        $voucher = '';
        while ($voucher == '' || $voucherModel->is_exist([[[VOUCHER_CODE, '=', $voucher]]])){
            $voucher = substr(str_shuffle(str_repeat("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 5)), 0, 5);
        }
        return $voucher;
    }
   
}

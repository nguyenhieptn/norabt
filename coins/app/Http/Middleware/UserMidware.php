<?php

namespace App\Http\Middleware;

use App\Helpers\Control\Ctrl;
use App\Helpers\Customer\Customer_helper;
use App\Helpers\Customer\Voucher_helper;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Token\JWToken;
use Closure;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\App;
use Illuminate\Support\Facades\Cookie;

class UserMidware
{
    public function handle($request, Closure $next)
    {

        $tokenKey = Ctrl::get('tokenKey', '');
        if ($tokenKey == '') return redirect('/pages/client?error=Hệ thống chưa cài đặt token key');

        $tokenString = $request->input('token', '');
        if ($tokenString == '') {
            $tokenString = $request->cookie('resident_token');
        } else {
            Cookie::queue(Cookie::make('resident_token', $tokenString, 7 * 24 * 60 * 60, '/', APP_DOMAIN));
        }
        
        $token = JWToken::payload($tokenString, ['key' => $tokenKey]);

        if (!isset($token->id) || !isset($token->fullName)) return redirect('/pages/client?error=Tính năng chỉ dùng cho cư dân');

        $customer = [
            CUS_ID => $token->id,
            CUS_NAME => $token->fullName,
            CUS_HOME => get($token->apartment, ''),
            CUS_TOWER => get($token->building, ''),
            CUS_GENDER => get($token->gender, ''),
            CUS_BIRTHDAY => get($token->birthday, ''),
            CUS_PHONE => get($token->phone, ''),
            CUS_EMAIL => get($token->email, ''),
        ];
        Customer_helper::set($customer);

        $customerModel = Models::get('Admin/Customers');
        if (!$customerModel->is_exist([[[CUS_ID, '=', $token->id]]])) {
            $result = $customerModel->add([$customer]);
            if (!$result['result']) return redirect('/pages/client?error= Xin lỗi quý khách, hệ thống đang xảy ra lỗi');
            // Models::get('Admin/Vouchers')->add([[
            //     VOUCHER_OID => 0,
            //     VOUCHER_CODE => Voucher_helper::create(),
            //     VOUCHER_VALUE => Ctrl::get('defaultVoucher', 100000),
            //     VOUCHER_TIME => Ctrl::get('startCampaign', time()),
            //     VOUCHER_EXPIRE => Ctrl::get('stopCampaign', time()),
            //     VOUCHER_CID => $token->id,
            //     VOUCHER_STATUS => VOUCHER_STATUS_NEW,
            // ]]);
        }

        return $next($request);
    }
}

<?php
// Tạo tài khoản portal theo yêu cầu của chủ hệ thống (chạy: php artisan tinker < file này)
// Dùng đúng model + Hash của app, giống hệt RegisterController (đang bị vô hiệu bằng die;)

use App\Helpers\DB\Models;
use Illuminate\Support\Facades\Hash;

$username = 'nora';
$plainPassword = 'nora123';
$email = 'nora@f5traders.com';

$authenModel = Models::get('Auth/Authentication');

if ($authenModel->is_exist([[[AUTHEN_USERNAME, '=', $username]]])) {
    echo "SKIP: user '$username' da ton tai - dang cap nhat mat khau + kich hoat\n";
    $authenModel->edit(
        [[[AUTHEN_USERNAME, '=', $username]]],
        [
            AUTHEN_PASS => Hash::make(base64_encode($plainPassword)),
            AUTHEN_ACTIVE => AUTHEN_ACTIVE_VERIFIED,
            AUTHEN_STATUS => AUTHEN_STATUS_APPROVE,
        ]
    );
    echo "DONE: da reset mat khau cho '$username'\n";
} else {
    $result = $authenModel->add([[
        AUTHEN_USERNAME => $username,
        AUTHEN_PASS => Hash::make(base64_encode($plainPassword)),
        AUTHEN_EMAIL => $email,
        AUTHEN_ACTIVE => AUTHEN_ACTIVE_VERIFIED,
        AUTHEN_STATUS => AUTHEN_STATUS_APPROVE,
        AUTHEN_GROUP => AUTHEN_GROUP_ROOT,
        AUTHEN_TIME => time(),
    ]]);
    echo $result['result'] ? "DONE: da tao user '$username'\n" : ('FAIL: ' . json_encode($result) . "\n");
}

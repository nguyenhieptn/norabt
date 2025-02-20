<?php
namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Helpers\Captcha\Captcha;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Http\Request;
use App\Helpers\Encrypt\Encrypt;
use App\Helpers\Mailer\MailFunction;
use App\Helpers\Token\JWToken;
use Illuminate\Support\Facades\Hash;

class PasswordController extends Controller
{
    /*
    |--------------------------------------------------------------------------
    | Login Controller
    |--------------------------------------------------------------------------
    |
    | This controller handles authenticating users for the application and
    | redirecting them to your home screen. The controller uses a trait
    | to conveniently provide its functionality to your applications.
    |
    */

    /**
     * Where to redirect users after login.
     *
     * @var string
     */

    /**
     * Create a new controller instance.
     *
     * @return void
     */
    public function __construct()
    {
        
    }
    
    public function sendEmail(Request $request){
        try {
            $captcha = $request->input('captcha', false);
            if(!Captcha::verifyCaptcha($captcha)){
                Reply::finish(false, 'Captcha is wrong');
            }
            
            $email = $request->input('email', '');
            if($email == '') Reply::finish(false, ERROR_UNDEFINE, ['data'=>'Email']);
            $accountData = Models::get('Auth/Authentication')->read([[ [AUTHEN_EMAIL, '=', $email], [AUTHEN_STATUS, '=', AUTHEN_STATUS_APPROVE] ]]);
            if(!$accountData['result']) return $accountData;
            if(!isset($accountData['data'][0])) Reply::finish(false, 'Email not found or blocked');
            $accountData = $accountData['data'][0];
            
            $payload = [
                'email' => $email,
            ];
          
            $token = JWToken::make($payload);

            $content = "<p><b>Hi ".$accountData->{AUTHEN_USERNAME}."</b></p>";
            $content .= "<p>Click to this link to reset Password:<p>";
            $content .= "<a href='".$_SERVER['HTTP_HOST']."/guest/password/view?token=".$token."'>Reset Password<a>";
            $content .= '<p> Incase the button not working, paste this link to your browser: '.$_SERVER['HTTP_HOST']."/guest/password/view?token=".$token.'</p>';

            $payloadEmail = [
                'to'=> $email,
                'subject' => APP_NAME,
                'html' => $content,
                'signature' => APP_NAME
            ];
            
            $result = MailFunction::send($payloadEmail);
            
            if(!$result['result']) return $result;
            
            Reply::finish(true, 'Success', 'Email is send. Please check your email.');
            
        }catch (\ErrorException $e){
            
            Reply::finish(false, 'Please checking you configuration');
        }
    }


    public function view(Request $request){
        $token = $request->input('token', '');
        return view('auth.passwords.reset', ['token'=>$token]);
    }
    
    public function reset(Request $request){
        try {
        $token = $request->input('token', '');
       
        if($token == '') throw new \ErrorException('No token');
       
        $payload = JWToken::payload($token);
        if(!$payload)  throw new \ErrorException(JWToken::getMessage());

        $email = get($payload->{'email'}, '');
        if($email == '') throw new \ErrorException('No Email');

        $authenModel = Models::get('Auth/Authentication');

        $pass = $request->input('password', '');
        if($pass == '') throw new \ErrorException('No password');

        if(!preg_match('/.{5,}/m', base64_decode($pass)) ) Reply::finish(false, 'Password must be at least 5 characters');
        
        $editResult = $authenModel->edit([
            DATA_KEY => [[[AUTHEN_EMAIL, '=', $email]]],
            DATA_EDITOR => [AUTHEN_PASS => Hash::make($pass)]
        ]);

        if(!$editResult['result']) return $editResult;
        Reply::finish(true, 'success', 'Reset Password successful. Sign in to start using'); 
        
    } catch (\ErrorException $e) {
        return Reply::finish(false, $e->getMessage()); 
    } 
        
    }
    
    
}

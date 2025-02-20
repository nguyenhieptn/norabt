<?php
namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Helpers\Auth\AuthenticatesUsers;
use App\Helpers\Captcha\Captcha;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Http\Request;
use App\Helpers\Encrypt\Encrypt;
use App\Helpers\Mailer\MailFunction;
use App\Helpers\Token\JWToken;
use Illuminate\Support\Facades\Hash;
use App\Helpers\Mailer\MailHelper;
use App\Helpers\Request\Query;
use Illuminate\Mail\Mailer;
use Illuminate\Support\Facades\Mail;

class RegisterController extends Controller
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
    
    public function view(){

        return "Unsupport";
        
        return view('auth.register');
        
    }
    
    public function register(Request $request){

        die;
        
        $data = $request->all();

        if(!Captcha::verifyCaptcha($data['captcha'])){
            Reply::finish(false, 'Captcha is wrong');
        }

        $authenModel = Models::get('Auth/Authentication');
        
        if(!isset($data['username']) || !isset($data['password']) || !isset($data['email'])){
            Reply::finish(false, 'Please fill all fields');
        }

        if($authenModel->is_exist([[ [AUTHEN_EMAIL, '=', $data['email']] ]])){
            Reply::finish(false, 'This email address already exists. 
            <br/>If you forgot your password you can <b class="button" onclick="resetPass()">reset</b> it. 
            <br/>If you still haven\'t received the confirmation email click to <b class="button" onclick="reverify()">resend the confirmation email</b>.');
        }

        if($authenModel->is_exist([[ [AUTHEN_USERNAME, '=', $data['username']] ]])){
            Reply::finish(false, 'This username already exists. Please chose another username');
        }
        
        if(!preg_match('/.{5,}/m', base64_decode($data['password'])) ) Reply::finish(false, 'Password must be at least 5 characters');

        
        $addData = [
            AUTHEN_USERNAME => $data['username'],
            AUTHEN_PASS => Hash::make($data['password']),
            AUTHEN_EMAIL => $data['email'],
            AUTHEN_ACTIVE => AUTHEN_ACTIVE_WAITTING,
            AUTHEN_STATUS => AUTHEN_STATUS_APPROVE,
            AUTHEN_GROUP => AUTHEN_GROUP_PROVIDER,
            AUTHEN_TIME => time(),
        
        ];

        $result = $authenModel->add([$addData]);
        if(!$result['result']) return $result;

        $result = $this->sendVerifyEmail($data['email']);
        if(!$result['result']) return $result;

        Reply::finish(true, 'success', "Thank you for contributing to building the ".APP_NAME." community. 
        Please check your email <b>".$data['email']."</b> to activate your account. If you do not receive the email please check the junk email or contact us at the website i-share.top");
    }


    public function reverify(Request $request){
        $data = $request->all();

        $email = get($data['email'], '');
        if($email == '') Reply::finish(false, ERROR_UNDEFINE, ['data'=>'Email']);

        if(!Captcha::verifyCaptcha($data['captcha'])){
            Reply::finish(false, 'Captcha is wrong');
        }

        $authenModel = Models::get('Auth/Authentication');

        $accountData = $authenModel->read([[[AUTHEN_EMAIL, '=', $email]]]);
        if(!$accountData['result']) return $accountData;
        if(!isset($accountData['data'][0])) Reply::finish(false, 'Email does not exist. Please register again');
        $accountData = $accountData['data'][0];

        if($accountData->{AUTHEN_ACTIVE} == AUTHEN_ACTIVE_VERIFIED) Reply::finish(false, 'Your account is Actived');
        if($accountData->{AUTHEN_STATUS} == AUTHEN_STATUS_DENY) Reply::finish(false, 'Your account blocked. Contact with us for helping');

        $result = $this->sendVerifyEmail($email);

        if(!$result['result']) return $result;

        Reply::finish(true, 'success', "Thank you for contributing to building the ".APP_NAME." community. 
        Please check your email <b>".$data['email']."</b> to activate your account. If you do not receive the email please check the junk email or contact us at the website i-share.top");

    }

    private function sendVerifyEmail($email){
        //create verify token

        $token = JWToken::make(['email'=>$email]);
        
        // send email verify

        $payloadEmail = [
                'to'=> $email,
                'subject' => APP_NAME,
                'html' => "
                    <h3>Confirmation email</h3>
                    <p>Thank you for contributing to building the ".APP_NAME." community. Click on the link below to confirm your account.</p>
                    <a href='".APP_AUTHEN."/guest/register/verify?token=$token'><button>Active Account</button></a>
                    <p> Incase the button not working, paste this link to your browser:".APP_AUTHEN."/guest/register/verify?token=$token</p>
                    <br/>
                ",
                'signature' => APP_NAME
            ];

        $result = MailFunction::send($payloadEmail);
        return $result;
    }
    
    public function verify(Request $request){
        try {
            $token = $request->input('token', '');
            if($token == '') throw new \ErrorException('No token');
            $data = JWToken::payload($token);
            
            if(!$data)  throw new \ErrorException(JWToken::getMessage());

            $email = get($data->{'email'}, '');
            if($email == '') throw new \ErrorException('No Email');

            $authenModel = Models::get('Auth/Authentication');

            $result = $authenModel->edit([
                DATA_KEY => [[[AUTHEN_EMAIL, '=', $email]]],
                DATA_EDITOR => [AUTHEN_ACTIVE => AUTHEN_ACTIVE_VERIFIED],
            ]);

            if(!$result['result']) return $result;
            return redirect('/login?success=Your account has been activated. Sign in to start using'); 
           
            
            
        } catch (\ErrorException $e) {
            return redirect('/login?error='.$e->getMessage()); 
        } 
        
         
    }
    
    
    
    
}

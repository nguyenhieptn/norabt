<?php
namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Helpers\Auth\AuthenticatesUsers;
use App\Helpers\Captcha\Captcha;
use App\Helpers\Request\Reply;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class LoginController extends Controller
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

    use AuthenticatesUsers;

    /**
     * Where to redirect users after login.
     *
     * @var string
     */
    protected $redirectTo = '/home';

    /**
     * Create a new controller instance.
     *
     * @return void
     */
    public function __construct()
    {
        // $this->middleware('guest')->except('logout');
    }
    
    public function captcha(Request $request){
        $id = $request->input('id', 'global');
        $captcha = Captcha::createCaptcha($id); 
        Reply::finish(true, 'Success', $captcha);
    }

    public function setToken(Request $request){
        $token = $request->input('token');
        $nextLink = $request->input('next');
        Auth::login($token);
        return redirect($nextLink);
    }
    
    
}

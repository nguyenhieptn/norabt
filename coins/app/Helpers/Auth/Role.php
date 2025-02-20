<?php 
namespace App\Helpers\Auth;

use App\Helpers\Request\Reply;
use Illuminate\Support\Facades\Auth;

class Role {

    function __construct(){
    }
    public static function checkRoot(){
        return Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ROOT;
    }

    public static function checkAdmin(){
        if(Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ROOT) return true;
        return Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ADMIN;
    }

    public static function check($role)
    {
        if(Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ROOT) return true;
        if(Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ADMIN) return true;
        if(Auth::user()->{AUTHEN_GROUP} != $role) Reply::finish(false, ERROR_PERMISSION);
    }

    public static function checkMonitor()
    {
        if(Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ROOT) return true;
        if(Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_ADMIN) return true;
        return Auth::user()->{AUTHEN_GROUP} == AUTHEN_GROUP_MONITOR;
    }
}

?>
<?php 
namespace App\Helpers\Uploader;

use App\Helpers\Token\JWToken;
class FileToken {
    
    public static $payload = null;
    public static function token($disk, $path, $files='All', $permission='All', $options=[]){
        
       $customClaims = ['disk'=>$disk, 'files' => $files, 'path'=>$path, 'permission' => $permission, 'options'=>$options];
       
       return JWToken::make($customClaims);
    }
    
    public static function getToken($request)
    {
        if($token = $request->cookie('utoken', false)) return $token;
        if($token = $request->input('utoken', false)) return $token;
        return false;
    }
    
    public static function check($token){
        try {

            $payload = JWToken::payload($token);
            self::$payload = $payload;
            return true;

        } catch (\Exception $e){
            return false;
        }
    }

}

FileToken::$payload = (object)[];

?>
<?php

namespace App\Helpers\Admin;

use App\Helpers\Request\Query;
use App\Helpers\Token\JWToken;

class LabQuery {
    
    
    public static function makeRemoteQuery($ip, $path, $param, $config=[]){
       
        $SECRET_KEY = 'v9rp=os36qdxpkc=fz^syxj-oeha)k&pzwyp%rlfa68n_q!k=n';
        $token = JWToken::make($param, [
            'key' => $SECRET_KEY,
            'iat' => time() - 10,
            'nbf' => time() - 10,
            'exp' => time() + 10,
            'aud' => 'phoenix_center',
        ]);
        $link = "http://$ip/$path?token=${token}";
        return Query::make($link, 'GET', [], ['dataType' => 'json'], $config);
    
    }
    
    
}


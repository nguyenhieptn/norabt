<?php
namespace App\Helpers\Mailer;
use App\Helpers\Token\JWToken;
use App\Helpers\Request\Reply;
use App\Helpers\Request\Query;
class MailFunction {
        
    public static function send($options, $mailer=null){
        
        $mtoken = JWToken::make([
            'action'=>'send',
            'name' => $mailer,
            'options' => $options,
        ]);
        $result = Query::make(APP_MAILER.'/api/mailer/mailer/send', 'post', ['token'=>$mtoken], ['dataType'=>'json']);
        if(!$result) return Reply::make(false, 'ERROR', ['data'=>'Can not send email']);
        if(!$result['result']) return $result;
        return $result;
        
    }
    
}
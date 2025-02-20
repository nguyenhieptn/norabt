<?php
namespace App\Helpers\Mailer;

use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Support\Facades\Config;
use Illuminate\Mail\Mailer;
use Illuminate\Support\Arr;
use Illuminate\Support\Str;
class MailFactory { 
    
    private static $mailers=[];
    private static $log='';
    private static $config=null;
    
    public static function make($name=null){

        if(isset($name)){
            $mailerCfg = Models::get('Mailer/Mailer_config')->read([[ 
                [MAIL_NAME, '=', $name], 
                [MAIL_FREE, '>', 0], 
                [MAIL_ACTIVE, '=', 1],
            ]], function($db){
                $db->orderBy(MAIL_WEIGHT, 'DESC');
            });
        }else{
            $mailerCfg = Models::get('Mailer/Mailer_config')->read([[ 
                [MAIL_FREE, '>', 0], 
                [MAIL_ACTIVE, '=', 1],
            ]], function($db){
                $db->orderBy(MAIL_WEIGHT, 'DESC');
            });
        }
        
        if(!$mailerCfg['result']){
            self::$log = $mailerCfg['data']['data'];
            return false;
        };

        if(!isset($mailerCfg['data'][0])){
            self::$log = "No mailer available";
            return false;
        }

        $mailerCfg = $mailerCfg['data'][0];
        self::$config = $mailerCfg;

        if(isset(self::$mailers[$mailerCfg->{MAIL_NAME}])) return self::$mailers[$mailerCfg->{MAIL_NAME}];
        
        $config = json_decode($mailerCfg->{MAIL_CONFIG}, true);
        $config['from'] = [ 
            'address' => $config['username'],
            'name' => $config['username'],
        ];
                
        Config::set('mail', $config);
        
        $app = app();
        $mail = new Mailer(
            $app['view'], $app['swift.mailer'], $app['events']
        );
    
        if ($app->bound('queue')) {
            $mail->setQueue($app['queue']);
        }
        
        // foreach (['from', 'reply_to', 'to'] as $type) {
        //     self::setGlobalAddress($mail, $config, $type);
        // }
        
        self::$mailers[$mailerCfg->{MAIL_NAME}] = $mail;
        
        return self::$mailers[$mailerCfg->{MAIL_NAME}];
        
    }

    public static function getMessage(){
        return self::$log;
    }

    public static function getConfig(){
        return self::$config;
    }
    
    
    // private static function setGlobalAddress($mailer, array $config, $type)
    // {
        
    //     $address = Arr::get($config, $type);
    //     if (is_array($address) && isset($address['address'])) {
    //         $mailer->{'always'.Str::studly($type)}($address['address'], $address['name']);
    //     }
    // }
    
}
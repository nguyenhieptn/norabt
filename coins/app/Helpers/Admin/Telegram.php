<?php

namespace App\Helpers\Admin;


class Telegram
{
    
    public static function send($text, $chartId=null, $botId = null)
    {
        $text = str_replace('"', "'", $text);
        if(php_sapi_name() == 'cli') echo "Telegram: $chartId $botId\n". $text . "\n";
        if(!$chartId || $chartId == '') return;
        if(!$botId) $botId = TELE_BOT_DEFAULT;
        $command = 'sudo php ' . base_path() . '/artisan telegram_send "'.$text.'" "'.$chartId.'" "'.$botId.'"  > /dev/null &';
        $result = exec($command);
        
    }

    public static function handleException($e, $chartId){
        $ms = $e->getFile() . " " . $e->getLine() . " " . $e->getMessage();
        Telegram::send(TELE_ICON_ERROR . " " . $ms, $chartId);
        echo $ms;
    }

}

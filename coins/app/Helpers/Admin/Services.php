<?php

namespace App\Helpers\Admin;

use App\Helpers\DB\Models;

class Services
{
    private static $isActiveResult = [];

    public static function isActive($serviceName)
    {
        if (!isset(self::$isActiveResult[$serviceName])) {
            self::$isActiveResult[$serviceName] = false;
            $output = shell_exec("systemctl is-active $serviceName");
            $outputs = preg_split('/\r\n|\r|\n/', $output);
            foreach ($outputs as $out) {
                if ($out == 'active') {
                    self::$isActiveResult[$serviceName] = true;
                    break;
                }
            }
        }

        return self::$isActiveResult[$serviceName];
    }

    public static function isRunning($command){
        if (!isset(self::$isActiveResult[$command])) {
            self::$isActiveResult[$command] = false;
            exec("sudo ps -aux | grep  \"$command\" | grep -v grep", $output, $return);
            if ($return == 0) {
                self::$isActiveResult[$command] = true;
            }
        }
        return self::$isActiveResult[$command];
    }

    public static function isDir($dir){
        if (!isset(self::$isActiveResult[$dir])) {
            self::$isActiveResult[$dir] = false;
            exec("sudo ls $dir", $output, $return);
            if ($return == 0) {
                self::$isActiveResult[$dir] = true;
            }
        }
        return self::$isActiveResult[$dir];
    }

    public static function restartTestnet($accountId){
        $accountService = "testnet_account@" . $accountId;
        if(self::isActive($accountService)){
            shell_exec("sudo systemctl restart " . $accountService);
        }
        return "sudo systemctl restart " . $accountService;
    }
}

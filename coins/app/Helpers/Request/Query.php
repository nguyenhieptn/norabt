<?php

namespace App\Helpers\Request;

use App\Helpers\Encrypt\Encrypt;
class Query {
    
    
    public static $ch = null;
    
    public static function make($url, $method = 'get', $post=array(), $options=[], $config=[]){
       
        self::$ch = curl_init();
        
        curl_setopt(self::$ch, CURLOPT_URL, $url);
        curl_setopt(self::$ch, CURLOPT_RETURNTRANSFER, true);
        // curl_setopt(self::$ch, CURLOPT_FOLLOWLOCATION, true);
        // curl_setopt(self::$ch, CURLOPT_POST, false);
        
        if(isset($options['header'])){
            curl_setopt(self::$ch, CURLOPT_HTTPHEADER, $options['header']);
        }
        
        foreach($config as $key=>$value){
            curl_setopt(self::$ch, $key, $value);
        }
        
        if($method == 'post'){
            if(is_string($post)){
                curl_setopt(self::$ch, CURLOPT_POST, true);
            }else{
                curl_setopt(self::$ch, CURLOPT_POST, count($post));
            }
            
            curl_setopt(self::$ch, CURLOPT_POSTFIELDS, $post);
        }
        
        $responseString = curl_exec(self::$ch); 
        
        // if(!isset($options['continue']) || !$options['continue']){
        //     curl_close(self::$ch);
        // }
       
        if(!$responseString){
            $ms = 'Error: "' . curl_error(self::$ch) . '" - Code: ' . curl_errno(self::$ch);
            return Reply::make(false, $ms);
        }
       
        if(isset($options['dataType']) && $options['dataType'] == 'json'){
            $responseString = json_decode($responseString, true);
            if(json_last_error() != JSON_ERROR_NONE) {
                return Reply::make(false, 'Data is not a json');
            }
        }
        
        return $responseString;
    
    }
    
    
    
    
    private static function getDataFromUrl($url){
        $dataString = explode('?', $url);
        if(!isset($dataString[1])) return [];
        $dataString = $dataString[1];
        $dataString = explode('&', $dataString);
        $data = [];
        foreach ($dataString as $value){
            $valueArray = explode('=', $value);
            if(!isset($valueArray[1]) || $valueArray[1]=='') continue;
            $data[trim($valueArray[0])] = trim($valueArray[1]);
        }
        return $data;
    }
    
}


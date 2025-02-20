<?php
namespace App\Helpers\Encrypt;

class Encrypt {
    
    public static function crypt_data($string, $action='e') {
        // you may change these values to your own
        try {
             
            $secret_key = "gsgsgsghkjjghksgs%^465#";
            $secret_iv = "etwdgsio##kljhjgf%^465#";
    
            $output = false;
            $encrypt_method = "AES-256-CBC";
            $key = hash( 'sha256', $secret_key );
            $iv = substr( hash( 'sha256', $secret_iv ), 0, 16 );
            if( $action == 'e' ) {
                $output = base64_encode( openssl_encrypt( time().'##time##'.$string, $encrypt_method, $key, 0, $iv ) );
            }
            else if( $action == 'd' ){
                $output = openssl_decrypt( base64_decode( $string ), $encrypt_method, $key, 0, $iv );
                $outputArray = explode('##time##', $output);
                $output = [];
                $output['payload'] = $outputArray[1];
                $output['iat'] = $outputArray[0];
    
            }
            return $output;
             
        }catch (\Exception $e) {
            return false;
        }
    }

    public static function crypt_lab($content, $id, $action = 'e')
    {
        try {
            $pattern = 'amxranNnaGdq';
            if ($action == 'e') {
                $content = base64_encode($content);
                $firstPart = $id.$pattern.substr($content, 0, 10000);
                $theRest = substr($content, 10000);
                $firstE = self::crypt_data($firstPart, 'e');
                return $firstE . $pattern . $theRest;
            } else {
                                
                $labArray = explode($pattern, $content);
                
                if(!isset($labArray[1])) $labArray[1] = '';
                
                $decryptData = self::crypt_data($labArray[0], 'd');
                $decryptData = $decryptData['payload'];
                $decryptArray = explode($pattern, $decryptData);

                return [
                    'id' => $decryptArray[0],
                    'lab' => $decryptArray[1].$labArray[1],
                ];
                
            }
            
        } catch (\Exception $e) {
            return [];
        }
        
    }
    
}

<?php 
namespace App\Helpers\View;
 
class Loader {
    private static $loaded = [];
    public static function asset($id, $data, $type = null){
       if(isset(self::$loaded[$id])){
           return '';
       }else{
          self::$loaded[$id] = true;
           switch ($type){
               case null:{
                   return $data;
               }
               case 'script':{
                   return '<script src="'.$data.'"></script>';
                   break;
               }
               case 'css':{
                   return '<link rel="stylesheet" href="'.$data.'" media="all" type="text/css">';
                   break;
               }
           }
       }
        
    }
}


?>
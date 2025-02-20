<?php 
namespace App\Helpers\DB;
use Illuminate\Support\Facades\DB;

class Models {

    function __construct(){
    }
    private static $models = [];
   
    public function getModel($modelName, $parameter=[]){
        
        if(isset(self::$models[$modelName])){
            return self::$models[$modelName];
        }
        
        $modelResolv = "App\\Model\\".str_replace('/', '\\', $modelName);
        self::$models[$modelName] = new $modelResolv(...$parameter);
        return self::$models[$modelName];
    } 
    
    public function set($modelName, $model){
        self::$models[$modelName] = $model;
    }

    public static function get($modelName, $parameter=[], $dbName = null){
        if(!isset(self::$models[$modelName])){
            $modelResolv = "App\\Model\\".str_replace('/', '\\', $modelName);
            self::$models[$modelName] = new $modelResolv(...$parameter);
        }
        if(isset($dbName)){
            self::$models[$modelName]->query_builder = DB::connection($dbName)->table(self::$models[$modelName]->name);
        }
        return self::$models[$modelName];
    }

    public static function clone($modelName, $parameter=[]){
        $modelResolv = "App\\Model\\".str_replace('/', '\\', $modelName);
        $model = new $modelResolv(...$parameter);
        if(method_exists($model, 'resetConnection' )) $model->resetConnection();
        return $model;
    }


   
}

?>
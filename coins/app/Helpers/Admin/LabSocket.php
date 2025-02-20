<?php

namespace App\Helpers\Admin;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;
use App\Helpers\Token\JWToken;
use Exception;
use Illuminate\Support\Facades\Redis;

class LabSocket {
    
    
    public static function makeRemoteQuery($server, $controler, $method, $param=[]){
       
        $id = makeId();

        $model = Models::get('Admin/Lab_node');
        $data = [
            'order_socket_id' => $id,
            'order_socket_server' => $server,
            'order_socket_controller' => $controler,
            'order_socket_method' => $method,
        ];

        $data += $param;
        $result = Reply::make(false, 'Can not get data');
        try {
            //code...
            Redis::publish('lab_order', json_encode($data));
            Redis::subscribe('lab_order_result', function($message) use($id, &$result){
                try {
                    $message = json_decode($message, true);
                    
                    if($message['order_socket_id'] == $id){
                        $result = $message['response'];
                        throw new Exception("success");
                    }
                } catch (\Throwable $th) {
                    if($th->getMessage() != 'success')
                        $result = Reply::make(false, $th->getMessage());
                    throw new Exception("success");
                }
                
            });

        } catch (\Exception $th) {
            Redis::unsubscribe('lab_order_result');
        }

        return $result;
    
    }
    
}


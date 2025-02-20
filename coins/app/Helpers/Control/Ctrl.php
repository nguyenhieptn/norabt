<?php

namespace App\Helpers\Control;

use App\Helpers\DB\Models;

class Ctrl
{
    public static $defaults = [
        CONTROL_LAB_DB => 'lab'
    ];

    public static function get($name, $default = null, $array = false)
    {
        if($default == null) $default = get(self::$defaults[$name], null);
        $result = Models::get('Control/Control')->read([[[CONTROL_NAME, '=', $name]]]);
        if (!$result['result']) return $default;
        if (!isset($result['data'][0])) return $default;
        if ($array) {
            return json_decode($result['data'][0]->{CONTROL_VALUE}, true);
        } else {
            return $result['data'][0]->{CONTROL_VALUE};
        }
    }

    public static function gets($nameArray){
        $result = Models::get('Control/Control')->read(null, function($db)use($nameArray){
            $db->whereIn(CONTROL_NAME, $nameArray);
        });
        if (!$result['result']) return [];
        $result = $result['data'];
        $resultIndex = [];
        foreach($result as $ctr){
            $resultIndex[$ctr->{CONTROL_NAME}] = $ctr->{CONTROL_VALUE};
        }
        $returnData = [];
        foreach($nameArray as $name){
            $returnData[$name] = get($resultIndex[$name], get(self::$defaults[$name], null));
        }

        return $returnData;

    }

    public static function set($name, $value, $array = false)
    {
        $ctlModel = Models::get('Control/Control');
        if ($array) $value = json_encode($value);
        if ($ctlModel->is_exist([[[CONTROL_NAME, '=', $name]]])) {
            return $ctlModel->edit([
                DATA_KEY => [[[CONTROL_NAME, '=', $name]]],
                DATA_EDITOR => [CONTROL_VALUE => $value]
            ]);
        } else {
            return $ctlModel->add([[CONTROL_NAME => $name, CONTROL_VALUE => $value]]);
        }
    }
}

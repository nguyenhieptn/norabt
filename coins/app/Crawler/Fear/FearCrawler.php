<?php

namespace App\Crawler\Fear;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class FearCrawler {

    public function crawl()
    {
        $fearModel = Models::get('Admin/Fear');

        $lastTime = 0;
        $limit = 10;

        $lastFear = $fearModel->read([], function($db){
            $db->orderBy(FEAR_TIME, 'DESC')->limit(1);
        });
        if(!$lastFear['result']) return $lastFear;
        if(isset($lastFear['data'][0])){
            $lastTime = doubleval($lastFear['data'][0]->{FEAR_TIME});
        }

        $time = round(microtime(true) * 1000);
        if($time - $lastTime > 9 * 86400* 1000) $limit = 1000;
        
        $data = Query::make('https://api.alternative.me/fng/?limit='.$limit, 'GET', null, ['dataType'=> 'json']);

        if(isset($data['data'])){
            $data = $data['data'];
           
            $timePoint = 0;

            $addData = [];
            foreach($data as $key=>$value){
                $timeStamp = (int)$value['timestamp'] * 1000;
                if( $timeStamp <= $lastTime) continue;

                array_unshift($addData, [
                    FEAR_TIME => $timeStamp,
                    FEAR_CLASS => $value['value_classification'],
                    FEAR_VALUE => $value['value'],
                ]);

            }

            if(count($addData) > 0){
                $fearModel->add($addData);
            }

        }

        return Reply::make(true, 'success');

    }
}
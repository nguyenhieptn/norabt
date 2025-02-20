<?php

namespace App\Crawler\Lab\Service;

use App\Crawler\Caculator\EmaRealtime;
use App\Crawler\Caculator\RsiEmaRealtime;
use App\Crawler\Caculator\RsiRealtime;
use App\Crawler\Caculator\SignalRealtime;
use App\Crawler\Lab\Calculate\IndexCalculate;
use App\Crawler\Lab\History\CandleHistory;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Illuminate\Support\Facades\DB;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

include('SocketConnector.php');


class CandleRealtime
{

    private $symbol;

    function __construct($symbol)
    {
        $frame = '1m';
        $this->symbol = $symbol;
        $this->frame = $frame;
        $this->data = [];

        $this->intervalTime = [
            '1m' => 60000,
            '3m' => 3 * 60000,
            '15m' => 15 * 60000,
            '1h' => 3600000,
            '4h' => 4 * 3600000,
            '1d' => 24 * 3600000,
            '1w' => 7 * 24 * 3600000
        ];

        $this->lastUpdateTime = [];

        $this->mongoDb = DB::connection('mongo_crawler');
    }

    public function crawl()
    {

        $errorLog = '';
        $errorTime = 0;

        //craw last 500 history value calculate indicate and get 50 last value
        foreach (['1m', '1w', '1d', '4h', '1h', '15m', '3m'] as $frame) {

            $this->data[$frame] = [];
            $model = Models::get('Admin/Lab_candle_' . $frame);
            $model->query_builder = DB::connection('coin_crawler')->table('lab_candle_' . $frame);

            $historyData = CandleHistory::craw($this->symbol, $frame, 500);
            if (!$historyData['result']) return $historyData;
            $historyData = (array)$historyData['data'];

            $data = array_slice($historyData, -50);
            $this->data[$frame]['data'] = $data;
            $this->data[$frame]['model'] = $model;

            $closeTimeColName = "lab_candle_" . $frame . "_close_time";
            $symbolColName = "lab_candle_" . $frame . "_symbol";
            $startpointColName = "lab_candle_" . $frame . "_startpoint";

            for($i = 0; $i < count($data); $i++){
                $closeTime = $data[$i][$closeTimeColName];
                if($data[$i][$startpointColName] != 1) continue;
                if(!$model->is_exist([[
                    [$symbolColName, '=', $this->symbol], 
                    [$closeTimeColName, '=', $closeTime], 
                    [$startpointColName, '=', 1] 
                ]])){
                    $model->add([$data[$i]]);
                }
            }

        }

        // mark trades and volume of all frame
        $length = count($this->data['1m']['data']);
        $candle1m0 = $this->data['1m']['data'][$length - 1];
        
        foreach ($this->data as $frame => $data) {
            $dataLength = count($data['data']);
            $lastData = $data['data'][$dataLength - 1];
            $tradesColName = "lab_candle_" . $frame . "_trades";
            $volumeColName = "lab_candle_" . $frame . "_volume";
           
            if ($frame != '1m') {
                $this->data[$frame]['close_1m_time'] = $candle1m0[LAB_CANDLE_1M_CLOSE_TIME];
                $this->data[$frame]['mark_trades'] = $lastData[$tradesColName] - $candle1m0[LAB_CANDLE_1M_TRADES];
                $this->data[$frame]['mark_volume'] = $lastData[$volumeColName] - $candle1m0[LAB_CANDLE_1M_VOLUME];
            }
        }

        

        try {

            $sp = $this->openSocket($errorLog);
            while (true) {

                if (!$sp || feof($sp)) {

                    $ms = 'Lost connection to market stream (' . $this->symbol . $this->frame . ')' . $errorLog;
                    echo $ms . "\n";
                    Telegram::send(TELE_ICON_ERROR . ' ' . $ms, TELE_REAL_ERROR);
                    echo "Try connect socket again\n";
                    $sp = $this->openSocket($errorLog);
                    if (!$sp || feof($sp)) {
                        echo "Socket not running sleep 15 seconds\n";
                        sleep(15);
                    }
                } else {
                    $data = websocket_read($sp, $errorLog);
                    if (!$data) {
                        $errorTime++;
                        if ($errorTime >= 30) {
                            fclose($sp);
                            $sp = null;
                        }
                        // echo "[" . $this->symbol . $this->frame . "] Lost $errorTime packages\n";
                    } else {
                        $errorTime = 0;
                        $this->catchEvent($data);
                    }
                }
            }
        } catch (\Exception $th) {
            $ms = 'Exception Lost connection to market stream (' . $this->symbol . $this->frame . ')' . $th->getFile() . " " . $th->getLine() . ' ' . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . ' ' . $ms, TELE_REAL_ERROR);
        }
    }


    private function openSocket(&$errorLog)
    {

        $streamName = [
            strtolower($this->symbol) . "@kline_" . $this->frame,
        ];

        if ($sp = websocket_open('ssl://fstream.binance.com:443', [], $errorLog, 10, '/stream?streams=' . implode('/', $streamName))) {
            return $sp;
        } else {
            echo "Server responed with: $errorLog\n";
            return false;
        }
    }




    private function catchEvent($streamData)
    {

        $time_start = microtime(true);

        $streamData = json_decode($streamData, true);

        if (json_last_error() == JSON_ERROR_NONE) {

            if (!isset($streamData['data'])) return;
            $data = $streamData['data'];
            $symbol = $data["s"];
            $candleData = $data["k"];
            $saveTime = intval($data['E']) <= intval($candleData['T']) ? intval($data['E']) : intval($candleData['T']);
            $time = floor($saveTime/250)*250;

            $interval = $candleData['i'];
            if ($interval != $this->frame) return;

            // if (!isset($this->timeLine[$interval])) $this->timeLine[$interval] = 0;
            // if ($time_start - $this->timeLine[$interval] < 1) return;

            // $this->timeLine[$interval] = $time_start;

            $editData = [
                'interval' => $candleData['i'],
                'start_time' => $candleData['t'],
                'close_time' => $candleData['T'],
                'symbol' => $candleData['s'],
                'o' => $candleData['o'],
                'c' => $candleData['c'],
                'h' => $candleData['h'],
                'l' => $candleData['l'],
                'volume' => $candleData['v'],
                'trades' => $candleData['n'],
                'is_close' => $candleData['x']
            ];

            

            $this->processData($editData, '1m', $time);
            $this->processData($editData, '3m', $time);
            $this->processData($editData, '15m', $time);
            $this->processData($editData, '1h', $time);
            $this->processData($editData, '4h', $time);
            $this->processData($editData, '1d', $time);
            $this->processData($editData, '1w', $time);

            // $this->updateRawData($data);

            // echo "Craw $symbol Excute totaltime $interval " . (microtime(true) - $time_start) . " second\n";
        }
    }


    public function processData($candle, $frame, $time)
    {
        $columnName = [
            'LAB_CANDLE_ID' => "lab_candle_" . $frame . "_id",
            'LAB_CANDLE_TIME' => "lab_candle_" . $frame . "_time",
            'LAB_CANDLE_SYMBOL' => "lab_candle_" . $frame . "_symbol",
            'LAB_CANDLE_OPEN_TIME' => "lab_candle_" . $frame . "_open_time",
            'LAB_CANDLE_CLOSE_TIME' => "lab_candle_" . $frame . "_close_time",
            'LAB_CANDLE_OPEN' => "lab_candle_" . $frame . "_open",
            'LAB_CANDLE_CLOSE' => "lab_candle_" . $frame . "_close",
            'LAB_CANDLE_HIGH' => "lab_candle_" . $frame . "_high",
            'LAB_CANDLE_LOW' => "lab_candle_" . $frame . "_low",
            'LAB_CANDLE_TRADES' => "lab_candle_" . $frame . "_trades",
            'LAB_CANDLE_VOLUME' => "lab_candle_" . $frame . "_volume",
            'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $frame . "_startpoint",
        ];

        if ($frame == '1m') {

            $updateData = [

                $columnName['LAB_CANDLE_SYMBOL'] => $candle['symbol'],
                $columnName['LAB_CANDLE_TIME'] => $time,
                $columnName['LAB_CANDLE_OPEN_TIME'] => $candle['start_time'],
                $columnName['LAB_CANDLE_CLOSE_TIME'] => $candle['close_time'],
                $columnName['LAB_CANDLE_OPEN'] => $candle['o'],
                $columnName['LAB_CANDLE_CLOSE'] => $candle['c'],
                $columnName['LAB_CANDLE_HIGH'] => $candle['h'],
                $columnName['LAB_CANDLE_LOW'] => $candle['l'],
                $columnName['LAB_CANDLE_TRADES'] => $candle['trades'],
                $columnName['LAB_CANDLE_VOLUME'] => $candle['volume'],
            ];

            if($candle['is_close']) $updateData[$columnName['LAB_CANDLE_STARTPOINT']] = 1;

           

            $frameData = $this->data[$frame]['data'];
            $model = $this->data[$frame]['model'];

            $lenth = count($frameData);
            $isUpdate = false;
            if ($frameData[$lenth - 1][$columnName['LAB_CANDLE_CLOSE_TIME']] == $updateData[$columnName['LAB_CANDLE_CLOSE_TIME']]) {
                $periodData = $frameData[$lenth - 2];
                array_pop($this->data[$frame]['data']);
                $isUpdate = true;
            } else {
                $periodData = $frameData[$lenth - 1];
                if(count($this->data[$frame]['data']) > 50 ) array_shift($this->data[$frame]['data']);
                $isUpdate = false;
            }

            IndexCalculate::calIndex($periodData, $updateData, $frame, $this->data[$frame]['data']);

           
            
            $this->data[$frame]['data'][] = $updateData;

            if ($isUpdate) {
                $result = $model->add([$updateData]);
                // $this->lastUpdateTime[$frame] = $time;
            } else {
                $model->add([$updateData]);
                // if(isset($this->lastUpdateTime[$frame])){
                //     $model->edit([
                //         DATA_KEY => [[
                //             [$columnName['LAB_CANDLE_SYMBOL'], '=', $this->symbol],
                //             [$columnName['LAB_CANDLE_TIME'], '=', $this->lastUpdateTime[$frame]]
                //         ]],
                //         DATA_EDITOR => [$columnName['LAB_CANDLE_STARTPOINT'] => 1]
                //     ]);
                // }
                    
                // $this->lastUpdateTime[$frame] = $time;

            }
        } else {

            $frameData = $this->data[$frame]['data'];
            $model = $this->data[$frame]['model'];

            $lenth = count($frameData);
            $isUpdate = false;

            $lastData = $frameData[$lenth - 1];

            if ($lastData[$columnName['LAB_CANDLE_CLOSE_TIME']] < $candle['start_time']) {
                if($frame == '1w'){
                    $startTime = floor(doubleval($candle['start_time'])/$this->intervalTime['1d'])*$this->intervalTime['1d'];
                }else{
                    $startTime = floor(doubleval($candle['start_time'])/$this->intervalTime[$frame])*$this->intervalTime[$frame];
                }
                $updateData = [
                    $columnName['LAB_CANDLE_SYMBOL'] => $candle['symbol'],
                    $columnName['LAB_CANDLE_TIME'] => $time,
                    $columnName['LAB_CANDLE_OPEN_TIME'] => $startTime,
                    $columnName['LAB_CANDLE_CLOSE_TIME'] => $startTime + $this->intervalTime[$frame] - 1,
                    $columnName['LAB_CANDLE_OPEN'] => $candle['o'],
                    $columnName['LAB_CANDLE_CLOSE'] => $candle['c'],
                    $columnName['LAB_CANDLE_HIGH'] => $candle['h'],
                    $columnName['LAB_CANDLE_LOW'] => $candle['l'],
                    $columnName['LAB_CANDLE_TRADES'] => $candle['trades'],
                    $columnName['LAB_CANDLE_VOLUME'] => $candle['volume'],
                ];

                $this->data[$frame]['mark_trades'] = 0;
                $this->data[$frame]['mark_volume'] = 0;
                $this->data[$frame]['close_1m_time'] = $candle['close_time'];

                $periodData = $frameData[$lenth - 1];
                if(count($this->data[$frame]['data']) > 50 ) array_shift($this->data[$frame]['data']);
                $isUpdate = false;

            } else {

                $updateData = $lastData;

                //internal create close, high, low
                $updateData[$columnName['LAB_CANDLE_CLOSE']] = $candle['c'];
                $updateData[$columnName['LAB_CANDLE_TIME']] = $time;
                if (doubleval($updateData[$columnName['LAB_CANDLE_HIGH']]) < doubleval($candle['h'])) $updateData[$columnName['LAB_CANDLE_HIGH']] = $candle['h'];
                if (doubleval($updateData[$columnName['LAB_CANDLE_LOW']]) > doubleval($candle['l'])) $updateData[$columnName['LAB_CANDLE_LOW']] = $candle['l'];

                // internal create trades, volume
                $last1mClose = get($this->data[$frame]['close_1m_time'], 0);
               
                if ($last1mClose < $candle['start_time']) {
                    $this->data[$frame]['mark_trades'] = $lastData[$columnName['LAB_CANDLE_TRADES']];
                    $this->data[$frame]['mark_volume'] = $lastData[$columnName['LAB_CANDLE_VOLUME']];
                    $this->data[$frame]['close_1m_time'] = $candle['close_time'];
                    
                }

                $markTrades = get($this->data[$frame]['mark_trades'], $lastData[$columnName['LAB_CANDLE_TRADES']]);
                $markVolume = get($this->data[$frame]['mark_volume'], $lastData[$columnName['LAB_CANDLE_VOLUME']]);

                $updateData[$columnName['LAB_CANDLE_TRADES']] = $markTrades + $candle['trades'];
                $updateData[$columnName['LAB_CANDLE_VOLUME']] = $markVolume + $candle['volume'];

                $periodData = $frameData[$lenth - 2];
                array_pop($this->data[$frame]['data']);
                $isUpdate = true;
            }

            if($candle['is_close']){
                if($lastData[$columnName['LAB_CANDLE_CLOSE_TIME']] == $candle['close_time']){
                    $updateData[$columnName['LAB_CANDLE_STARTPOINT']] = 1;
                }
            }

            IndexCalculate::calIndex($periodData, $updateData, $frame, $this->data[$frame]['data']);
            if($frame == '15m' || $frame == '1h' || $frame == '4h' || $frame == '1d' || $frame == '1w'){
                IndexCalculate::calRsiWma($this->data[$frame]['data'], $updateData, $frame, 45);
            }
            
            $this->data[$frame]['data'][] = $updateData;


            if ($isUpdate) {
                $model->add([$updateData]);
                // $this->lastUpdateTime[$frame] = $time;
            } else {
                $model->add([$updateData]);
                // if(isset($this->lastUpdateTime[$frame])){
                //     $model->edit([
                //         DATA_KEY => [[
                //             [$columnName['LAB_CANDLE_SYMBOL'], '=', $this->symbol],
                //             [$columnName['LAB_CANDLE_TIME'], '=', $this->lastUpdateTime[$frame]]
                //         ]],
                //         DATA_EDITOR => [$columnName['LAB_CANDLE_STARTPOINT'] => 1]
                //     ]);
                // }
                    
                // $this->lastUpdateTime[$frame] = $time;

            }
        }
    }


    private function updateRawData($dt){
        
        $closeTime = intval($dt['k']['T']);
        $saveTime = intval($dt['E']) <= $closeTime ? intval($dt['E']) : $closeTime;
        $symbol = $dt['s'];

        $date = date('Y_m_d', intval($saveTime/1000));

        $coll = $date . "_" . $symbol . "_kline_1m";

        $k = $dt['k'];
        unset($dt['k']);
        foreach($k as $key => $val){
            $dt[$key] = $val;
        }
        
        $this->mongoDb->table($coll)->insert($dt);

        
    }


}

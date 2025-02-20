<?php

namespace App\Crawler\System\Service;

use App\Crawler\Caculator\EmaRealtime;
use App\Crawler\Caculator\RsiEmaRealtime;
use App\Crawler\Caculator\RsiRealtime;
use App\Crawler\Caculator\SignalRealtime;
use App\Crawler\System\Calculate\IndexCalculate;
use App\Crawler\System\History\CandleHistory;
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
            '1w' => 7 * 24 * 3600000,
        ];
    }

    public function crawl()
    {
       
        $errorLog = '';
        $errorTime = 0;

        //craw last 500 history value calculate indicate and get 50 last value
        foreach (['1m', '1w', '1d', '4h', '1h', '15m', '3m'] as $frame) {
            $this->data[$frame] = [];
            $model = Models::get('Admin/Candle_' . $frame);
            // $model->query_builder = DB::connection('coin_crawler')->table('candle_' . $frame);

            $symbolColName = "candle_" . $frame . "_symbol";

            $historyData = CandleHistory::craw($this->symbol, $frame, 500);
            if (!$historyData['result']) return $historyData;
            $historyData = (array)$historyData['data'];

            $model->drop([[[$symbolColName, '=', $this->symbol]]]);
            $model->add($historyData);

            $this->data[$frame]['data'] = array_slice($historyData, -50);
            $this->data[$frame]['model'] = $model;
        }

        

        // mark trades and volume of all frame
        $length = count($this->data['1m']['data']);
        $candle1m0 = $this->data['1m']['data'][$length - 1];
        // print_r($candle1m0);

        foreach ($this->data as $frame => $data) {
            $dataLength = count($data['data']);
            $lastData = $data['data'][$dataLength - 1];
            $tradesColName = "candle_" . $frame . "_trades";
            $volumeColName = "candle_" . $frame . "_volume";
           
            if ($frame != '1m') {
                $this->data[$frame]['close_1m_time'] = $candle1m0[CANDLE_1M_CLOSE_TIME];
                $this->data[$frame]['mark_trades'] = $lastData[$tradesColName] - $candle1m0[CANDLE_1M_TRADES];
                $this->data[$frame]['mark_volume'] = $lastData[$volumeColName] - $candle1m0[CANDLE_1M_VOLUME];
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
            ];

            $this->processData($editData, '1m');
            $this->processData($editData, '3m');
            $this->processData($editData, '15m');
            $this->processData($editData, '1h');
            $this->processData($editData, '4h');
            $this->processData($editData, '1d');
            $this->processData($editData, '1w');

            // echo "Craw $symbol Excute totaltime $interval " . (microtime(true) - $time_start) . " second\n";
        }
    }


    public function processData($candle, $frame)
    {
       
        $columnName = [
            'CANDLE_ID' => "candle_" . $frame . "_id",
            'CANDLE_SYMBOL' => "candle_" . $frame . "_symbol",
            'CANDLE_OPEN_TIME' => "candle_" . $frame . "_open_time",
            'CANDLE_CLOSE_TIME' => "candle_" . $frame . "_close_time",
            'CANDLE_OPEN' => "candle_" . $frame . "_open",
            'CANDLE_CLOSE' => "candle_" . $frame . "_close",
            'CANDLE_HIGH' => "candle_" . $frame . "_high",
            'CANDLE_LOW' => "candle_" . $frame . "_low",
            'CANDLE_TRADES' => "candle_" . $frame . "_trades",
            'CANDLE_VOLUME' => "candle_" . $frame . "_volume",
        ];

        if ($frame == '1m') {

            $updateData = [
                $columnName['CANDLE_SYMBOL'] => $candle['symbol'],
                $columnName['CANDLE_OPEN_TIME'] => $candle['start_time'],
                $columnName['CANDLE_CLOSE_TIME'] => $candle['close_time'],
                $columnName['CANDLE_OPEN'] => $candle['o'],
                $columnName['CANDLE_CLOSE'] => $candle['c'],
                $columnName['CANDLE_HIGH'] => $candle['h'],
                $columnName['CANDLE_LOW'] => $candle['l'],
                $columnName['CANDLE_TRADES'] => $candle['trades'],
                $columnName['CANDLE_VOLUME'] => $candle['volume'],
            ];

            $frameData = $this->data[$frame]['data'];
            $model = $this->data[$frame]['model'];

            $lenth = count($frameData);
            $isUpdate = false;
            if ($frameData[$lenth - 1][$columnName['CANDLE_CLOSE_TIME']] == $updateData[$columnName['CANDLE_CLOSE_TIME']]) {
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
                $model->edit([
                    DATA_KEY => [[
                        [$columnName['CANDLE_SYMBOL'], '=', $this->symbol],
                        [$columnName['CANDLE_CLOSE_TIME'], '=', $updateData[$columnName['CANDLE_CLOSE_TIME']]]
                    ]],
                    DATA_EDITOR => $updateData
                ]);
            } else {
                $model->add([$updateData]);
            }
        } else {

            $frameData = $this->data[$frame]['data'];
            $model = $this->data[$frame]['model'];

            $lenth = count($frameData);
            $isUpdate = false;

            $lastData = $frameData[$lenth - 1];

            if ($lastData[$columnName['CANDLE_CLOSE_TIME']] < $candle['start_time']) {
               
                if($frame == '1w'){
                    $startTime = floor(doubleval($candle['start_time'])/$this->intervalTime['1d'])*$this->intervalTime['1d'];
                }else{
                    $startTime = floor(doubleval($candle['start_time'])/$this->intervalTime[$frame])*$this->intervalTime[$frame];
                }
                // $startTime = $candle['start_time'];
                $updateData = [
                    $columnName['CANDLE_SYMBOL'] => $candle['symbol'],
                    $columnName['CANDLE_OPEN_TIME'] => $startTime,
                    $columnName['CANDLE_CLOSE_TIME'] => $startTime + $this->intervalTime[$frame] - 1,
                    $columnName['CANDLE_OPEN'] => $candle['o'],
                    $columnName['CANDLE_CLOSE'] => $candle['c'],
                    $columnName['CANDLE_HIGH'] => $candle['h'],
                    $columnName['CANDLE_LOW'] => $candle['l'],
                    $columnName['CANDLE_TRADES'] => $candle['trades'],
                    $columnName['CANDLE_VOLUME'] => $candle['volume'],
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
                $updateData[$columnName['CANDLE_CLOSE']] = $candle['c'];
                if (doubleval($updateData[$columnName['CANDLE_HIGH']]) < doubleval($candle['h'])) $updateData[$columnName['CANDLE_HIGH']] = $candle['h'];
                if (doubleval($updateData[$columnName['CANDLE_LOW']]) > doubleval($candle['l'])) $updateData[$columnName['CANDLE_LOW']] = $candle['l'];

                // internal create trades, volume
                $last1mClose = get($this->data[$frame]['close_1m_time'], 0);
               
                if ($last1mClose < $candle['start_time']) {
                    $this->data[$frame]['mark_trades'] = $lastData[$columnName['CANDLE_TRADES']];
                    $this->data[$frame]['mark_volume'] = $lastData[$columnName['CANDLE_VOLUME']];
                    $this->data[$frame]['close_1m_time'] = $candle['close_time'];
                    
                }

                $markTrades = get($this->data[$frame]['mark_trades'], $lastData[$columnName['CANDLE_TRADES']]);
                $markVolume = get($this->data[$frame]['mark_volume'], $lastData[$columnName['CANDLE_VOLUME']]);

                $updateData[$columnName['CANDLE_TRADES']] = $markTrades + $candle['trades'];
                $updateData[$columnName['CANDLE_VOLUME']] = $markVolume + $candle['volume'];

                $periodData = $frameData[$lenth - 2];
                array_pop($this->data[$frame]['data']);
                $isUpdate = true;
            }

            IndexCalculate::calIndex($periodData, $updateData, $frame, $this->data[$frame]['data']);
            if($frame == '1h' || $frame == '4h' || $frame == '1d' || $frame == '1w'){
                IndexCalculate::calRsiWma($this->data[$frame]['data'], $updateData, $frame, 45);
                
                IndexCalculate::calRsiWma($this->data[$frame]['data'], $updateData, $frame, 45, 'close', 'price_wma45');
                IndexCalculate::calRsiWma($this->data[$frame]['data'], $updateData, $frame, 45, 'rsi14', 'rsi_wma45');
                // IndexCalculate::calEma($this->data[$frame]['data'], $updateData, $frame, 9, 'close', 'price_ema');
                IndexCalculate::calEma($this->data[$frame]['data'], $updateData, $frame, 9, 'close', 'price_ema');
                IndexCalculate::calEma($this->data[$frame]['data'], $updateData, $frame, 9, 'rsi14', 'rsi_ema');
                IndexCalculate::calNet($updateData, $frame, "price_ema9", "price_wma45", 'net_ema9_wma45');
            }
            
            $this->data[$frame]['data'][] = $updateData;


            if ($isUpdate) {
                $model->edit([
                    DATA_KEY => [[
                        [$columnName['CANDLE_SYMBOL'], '=', $this->symbol],
                        [$columnName['CANDLE_CLOSE_TIME'], '=', $updateData[$columnName['CANDLE_CLOSE_TIME']]]
                    ]],
                    DATA_EDITOR => $updateData
                ]);
            } else {
                $model->add([$updateData]);
            }
        }
    }
}

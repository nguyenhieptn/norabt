<?php

namespace App\Crawler\Analytics;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

include(__DIR__.'/../SocketConnector.php');


class Candle24hCrawler
{

   
    function __construct()
    {
        $this->candleModel = Models::get('Admin/Candle_24h');
    }

    public function crawl()
    {

        $errorLog = '';
        $errorTime = 0;

        try {

            $sp = $this->openSocket($errorLog);
            while (true) {

                if (!$sp || feof($sp)) {

                    $ms = 'Lost connection to market stream miniTicker crawl volume' . $errorLog;
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
            $ms = 'Exception Lost connection to volume stream' . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . ' ' . $ms, TELE_REAL_ERROR);
        }
    }


    private function openSocket(&$errorLog)
    {

        $streamName = [
            // "!markPrice@arr@1s"
            // "btcusdt@kline_1m",
            // "etcusdt@kline_1m",
            "!miniTicker@arr"

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
        // echo $streamData . "\n";


        $startTime = round(microtime(true)*1000);
        $dateTime = floor($startTime/86400000) * 86400000;
        
        $streamData = json_decode($streamData, true);
        if(!$streamData) return;

        $streamData = $streamData['data'];
        $addData = [];
        foreach($streamData as $data){
            $sym = get($data['s'], null);
            if (strpos($sym, 'USDT') === false) continue;
            $time = get($data['E'], null);
            $close = get($data['c'], null);
            $open = get($data['o'], null);
            $low = get($data['l'], null);
            $high = get($data['h'], null);
            $volume = get($data['v'], null);
            $tradeVolume = get($data['q'], null);
            

            if($this->candleModel->is_exist([[[CANDLE_24H_SYMBOL, '=', $sym], [CANDLE_24H_DATE, '=', $dateTime]]])){
                $this->candleModel->edit([
                    DATA_KEY => [[[CANDLE_24H_SYMBOL, '=', $sym], [CANDLE_24H_DATE, '=', $dateTime], [CANDLE_24H_VOLUME_USDT, '<', $tradeVolume]]],
                    DATA_EDITOR => [
                        CANDLE_24H_TIME => $time,
                        CANDLE_24H_CLOSE => $close,
                        CANDLE_24H_OPEN => $open,
                        CANDLE_24H_LOW => $low,
                        CANDLE_24H_HIGH => $high,
                        CANDLE_24H_VOLUME => $volume,
                        CANDLE_24H_VOLUME_USDT => $tradeVolume
                    ]
                    ]);
            }else{
                $addData[] = [
                    CANDLE_24H_SYMBOL => $sym,
                    CANDLE_24H_DATE => $dateTime,
                    CANDLE_24H_TIME => $time,
                    CANDLE_24H_CLOSE => $close,
                    CANDLE_24H_OPEN => $open,
                    CANDLE_24H_LOW => $low,
                    CANDLE_24H_HIGH => $high,
                    CANDLE_24H_VOLUME => $volume,
                    CANDLE_24H_VOLUME_USDT => $tradeVolume
                ];
            }

            
                
        }

        if(count($addData) > 0){
            $this->candleModel->add($addData);
        }

        // echo "Process time " . (microtime(true)*1000 - $startTime) . " ms\n";
    }
}

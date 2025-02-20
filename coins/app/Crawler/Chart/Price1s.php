<?php

namespace App\Crawler\Chart;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

include(__DIR__.'/../SocketConnector.php');


class Price1s
{

   
    function __construct()
    {
       
        $this->model = Models::get('Admin/Price_1s');
        $this->watchList = Models::get('Admin/Watchlist');

        $symbols = $this->watchList->read([]);
        if(!$symbols['result']) return $symbols;

        $this->symbols = [];
        foreach($symbols['data'] as $val){
            $this->symbols[$val->{WL_SYMBOL}] = true;
        }


        
    }

    public function crawl()
    {

        $errorLog = '';
        $errorTime = 0;

        try {

            $sp = $this->openSocket($errorLog);
            while (true) {

                if (!$sp || feof($sp)) {

                    $ms = 'Lost connection to market stream miniTicker price 1s' . $errorLog;
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
            $ms = 'Exception Lost connection to 1s price stream' . $th->getMessage();
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

        $startTime = microtime(true);
        
        $streamData = json_decode($streamData, true);
        if(!$streamData) return;

        $streamData = $streamData['data'];
        $addData = [];
        $needDataLeng = count($this->symbols);
        $needDataCount = 0;
        foreach($streamData as $data){
            $sym = $data['s'];
           
            if(isset($this->symbols[$sym])){
                $needDataCount++;
                $time = $data['E'];
                $close = $data['c'];
                $open = $data['o'];
                $low = $data['l'];
                $high = $data['h'];
                $addData[] = [
                    PRICE_1S_SYMBOL => $sym,
                    PRICE_1S_TIME => $time,
                    PRICE_1S_CLOSE => $close,
                    PRICE_1S_OPEN => $open,
                    PRICE_1S_LOW => $low,
                    PRICE_1S_HIGH => $high,
                ];
                if($needDataCount == $needDataLeng) break;
            }
        }

        if(count($addData) > 0){
            $this->model->add($addData);
        }

        // echo "Process time " . (microtime(true) - $startTime) . " seconds\n";

       
    }
}

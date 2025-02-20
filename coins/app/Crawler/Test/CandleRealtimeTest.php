<?php

namespace App\Crawler\Test;

include('SocketConnectorOrigin.php');


class CandleRealtimeTest
{

    private $symbol;

    function __construct()
    {
        $this->isSendChanel = false;
    }

    public function crawl()
    {

        try {

            $sp = $this->openSocket($errorLog);

            if ($sp) {
                echo "Send Channel\n";
                $chanel = json_encode([
                    'event' => 'sub',
                    'params' => [
                        'channel' => 'market_btcusdt_ticker',
                        'id' => '14154656788876',
                    ]
                ]);
                echo $chanel . "\n";
                websocket_write($sp, $chanel, false, false);
                $this->isSendChanel = true;
            }

            while (true) {

                $data = websocket_read($sp, $errorLog);
                $this->catchEvent($data, $sp);
            }
        } catch (\Exception $th) {
            $ms = 'Exception Lost connection to market stream' . $th->getFile() . " " . $th->getLine() . ' ' . $th->getMessage();
            echo $ms . "\n";
        }
    }


    private function openSocket(&$errorLog)
    {


        if ($sp = websocket_open(
            "api.cointiger.com",
            443,
            [],
            $errorLog,
            100,
            true,
            true,
            '/exchange-market/ws'
        )) {
            echo $errorLog . "\n";


            // echo "Write socket successfully\n";
            return $sp;
        } else {
            echo "Server responed with: $errorLog\n";
            return false;
        }
    }




    private function catchEvent($streamData, $sp)
    {
        try {
            $data = gzdecode($streamData);
            if (strpos($data, 'ping') !== false) {
                echo "Get Ping $data\n";
                $pong = str_replace('ping', 'pong', $data);
                echo "Send Pong $pong\n";
                websocket_write($sp, $pong);
            } else {
                echo $data . "\n";
            }
        } catch (\Throwable $th) {
            
        }
    }
}

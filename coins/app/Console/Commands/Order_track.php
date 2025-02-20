<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;

class Order_track extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'order_track';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Command description';

    /**
     * Create a new command instance.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
        
    }

    /**
     * Execute the console command.
     *
     * @return mixed
     */
    public function handle()
    {
        $coinModel = Models::get('Admin/Watchlist');
        $candle1mModel = Models::get('Admin/Candle_1m');
        $candle4hModel = Models::get('Admin/Candle_4h');
        $candle1hModel = Models::get('Admin/Candle_1h');
        $candle15mModel = Models::get('Admin/Candle_15m');
        $trackModel = Models::get('Admin/Order_track');
        $coins = $coinModel->read([]);
        if(!$coins['result']) return $coins;
        $coins = $coins['data'];

        $addData = [];
        foreach($coins as $key => $coin){
            $candle4h = $candle4hModel->read([[[CANDLE_4H_SYMBOL, '=', $coin->{WL_SYMBOL}]]], function($db){
                $db->orderBy(CANDLE_4H_CLOSE_TIME, 'DESC')->limit(2);
            });

            if(!$candle4h['result']) continue;
            $candle4h = $candle4h['data'];
            if(!isset($candle4h[0]) || !isset($candle4h[1])) continue;

            $close = $candle4h[0]->{CANDLE_4H_CLOSE};
            $low = $candle4h[1]->{CANDLE_4H_LOW};
            $high = $candle4h[1]->{CANDLE_4H_HIGH};
            $up = ($close - $high)*100 / $close;
            $up = floor($up * 100)/100;
            $down = ($close - $low)*100 / $close;
            $down = floor($down * 100)/100;

            $close4h = $candle4h[1]->{CANDLE_4H_CLOSE};
            $change = ($close - $close4h)*100/$close;
            $change = floor($change * 100)/100;


            $candle1h = $candle1hModel->read([[[CANDLE_1H_SYMBOL, '=', $coin->{WL_SYMBOL}]]], function($db){
                $db->orderBy(CANDLE_1H_CLOSE_TIME, 'DESC')->limit(2);
            });

            if(!$candle1h['result']) continue;
            $candle1h = $candle1h['data'];
            if(!isset($candle1h[0]) || !isset($candle1h[1])) continue;

            $close1h = $candle1h[1]->{CANDLE_1H_CLOSE};
            $high1h = $candle1h[1]->{CANDLE_1H_HIGH};
            $low1h = $candle1h[1]->{CANDLE_1H_LOW};
            $up1h = ($close - $high1h)*100 / $high1h;
            $up1h = floor($up1h * 100)/100;
            $down1h = ($close - $low1h)*100 / $low1h;
            $down1h = floor($down1h * 100)/100;


            $candle15m = $candle15mModel->read([[[CANDLE_15M_SYMBOL, '=', $coin->{WL_SYMBOL}]]], function($db){
                $db->orderBy(CANDLE_15M_CLOSE_TIME, 'DESC')->limit(2);
            });

            if(!$candle15m['result']) continue;
            $candle15m = $candle15m['data'];
            if(!isset($candle15m[0]) || !isset($candle15m[1])) continue;

            $close15m = $candle15m[1]->{CANDLE_15M_CLOSE};
            $high15m = $candle15m[1]->{CANDLE_15M_HIGH};
            $low15m = $candle15m[1]->{CANDLE_15M_LOW};
            $up15m = ($close - $high15m)*100 / $high15m;
            $up15m = floor($up15m * 100)/100;
            $down15m = ($close - $low15m)*100 / $low15m;
            $down15m = floor($down15m * 100)/100;

            $addData[] = [
                ORDER_TRACK_ID => $key,
                ORDER_TRACK_SYMBOL => $coin->{WL_SYMBOL},
                ORDER_TRACK_PRICE => $close,
                ORDER_TRACK_LOW => $low,
                ORDER_TRACK_HIGH => $high,
                ORDER_TRACK_UP => $up,
                ORDER_TRACK_DOWN => $down,
                ORDER_TRACK_CLOSE => $close4h,
                ORDER_TRACK_CHANGE => $change,
                ORDER_TRACK_RSI4H_0 => $candle4h[0]->{CANDLE_4H_RSI14},
                ORDER_TRACK_RSI4H_1 => $candle4h[1]->{CANDLE_4H_RSI14},
                ORDER_TRACK_1H_UP => $up1h,
                ORDER_TRACK_1H_DOWN => $down1h,
                ORDER_TRACK_15M_UP => $up15m,
                ORDER_TRACK_15M_DOWN => $down15m,
            ];


        }

        $trackModel->drop('All');
        $trackModel->add($addData);
        
        
        
    }

   
}

<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;


use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;

class Order_track_alert_2 extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'order_track_alert_2';

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
        $candle1DModel = Models::get('Admin/Candle_1d');
        $time = round(microtime(true) * 1000);

        $data1D = $candle1DModel->read([[[CANDLE_1D_CLOSE_TIME, '>', $time - 86400 * 1000]]], function ($db) {
            $db->orderBy(CANDLE_1D_CLOSE_TIME, 'DESC');
        });
        if (!$data1D['result']) return $data1D;
        $data1D = $data1D['data'];
        $addData1D = [];
        foreach ($data1D as $data) {
            $symbol = $data->{CANDLE_1D_SYMBOL};
            if (!isset($candle1D[$symbol])) $candle1D[$symbol] = [];
            $candle1D[$symbol][] = $data;
            if (count($candle1D[$symbol]) == 2) {

                $close = $candle1D[$symbol][0]->{CANDLE_1D_CLOSE};
                $low = $candle1D[$symbol][1]->{CANDLE_1D_LOW};
                $high = $candle1D[$symbol][1]->{CANDLE_1D_HIGH};

                $up = ($close - $high) * 100 / $close;
                $up = floor($up * 100) / 100;
                $down = ($close - $low) * 100 / $close;
                $down = floor($down * 100) / 100;

                $addData1D[$symbol] = [
                    'close' => $close,
                    'low' => $low,
                    'high' => $high,
                    'up' => $up,
                    'down' => $down,
                    'rsi_0' => $candle1D[$symbol][0]->{CANDLE_1D_RSI14},
                    'rsi_1' => $candle1D[$symbol][1]->{CANDLE_1D_RSI14},
                    'rsi_wma' => $candle1D[$symbol][0]->{CANDLE_1D_RSI_WMA},
                ];
            }
        }
        print_r($addData1D);
    }
}

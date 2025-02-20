<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;

class Order_alert extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * 
     * service name: order_alert
     * Service for alerting order before real order.
     */
    protected $signature = 'order_alert';

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

        try {
            $this->alarmResult = [];
            $this->fear = null;
            $this->fearUpdateTime = time();

            date_default_timezone_set('Asia/Ho_Chi_Minh');

            $trackModel = Models::get('Admin/Order_track');
            $this->resultModel = Models::get('Admin/Testnet_results');

            $this->frameData = [
                '4h' => [
                    'model' => Models::get('Admin/Candle_4h'),
                    'col_symbol' => CANDLE_4H_SYMBOL,
                    'col_low' => CANDLE_4H_LOW,
                    'col_close_time' => CANDLE_4H_CLOSE_TIME
                ],

                '1d' => [
                    'model' => Models::get('Admin/Candle_1d'),
                    'col_symbol' => CANDLE_1D_SYMBOL,
                    'col_low' => CANDLE_1D_LOW,
                    'col_close_time' => CANDLE_1D_CLOSE_TIME
                ]
            ];

            while (true) {

                sleep(15);

                $this->alarmCfg = Ctrl::get('alert_order_configuration', null);
                $this->alarmCfg = json_decode($this->alarmCfg, true);
                if ($this->alarmCfg == null) $this->alarmCfg = [];

                $time = round(microtime(true) * 1000);

                $datas = $trackModel->read([]);
                $datas = $datas['data'];
                $symbolData = [];

                foreach ($datas as $data) {
                    $symbolData[$data->{ORDER_TRACK_SYMBOL}] = (array)$data;
                }

                foreach ($symbolData as $symbol => $data) {
                    $this->checkAlarm($symbolData, $symbol);
                }
            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }


    private function checkAlarm($data, $symbol)
    {

        foreach ($this->alarmCfg as $key => $alarm) {
            if (isset($alarm['active']) && $alarm['active'] == 0) continue;
            $id = $symbol . "_" . $alarm['id'];

            if (isset($this->alarmCfg[$key]['next_alert'])) {
                $nextAlert = get($alarm['next_alert'][$symbol], 0);
                if (time() < $nextAlert) continue;
            }

            if ($this->resultModel->is_exist([[[TESTNET_RESULT_SYMBOL, '=', $symbol], [TESTNET_RESULT_PENDING, '=', 1], [TESTNET_RESULT_STRATEGY, '=', 35]]])) {
                continue;
            }

            $checkResult = $this->checkCondition($data, $alarm['condition'], $symbol);
            if ($checkResult === null) continue;
            if ($checkResult) {
                if (!isset($this->alarmCfg[$key]['next_alert']) || !is_array($this->alarmCfg[$key]['next_alert'])) $this->alarmCfg[$key]['next_alert'] = [];
                $this->alarmCfg[$key]['next_alert'][$symbol] = $this->getNextAlert($alarm['frame']);
                $this->makeAlert($this->alarmCfg[$key], $symbol);
                // echo $symbol;
                // print_r($data[$symbol]);
                // print_r($alarm['condition']);

            }
        }

        Ctrl::set('alert_order_configuration', json_encode($this->alarmCfg));
    }


    private function getNextAlert($frame)
    {
        if ($frame == '4h') {
            return ceil(time() / (4 * 60 * 60)) * (4 * 60 * 60);
        } else if ($frame == '1d') {
            return ceil(time() / (86400)) * (86400);
        }
    }

    private function checkCondition($data, $condition, $symbol)
    {
        $result = true;
        foreach ($condition as $con) {
            $compareResult = $this->compare($data, $con, $symbol);
            if ($compareResult === null) return null;
            if (!$compareResult) {
                $result = false;
                break;
            }
        }
        return $result;
    }

    private function compare($data, $condition, $defaultSymbol)
    {
        if (isset($condition['symbol']) && $condition['symbol'] != '') {
            $sym = $condition['symbol'];
        } else {
            $sym = $defaultSymbol;
        }

        $col = $condition['column'];
        $com1 = $this->calCom1($data, $sym, $col);

        $logic = $condition['logic'];
        $com2 = $condition['value'];
        if ($com1 === null || $com2 === null) return null;
        if (is_numeric($com1)) $com1 = doubleval($com1);
        if (is_numeric($com2)) $com2 = doubleval($com2);
        if ($logic == '=') return $com1 == $com2;
        if ($logic == '>') return $com1 > $com2;
        if ($logic == '<') return $com1 < $com2;
        if ($logic == '>=') return $com1 >= $com2;
        if ($logic == '<=') return $com1 <= $com2;
        if ($logic == '!=') return $com1 != $com2;
    }


    private function calCom1($data, $sym, $col)
    {

        if ($col == 'fear') {

            if ($this->fear != null && time() - $this->fearUpdateTime < 300) {
                return doubleval($this->fear);
            }

            $fearModel = Models::get('Admin/Fear');
            $lastFear = $fearModel->read([], function ($db) {
                $db->orderBy(FEAR_TIME, 'DESC')->limit(1);
            });
            if (!$lastFear['result']) return null;
            if (isset($lastFear['data'][0])) {
                $this->fearUpdateTime = time();
                $this->fear = doubleval($lastFear['data'][0]->{FEAR_VALUE});
            }

            return $this->fear;
        } else {

            if (!isset($data[$sym])) {
                $com1 = null;
            } else {
                $com1 = get($data[$sym][$col], null);
            }
            return $com1;
        }
    }

    private function makeAlert($alarm, $symbol)
    {
        $icon = $alarm['icon'];
        $content = $alarm['content'];
        $botId = $alarm['bot'];
        $groupId = $alarm['group'];


        $frame = $alarm['frame'];

        $frameData = $this->frameData[$frame];

        $low = $frameData['model']->read([[[$frameData['col_symbol'], '=', $symbol]]], function ($db) use ($frameData) {
            $db->orderBy($frameData['col_close_time'], 'DESC')->limit(2);
        });
        if (!$low['result']) return $low;
        $low = $low['data'];
        if (count($low) < 2) return Reply::make(false, 'Can not get low price');

        $phases = $alarm['phases'];

        $low = doubleval($low[1]->{$frameData['col_low']});
        $enterPricePercent = get($alarm['enter_price'], 0);
        $enterPrice = (100 * $low) / (100 - $enterPricePercent);

        $matchPrice = $enterPrice;
        $matchQty = 0;

        $phaseMs = '';

        foreach ($phases as $key => $phase) {
            if ($key == 0) {

                $phase[$key]['price'] = $enterPrice;
                $matchPrice = $enterPrice;
                $matchQty = doubleval($phase['enter_package']) / $matchPrice;
                $takeprofit = get($phase['takeprofit'], 0.8);
                $takeprofitPrice = $matchPrice * (1 + $takeprofit / 100);

                $phaseMs .= "- " . $phase['name'] . $phase['note']
                    . "\n + Giá vào ≈ " . round($enterPrice * 10000) / 10000 . " USDT"
                    . "\n + Tiền vào  " . $phase['enter_package'] . " %"
                    . "\n + Tỷ lệ Chốt lời: " . $phase['takeprofit'] . " %"
                    . "\n + Giá chốt lời ≈ " . round($takeprofitPrice * 10000) / 10000 . " USDT";
            } else {

                $price = $matchPrice * (1 + doubleval($phase['profit']) / 100);
                $qty = doubleval($phase['enter_package']) / $price;
                $matchPrice = ($price * $qty + $matchPrice * $matchQty) / ($matchQty + $qty);
                $matchQty = $matchQty + $qty;
                $phase[$key]['price'] = $price;
                $takeprofit = get($phase['takeprofit'], 0.8);
                $takeprofitPrice = $matchPrice * (1 + $takeprofit / 100);

                $phaseMs .= "\n- " . $phase['name'] . $phase['note']
                    . "\n + Giá vào ≈ " . round($price * 10000) / 10000 . " USDT"
                    . "\n + Tiền vào: " . $phase['enter_package'] . " %"
                    . "\n + Tỷ lệ Chốt lời: " . $phase['takeprofit'] . " %"
                    . "\n + Giá chốt lời ≈ " . round($takeprofitPrice * 10000) / 10000 . " USDT";
            }
        }

        $ms = "[" . $symbol . "] " . $content
            . "\n- Hiệu lực : " . date('m/d/Y H:i:s', $alarm['next_alert'][$symbol])
            . "\n" . $phaseMs;

        Telegram::send($icon . " " . $ms, $groupId, $botId);
    }
}

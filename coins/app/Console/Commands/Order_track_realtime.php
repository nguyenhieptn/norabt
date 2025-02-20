<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;

class Order_track_realtime extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * 
     * service name: phoenix_alert
     */
    protected $signature = 'order_track_realtime';

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
            $this->alarmCfg = Ctrl::get('alarm_configuration', null);
            $this->alarmCfg = json_decode($this->alarmCfg, true);
            if ($this->alarmCfg == null) $this->alarmCfg = [];

            $this->alarmResult = [];
            $this->fear = null;
            $this->fearUpdateTime = time();

            $coinModel = Models::get('Admin/Watchlist');

            $candle4HModel = Models::get('Admin/Candle_4h');
            $candle1HModel = Models::get('Admin/Candle_1h');
            $candle15MModel = Models::get('Admin/Candle_15m');
            $candle3MModel = Models::get('Admin/Candle_3m');
            $candle1DModel = Models::get('Admin/Candle_1d');
            $candle1WModel = Models::get('Admin/Candle_1w');
            $trackModel = Models::get('Admin/Order_track');

            $coins = $coinModel->read([[[WL_STOPTIME, '=', null]]]);
            if (!$coins['result']) return $coins;
            $coins = $coins['data'];

            while (true) {

                sleep(5);

                // $activeTime = Ctrl::get('order_track_active_time', time());
                // if(time() - $activeTime > 60) continue;

                $time = round(microtime(true) * 1000);

                $data4H = $candle4HModel->read([[[CANDLE_4H_CLOSE_TIME, '>', $time - 4 * 60 * 60 * 1000]]], function ($db) {
                    $db->orderBy(CANDLE_4H_CLOSE_TIME, 'DESC');
                });
                if (!$data4H['result']) return $data4H;
                $data4H = $data4H['data'];

                $data1H = $candle1HModel->read([[[CANDLE_1H_CLOSE_TIME, '>', $time - 1 * 60 * 60 * 1000]]], function ($db) {
                    $db->orderBy(CANDLE_1H_CLOSE_TIME, 'DESC');
                });
                if (!$data1H['result']) return $data1H;
                $data1H = $data1H['data'];

                $data15M = $candle15MModel->read([[[CANDLE_15M_CLOSE_TIME, '>', $time - 15 * 60 * 1000]]], function ($db) {
                    $db->orderBy(CANDLE_15M_CLOSE_TIME, 'DESC');
                });
                if (!$data15M['result']) return $data15M;
                $data15M = $data15M['data'];


                $data3M = $candle3MModel->read([[[CANDLE_3M_CLOSE_TIME, '>', $time - 3 * 60 * 1000]]], function ($db) {
                    $db->orderBy(CANDLE_3M_CLOSE_TIME, 'DESC');
                });
                if (!$data3M['result']) return $data3M;
                $data3M = $data3M['data'];

                $data1D = $candle1DModel->read([[[CANDLE_1D_CLOSE_TIME, '>', $time - 86400 * 1000]]], function ($db) {
                    $db->orderBy(CANDLE_1D_CLOSE_TIME, 'DESC');
                });
                if (!$data1D['result']) return $data1D;
                $data1D = $data1D['data'];


                $data1W = $candle1WModel->read([[[CANDLE_1W_CLOSE_TIME, '>', $time - 7 * 86400 * 1000]]], function ($db) {
                    $db->orderBy(CANDLE_1W_CLOSE_TIME, 'DESC');
                });
                if (!$data1W['result']) return $data1W;
                $data1W = $data1W['data'];


                $candle4H = [];
                $candle1H = [];
                $candle15M = [];
                $candle3M = [];
                $candle1D = [];
                $candle1W = [];

                $addData4H = [];
                $addData1H = [];
                $addData15M = [];
                $addData3M = [];
                $addData1D = [];
                $addData1W = [];

                foreach ($data4H as $data) {
                    $symbol = $data->{CANDLE_4H_SYMBOL};
                    if (!isset($candle4H[$symbol])) $candle4H[$symbol] = [];
                    $candle4H[$symbol][] = $data;
                    if (count($candle4H[$symbol]) == 2) {

                        $close = $candle4H[$symbol][0]->{CANDLE_4H_CLOSE};
                        $low = $candle4H[$symbol][1]->{CANDLE_4H_LOW};
                        $high = $candle4H[$symbol][1]->{CANDLE_4H_HIGH};
                        $up = ($close - $high) * 100 / $close;
                        $up = floor($up * 100) / 100;
                        $down = ($close - $low) * 100 / $close;
                        $down = floor($down * 100) / 100;

                        $close4H = $candle4H[$symbol][1]->{CANDLE_4H_CLOSE};
                        $change = ($close - $close4H) * 100 / $close;
                        $change = floor($change * 100) / 100;

                        $addData4H[$symbol] = [
                            'close' => $close,
                            'low' => $low,
                            'high' => $high,
                            'up' => $up,
                            'down' => $down,
                            'rsi_0' => $candle4H[$symbol][0]->{CANDLE_4H_RSI14},
                            'rsi_1' => $candle4H[$symbol][1]->{CANDLE_4H_RSI14},
                            'rsi_ema9' => $candle4H[$symbol][0]->{CANDLE_4H_RSI_EMA9},

                            'rsi_wma_45' =>  $candle4H[$symbol][0]->{CANDLE_4H_RSI_WMA},
                            'signal' =>  $candle4H[$symbol][0]->{CANDLE_4H_SIGNAL},
                        ];
                    }
                }


                foreach ($data1H as $data) {
                    $symbol = $data->{CANDLE_1H_SYMBOL};
                    if (!isset($candle1H[$symbol])) $candle1H[$symbol] = [];
                    $candle1H[$symbol][] = $data;
                    if (count($candle1H[$symbol]) == 2) {

                        $close = $candle1H[$symbol][0]->{CANDLE_1H_CLOSE};
                        $low = $candle1H[$symbol][1]->{CANDLE_1H_LOW};
                        $high = $candle1H[$symbol][1]->{CANDLE_1H_HIGH};

                        $up = ($close - $high) * 100 / $high;
                        $up = floor($up * 100) / 100;
                        $down = ($close - $low) * 100 / $low;
                        $down = floor($down * 100) / 100;

                        $addData1H[$symbol] = [
                            'close' => $close,
                            'low' => $low,
                            'high' => $high,
                            'up' => $up,
                            'down' => $down,
                            'rsi_0' => $candle1H[$symbol][0]->{CANDLE_1H_RSI14},
                            'rsi_1' => $candle1H[$symbol][1]->{CANDLE_1H_RSI14},
                        ];
                    }
                }

                foreach ($data15M as $data) {
                    $symbol = $data->{CANDLE_15M_SYMBOL};
                    if (!isset($candle15M[$symbol])) $candle15M[$symbol] = [];
                    $candle15M[$symbol][] = $data;
                    if (count($candle15M[$symbol]) == 2) {

                        $close = $candle15M[$symbol][0]->{CANDLE_15M_CLOSE};
                        $low = $candle15M[$symbol][1]->{CANDLE_15M_LOW};
                        $high = $candle15M[$symbol][1]->{CANDLE_15M_HIGH};

                        $up = ($close - $high) * 100 / $high;
                        $up = floor($up * 100) / 100;
                        $down = ($close - $low) * 100 / $low;
                        $down = floor($down * 100) / 100;

                        $addData15M[$symbol] = [
                            'close' => $close,
                            'low' => $low,
                            'high' => $high,
                            'up' => $up,
                            'down' => $down,
                            'rsi_0' => $candle15M[$symbol][0]->{CANDLE_15M_RSI14},
                            'rsi_1' => $candle15M[$symbol][1]->{CANDLE_15M_RSI14},
                        ];
                    }
                }

                foreach ($data3M as $data) {
                    $symbol = $data->{CANDLE_3M_SYMBOL};
                    if (!isset($candle3M[$symbol])) $candle3M[$symbol] = [];
                    $candle3M[$symbol][] = $data;
                    if (count($candle3M[$symbol]) == 2) {

                        $close = $candle3M[$symbol][0]->{CANDLE_3M_CLOSE};
                        $low = $candle3M[$symbol][1]->{CANDLE_3M_LOW};
                        $high = $candle3M[$symbol][1]->{CANDLE_3M_HIGH};

                        $up = ($close - $high) * 100 / $high;
                        $up = floor($up * 100) / 100;
                        $down = ($close - $low) * 100 / $low;
                        $down = floor($down * 100) / 100;

                        $addData3M[$symbol] = [
                            'close' => $close,
                            'low' => $low,
                            'high' => $high,
                            'up' => $up,
                            'down' => $down,
                            'rsi_0' => $candle3M[$symbol][0]->{CANDLE_3M_RSI14},
                            'rsi_1' => $candle3M[$symbol][1]->{CANDLE_3M_RSI14},
                        ];
                    }
                }

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


                            'signal' => $candle1D[$symbol][0]->{CANDLE_1D_SIGNAL},
                        ];
                    }
                }

                foreach ($data1W as $data) {
                    $symbol = $data->{CANDLE_1W_SYMBOL};
                    if (!isset($candle1W[$symbol])) $candle1W[$symbol] = [];
                    $candle1W[$symbol][] = $data;
                    if (count($candle1W[$symbol]) == 1) {
                        $addData1W[$symbol] = [
                            'rsi_wma' => $candle1W[$symbol][0]->{CANDLE_1W_RSI_WMA},
                        ];
                    }
                }


                $addData = [];
                $symbolData = [];
                foreach ($coins as $key => $coin) {

                    $symbol = $coin->{WL_SYMBOL};
                    $data = [
                        ORDER_TRACK_ID => $key,
                        ORDER_TRACK_SYMBOL => $coin->{WL_SYMBOL},
                        ORDER_TRACK_PRICE => isset($addData4H[$symbol]) ? $addData4H[$symbol]['close'] : null,
                        ORDER_TRACK_LOW => isset($addData4H[$symbol]) ? $addData4H[$symbol]['low'] : null,
                        ORDER_TRACK_HIGH => isset($addData4H[$symbol]) ? $addData4H[$symbol]['high'] : null,
                        ORDER_TRACK_UP => isset($addData4H[$symbol]) ? $addData4H[$symbol]['up'] : null,
                        ORDER_TRACK_DOWN => isset($addData4H[$symbol]) ? $addData4H[$symbol]['down'] : null,
                        ORDER_TRACK_CLOSE => isset($addData4H[$symbol]) ? $addData4H[$symbol]['close'] : null,
                        ORDER_TRACK_RSI4H_0 => isset($addData4H[$symbol]) ? $addData4H[$symbol]['rsi_0'] : null,
                        ORDER_TRACK_RSI4H_1 => isset($addData4H[$symbol]) ? $addData4H[$symbol]['rsi_1'] : null,
                        ORDER_TRACK_RSI1H_0 => isset($addData1H[$symbol]) ? $addData1H[$symbol]['rsi_0'] : null,
                        ORDER_TRACK_RSI1H_1 => isset($addData1H[$symbol]) ? $addData1H[$symbol]['rsi_1'] : null,
                        ORDER_TRACK_RSI_EMA9 => isset($addData4H[$symbol]) ? $addData4H[$symbol]['rsi_ema9'] : null,
                        ORDER_TRACK_1H_UP => isset($addData1H[$symbol]) ? $addData1H[$symbol]['up'] : null,
                        ORDER_TRACK_1H_DOWN => isset($addData1H[$symbol]) ? $addData1H[$symbol]['down'] : null,
                        ORDER_TRACK_15M_UP => isset($addData15M[$symbol]) ? $addData15M[$symbol]['up'] : null,
                        ORDER_TRACK_15M_DOWN => isset($addData15M[$symbol]) ? $addData15M[$symbol]['down'] : null,
                        ORDER_TRACK_3M_UP => isset($addData3M[$symbol]) ? $addData3M[$symbol]['up'] : null,
                        ORDER_TRACK_3M_DOWN => isset($addData3M[$symbol]) ? $addData3M[$symbol]['down'] : null,
                        ORDER_TRACK_1D_RSI_WMA => isset($addData1D[$symbol]) ? $addData1D[$symbol]['rsi_wma'] : null,
                        ORDER_TRACK_1W_RSI_WMA => isset($addData1W[$symbol]) ? $addData1W[$symbol]['rsi_wma'] : null,
                        ORDER_TRACK_1D_UP => isset($addData1D[$symbol]) ? $addData1D[$symbol]['up'] : null,
                        ORDER_TRACK_1D_DOWN => isset($addData1D[$symbol]) ? $addData1D[$symbol]['down'] : null,
                    ];


                    $addData[] = $data;

                    $extraData = array_merge(array(), $data); 
                    $extraData[CANDLE_4H_RSI_WMA] =  isset($addData4H[$symbol]) ? $addData4H[$symbol]['rsi_wma_45'] : null;
                    $extraData[CANDLE_4H_SIGNAL] =  isset($addData4H[$symbol]) ? $addData4H[$symbol]['signal'] : null;
                    $extraData[CANDLE_1D_SIGNAL] =  isset($addData1D[$symbol]) ? $addData1D[$symbol]['signal'] : null;
                    // $symbolData[$symbol] = $data;
                    $symbolData[$symbol] = $extraData;
                }

                foreach ($coins as $key => $coin) {
                    $this->checkAlarm($symbolData, $coin->{WL_SYMBOL});
                }

                // print_r($addData);

                $trackModel->drop('All');
                $trackModel->add($addData);

                // echo "Finish after " . (round(microtime(true) * 1000) - $time) . "ms\n";

            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }


    private function checkAlarm($data, $symbol)
    {

        foreach ($this->alarmCfg as $alarm) {
            if (isset($alarm['active']) && $alarm['active'] == 0) continue;
            $id = $symbol . "_" . $alarm['id'];
            $checkResult = $this->checkCondition($data, $alarm['condition'], $symbol);
            if ($checkResult === null) continue;
            if ($checkResult) {
                if (isset($this->alarmResult[$id]) && $this->alarmResult[$id] === false) {
                    $this->makeAlert($alarm, $symbol);
                }
                $this->alarmResult[$id] = true;
            } else {
                $this->alarmResult[$id] = false;
            }
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
        echo "\n[" . $symbol . "] " . $content;
        Telegram::send($icon . " [" . $symbol . "] " . $content, $groupId, $botId);
    }
}

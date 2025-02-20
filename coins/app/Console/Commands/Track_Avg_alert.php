<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;

class Track_Avg_alert extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * Service name: volatility_alert
     */
    protected $signature = 'track_avg_alert';

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


            $this->alarmCfg = Ctrl::get('track_avg_alter', null);
            $this->alarmCfg = json_decode($this->alarmCfg, true);
            if ($this->alarmCfg == null) $this->alarmCfg = [];

            $this->alarmResult = [];

            $this->Frame = [
                '1D-3D' => [
                    'Model' => Models::get('Crawler/Candle_1d'),
                    'CloseTime' => CANDLE_1D_CLOSE_TIME,
                    'Time' => 3,
                    'timeInterval' => 86400 * 1000,
                    'Symbol' => CANDLE_1D_SYMBOL,
                    'High' => CANDLE_1D_HIGH,
                    'Low' => CANDLE_1D_LOW,
                    'Close' => CANDLE_1D_CLOSE,

                ],
                '4H-3D' => [
                    'Model' => Models::get('Crawler/Candle_4h'),
                    'CloseTime' => CANDLE_4H_CLOSE_TIME,
                    'Time' => 3,
                    'timeInterval' => 4 * 3600 * 1000,
                    'Symbol' => CANDLE_4H_SYMBOL,
                    'High' => CANDLE_4H_HIGH,
                    'Low' => CANDLE_4H_LOW,
                    'Close' => CANDLE_4H_CLOSE,

                ],
                '1D-7D' => [
                    'Model' => Models::get('Crawler/Candle_1d'),
                    'CloseTime' => CANDLE_1D_CLOSE_TIME,
                    'Time' => 7,
                    'timeInterval' => 86400 * 1000,
                    'Symbol' => CANDLE_1D_SYMBOL,
                    'High' => CANDLE_1D_HIGH,
                    'Low' => CANDLE_1D_LOW,
                    'Close' => CANDLE_1D_CLOSE,

                ],
                '4H-7D' => [
                    'Model' => Models::get('Crawler/Candle_4h'),
                    'CloseTime' => CANDLE_4H_CLOSE_TIME,
                    'Time' => 7,
                    'timeInterval' => 4 * 3600 * 1000,
                    'Symbol' => CANDLE_4H_SYMBOL,
                    'High' => CANDLE_4H_HIGH,
                    'Low' => CANDLE_4H_LOW,
                    'Close' => CANDLE_4H_CLOSE,

                ],
            ];

            $wlModel = Models::get('Admin/Watchlist');
            $volatilityModel = Models::get('Admin/Volatility');
            $volatilityTModel = Models::get('Admin/Volatility_history');

            while (true) {



                $startTime = round(microtime(true) * 1000);

                $data = $wlModel->read();
                if (!$data['result']) return $data;

                $data = $data['data'];

                $result = [];

                foreach ($this->Frame as $key => $row) {
                    $result[$key] =  $this->CalAvg($key);
                }

                $volatilityData = [];
                $volatilityTdata = [];
                foreach ($data as $row) {
                    $symbol = $row->{WL_SYMBOL};
                    $rowData = [
                        VOLATILITY_SYMBOL => $symbol,
                        VOLATILITY_TIME => round(microtime(true) * 1000),
                        VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE => null,
                        VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE => null,
                        VOLATILITY_1D_LOW_LOW_AVG3D_VALUE => null,
                        VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE => null,
                        VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE => null,
                        VOLATILITY_1D_LOW_LOW_AVG7D_VALUE => null,
                        VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE => null,
                        VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE => null,
                        VOLATILITY_4H_LOW_LOW_AVG3D_VALUE => null,
                        VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE => null,
                        VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE => null,
                        VOLATILITY_4H_LOW_LOW_AVG7D_VALUE => null,
                        VOLATILITY_1D_HIGH_LOW_AVG3D_RANK => null,
                        VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK => null,
                        VOLATILITY_1D_LOW_LOW_AVG3D_RANK => null,
                        VOLATILITY_1D_HIGH_LOW_AVG7D_RANK => null,
                        VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK => null,
                        VOLATILITY_1D_LOW_LOW_AVG7D_RANK => null,
                        VOLATILITY_4H_HIGH_LOW_AVG3D_RANK => null,
                        VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK => null,
                        VOLATILITY_4H_LOW_LOW_AVG3D_RANK => null,
                        VOLATILITY_4H_HIGH_LOW_AVG7D_RANK => null,
                        VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK => null,
                        VOLATILITY_4H_LOW_LOW_AVG7D_RANK => null,

                        VOLATILITY_4H_CLOSE_LOW_AVG3D_VALUE => null,
                        VOLATILITY_4H_CLOSE_LOW_AVG7D_VALUE => null,
                        VOLATILITY_1D_CLOSE_LOW_AVG3D_VALUE => null,
                        VOLATILITY_1D_CLOSE_LOW_AVG7D_VALUE => null,
                        VOLATILITY_4H_CLOSE_LOW_AVG3D_RANK => null,
                        VOLATILITY_4H_CLOSE_LOW_AVG7D_RANK => null,
                        VOLATILITY_1D_CLOSE_LOW_AVG3D_RANK => null,
                        VOLATILITY_1D_CLOSE_LOW_AVG7D_RANK => null,
                    ];

                    $tdata = [
                        VOLATILITY_SYMBOL => $symbol,
                        VOLATILITY_TIME => round(microtime(true) * 1000),
                        VOLATILITY_4H_HIGHLOW_T0_VALUE => null,
                        VOLATILITY_4H_HIGHLOW_T1_VALUE => null,
                        VOLATILITY_4H_HIGHLOW_T2_VALUE => null,
                        VOLATILITY_4H_HIGHHIGH_T0_VALUE => null,
                        VOLATILITY_4H_HIGHHIGH_T1_VALUE => null,
                        VOLATILITY_4H_HIGHHIGH_T2_VALUE => null,
                        VOLATILITY_1D_HIGHLOW_T0_VALUE => null,
                        VOLATILITY_1D_HIGHLOW_T1_VALUE => null,
                        VOLATILITY_1D_HIGHLOW_T2_VALUE => null,
                        VOLATILITY_1D_HIGHHIGH_T0_VALUE => null,
                        VOLATILITY_1D_HIGHHIGH_T1_VALUE => null,
                        VOLATILITY_1D_HIGHHIGH_T2_VALUE => null,
                        VOLATILITY_4H_HIGHLOW_T0_RANK => null,
                        VOLATILITY_4H_HIGHLOW_T1_RANK => null,
                        VOLATILITY_4H_HIGHLOW_T2_RANK => null,
                        VOLATILITY_4H_HIGHHIGH_T0_RANK => null,
                        VOLATILITY_4H_HIGHHIGH_T1_RANK => null,
                        VOLATILITY_4H_HIGHHIGH_T2_RANK => null,
                        VOLATILITY_1D_HIGHLOW_T0_RANK => null,
                        VOLATILITY_1D_HIGHLOW_T1_RANK => null,
                        VOLATILITY_1D_HIGHLOW_T2_RANK => null,
                        VOLATILITY_1D_HIGHHIGH_T0_RANK => null,
                        VOLATILITY_1D_HIGHHIGH_T1_RANK => null,
                        VOLATILITY_1D_HIGHHIGH_T2_RANK => null,
                    ];

                    if (isset($result['1D-3D'][$symbol])) {
                        $rowData[VOLATILITY_1D_LOW_LOW_AVG3D_VALUE] = $result['1D-3D'][$symbol]['lowlowval'];
                        $rowData[VOLATILITY_1D_LOW_LOW_AVG3D_RANK] = $result['1D-3D'][$symbol]['lowlowrank'];
                        $rowData[VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE] = $result['1D-3D'][$symbol]['highhighval'];
                        $rowData[VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK] = $result['1D-3D'][$symbol]['highhighrank'];
                        $rowData[VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE] = $result['1D-3D'][$symbol]['highlowval'];
                        $rowData[VOLATILITY_1D_HIGH_LOW_AVG3D_RANK] = $result['1D-3D'][$symbol]['highlowrank'];
                        $rowData[VOLATILITY_1D_CLOSE_LOW_AVG3D_VALUE] = $result['1D-3D'][$symbol]['closelowval'];
                        $rowData[VOLATILITY_1D_CLOSE_LOW_AVG3D_RANK] = $result['1D-3D'][$symbol]['closelowrank'];

                        $tdata[VOLATILITY_1D_HIGHLOW_T0_VALUE] = $result['1D-3D'][$symbol]['highlowt0'];
                        $tdata[VOLATILITY_1D_HIGHLOW_T1_VALUE] = $result['1D-3D'][$symbol]['highlowt1'];
                        $tdata[VOLATILITY_1D_HIGHLOW_T2_VALUE] = $result['1D-3D'][$symbol]['highlowt2'];
                        $tdata[VOLATILITY_1D_HIGHHIGH_T0_VALUE] = $result['1D-3D'][$symbol]['highhight0'];
                        $tdata[VOLATILITY_1D_HIGHHIGH_T1_VALUE] = $result['1D-3D'][$symbol]['highhight1'];
                        $tdata[VOLATILITY_1D_HIGHHIGH_T2_VALUE] = $result['1D-3D'][$symbol]['highhight2'];

                        $tdata[VOLATILITY_1D_HIGHLOW_T0_RANK] = $result['1D-3D'][$symbol]['highlowt0rank'];
                        $tdata[VOLATILITY_1D_HIGHLOW_T1_RANK] = $result['1D-3D'][$symbol]['highlowt1rank'];
                        $tdata[VOLATILITY_1D_HIGHLOW_T2_RANK] = $result['1D-3D'][$symbol]['highlowt2rank'];
                        $tdata[VOLATILITY_1D_HIGHHIGH_T0_RANK] = $result['1D-3D'][$symbol]['highhight0rank'];
                        $tdata[VOLATILITY_1D_HIGHHIGH_T1_RANK] = $result['1D-3D'][$symbol]['highhight1rank'];
                        $tdata[VOLATILITY_1D_HIGHHIGH_T2_RANK] = $result['1D-3D'][$symbol]['highhight2rank'];
                    }

                    if (isset($result['4H-3D'][$symbol])) {
                        $rowData[VOLATILITY_4H_LOW_LOW_AVG3D_VALUE] = $result['4H-3D'][$symbol]['lowlowval'];
                        $rowData[VOLATILITY_4H_LOW_LOW_AVG3D_RANK] = $result['4H-3D'][$symbol]['lowlowrank'];
                        $rowData[VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE] = $result['4H-3D'][$symbol]['highhighval'];
                        $rowData[VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK] = $result['4H-3D'][$symbol]['highhighrank'];
                        $rowData[VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE] = $result['4H-3D'][$symbol]['highlowval'];
                        $rowData[VOLATILITY_4H_HIGH_LOW_AVG3D_RANK] = $result['4H-3D'][$symbol]['highlowrank'];
                        $rowData[VOLATILITY_4H_CLOSE_LOW_AVG3D_VALUE] = $result['4H-3D'][$symbol]['closelowval'];
                        $rowData[VOLATILITY_4H_CLOSE_LOW_AVG3D_RANK] = $result['4H-3D'][$symbol]['closelowrank'];

                        $tdata[VOLATILITY_4H_HIGHLOW_T0_VALUE] = $result['4H-3D'][$symbol]['highlowt0'];
                        $tdata[VOLATILITY_4H_HIGHLOW_T1_VALUE] = $result['4H-3D'][$symbol]['highlowt1'];
                        $tdata[VOLATILITY_4H_HIGHLOW_T2_VALUE] = $result['4H-3D'][$symbol]['highlowt2'];
                        $tdata[VOLATILITY_4H_HIGHHIGH_T0_VALUE] = $result['4H-3D'][$symbol]['highhight0'];
                        $tdata[VOLATILITY_4H_HIGHHIGH_T1_VALUE] = $result['4H-3D'][$symbol]['highhight1'];
                        $tdata[VOLATILITY_4H_HIGHHIGH_T2_VALUE] = $result['4H-3D'][$symbol]['highhight2'];

                        $tdata[VOLATILITY_4H_HIGHLOW_T0_RANK] = $result['4H-3D'][$symbol]['highlowt0rank'];
                        $tdata[VOLATILITY_4H_HIGHLOW_T1_RANK] = $result['4H-3D'][$symbol]['highlowt1rank'];
                        $tdata[VOLATILITY_4H_HIGHLOW_T2_RANK] = $result['4H-3D'][$symbol]['highlowt2rank'];
                        $tdata[VOLATILITY_4H_HIGHHIGH_T0_RANK] = $result['4H-3D'][$symbol]['highhight0rank'];
                        $tdata[VOLATILITY_4H_HIGHHIGH_T1_RANK] = $result['4H-3D'][$symbol]['highhight1rank'];
                        $tdata[VOLATILITY_4H_HIGHHIGH_T2_RANK] = $result['4H-3D'][$symbol]['highhight2rank'];
                    }

                    if (isset($result['1D-7D'][$symbol])) {
                        $rowData[VOLATILITY_1D_LOW_LOW_AVG7D_VALUE] = $result['1D-7D'][$symbol]['lowlowval'];
                        $rowData[VOLATILITY_1D_LOW_LOW_AVG7D_RANK] = $result['1D-7D'][$symbol]['lowlowrank'];
                        $rowData[VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE] = $result['1D-7D'][$symbol]['highhighval'];
                        $rowData[VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK] = $result['1D-7D'][$symbol]['highhighrank'];
                        $rowData[VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE] = $result['1D-7D'][$symbol]['highlowval'];
                        $rowData[VOLATILITY_1D_HIGH_LOW_AVG7D_RANK] = $result['1D-7D'][$symbol]['highlowrank'];
                        $rowData[VOLATILITY_1D_CLOSE_LOW_AVG7D_VALUE] = $result['1D-7D'][$symbol]['closelowval'];
                        $rowData[VOLATILITY_1D_CLOSE_LOW_AVG7D_RANK] = $result['1D-7D'][$symbol]['closelowrank'];
                    }

                    if (isset($result['4H-7D'][$symbol])) {
                        $rowData[VOLATILITY_4H_LOW_LOW_AVG7D_VALUE] = $result['4H-7D'][$symbol]['lowlowval'];
                        $rowData[VOLATILITY_4H_LOW_LOW_AVG7D_RANK] = $result['4H-7D'][$symbol]['lowlowrank'];
                        $rowData[VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE] = $result['4H-7D'][$symbol]['highhighval'];
                        $rowData[VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK] = $result['4H-7D'][$symbol]['highhighrank'];
                        $rowData[VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE] = $result['4H-7D'][$symbol]['highlowval'];
                        $rowData[VOLATILITY_4H_HIGH_LOW_AVG7D_RANK] = $result['4H-7D'][$symbol]['highlowrank'];
                        $rowData[VOLATILITY_4H_CLOSE_LOW_AVG7D_VALUE] = $result['4H-7D'][$symbol]['closelowval'];
                        $rowData[VOLATILITY_4H_CLOSE_LOW_AVG7D_RANK] = $result['4H-7D'][$symbol]['closelowrank'];
                    }


                    $volatilityData[] = $rowData;
                    $volatilityTdata[] = $tdata;
                }

                $volatilityModel->drop('All');
                $volatilityModel->add($volatilityData);

                $volatilityTModel->drop('All');
                $volatilityTModel->add($volatilityTdata);

                foreach ($volatilityData as $rowData) {
                    $this->checkAlarm($rowData, $rowData[VOLATILITY_SYMBOL]);
                }



                echo "Execute time " . ($startTime - round(microtime(true) * 1000)) . "ms\n";

                sleep(300);
            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }


    private function CalAvg($key)
    {
        $Config = $this->Frame[$key];
        $model = $Config['Model'];

        $time = floor(microtime(true) / 86400) * 86400 * 1000;

        //Get candle data off all symbol sort by close time
        $data_Candle = $model->read([[[$Config['CloseTime'], '>',  $time - $Config['Time'] * 86400 * 1000 - $Config['timeInterval']]]], function ($db) use ($Config) {
            $db->orderBy($Config['CloseTime'], 'ASC');
        });

        if (!$data_Candle['result']) return $data_Candle;
        $data_Candle = $data_Candle['data'];

        $arrayData = [];

        //split candle data to group by symbol
        foreach ($data_Candle as $row) {
            $arrayData[$row->{$Config['Symbol']}][] = $row;
        }

        $result = [];

        //Save data for sorting
        $highlowData = [];
        $highhighData = [];
        $lowlowData = [];
        $closelowData = [];


        $highlowt0Data = [];
        $highlowt1Data = [];
        $highlowt2Data = [];
        $highhight0Data = [];
        $highhight1Data = [];
        $highhight2Data = [];

        // calculate avg data for each group.
        foreach ($arrayData as $sym => $row) {

            $highlowval = 0;
            $count = 0;

            $lowlowsum = 0;
            $lowlowcount = 0;

            $highhighsum = 0;
            $highhighcount = 0;

            $closelowsum = 0;
            $closelowcount = 0;

            for ($i = 0; $i < count($row); $i++) {
                if ($i != 0) {

                    $highlowval += (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $count++;

                    $lowlowval = (($row[$i]->{$Config['Low']} - $row[$i - 1]->{$Config['Low']}) * 100) / $row[$i]->{$Config['Low']};

                    if ($lowlowval < -1) {
                        $lowlowsum += $lowlowval;
                        $lowlowcount++;
                    }

                    $highhighval = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};

                    if ($highhighval > 0) {
                        $highhighsum += $highhighval;
                        $highhighcount++;
                    }

                    $closelowval = (($row[$i]->{$Config['Low']} - $row[$i - 1]->{$Config['Close']}) * 100) / $row[$i - 1]->{$Config['Close']};

                    if ($closelowval < -1) {
                        $closelowsum += $closelowval;
                        $closelowcount++;
                    }
                }
            }

            if ($count > 0) $highlowval = $highlowval / $count;
            if ($lowlowcount > 0) $lowlowsum = $lowlowsum / $lowlowcount;
            if ($closelowcount > 0) $closelowsum = $closelowsum / $closelowcount;
            if ($highhighcount > 0) $highhighsum = $highhighsum / $highhighcount;

            $result[$sym] = [
                'highlowval' => round($highlowval, 2),
                'lowlowval' => round($lowlowsum, 2),
                'closelowval' => round($closelowsum, 2),
                'highhighval' =>  round($highhighsum, 2),
            ];

            if ($key == '1D-3D') {
                $length = count($row);
                $i = $length - 1;
                if (isset($row[$i - 1])) {
                    $highlow1dt0 = (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $highhigh1dt0 = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};
                } else {
                    $highlow1dt0 = 0;
                    $highhigh1dt0 = 0;
                }

                $i = $length - 2;
                if (isset($row[$i - 1])) {
                    $highlow1dt1 = (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $highhigh1dt1 = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};
                } else {
                    $highlow1dt1 = 0;
                    $highhigh1dt1 = 0;
                }

                $i = $length - 3;
                if (isset($row[$i - 1])) {
                    $highlow1dt2 = (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $highhigh1dt2 = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};
                } else {
                    $highlow1dt2 = 0;
                    $highhigh1dt2 = 0;
                }

                $result[$sym]['highlowt0'] = round($highlow1dt0, 2);
                $result[$sym]['highhight0'] = round($highhigh1dt0, 2);
                $result[$sym]['highlowt1'] = round($highlow1dt1, 2);
                $result[$sym]['highhight1'] = round($highhigh1dt1, 2);
                $result[$sym]['highlowt2'] = round($highlow1dt2, 2);
                $result[$sym]['highhight2'] = round($highhigh1dt2, 2);

                $highlowt0Data[$sym] = $highlow1dt0;
                $highlowt1Data[$sym] = $highlow1dt1;
                $highlowt2Data[$sym] = $highlow1dt2;

                $highhight0Data[$sym] = $highhigh1dt0;
                $highhight1Data[$sym] = $highhigh1dt1;
                $highhight2Data[$sym] = $highhigh1dt2;
            }

            if ($key == '4H-3D') {

                $length = count($row);
                $i = $length - 1;

                $highlow4ht0 = 0;
                $highhigh4ht0 = 0;
                $highlow4ht1  = 0;
                $highhigh4ht1 = 0;
                $highlow4ht2 = 0;
                $highhigh4ht2 = 0;

                if (isset($row[$i - 1])) {
                    $highlow4ht0 = (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $highhigh4ht0 = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};
                }
                $i = $length - 2;
                if (isset($row[$i - 1])) {
                    $highlow4ht1 = (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $highhigh4ht1 = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};
                }
                $i = $length - 3;
                if (isset($row[$i - 1])) {
                    $highlow4ht2 = (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['High']};
                    $highhigh4ht2 = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};
                }

                $result[$sym]['highlowt0'] = round($highlow4ht0, 2);
                $result[$sym]['highhight0'] = round($highhigh4ht0, 2);
                $result[$sym]['highlowt1'] = round($highlow4ht1, 2);
                $result[$sym]['highhight1'] = round($highhigh4ht1, 2);
                $result[$sym]['highlowt2'] = round($highlow4ht2, 2);
                $result[$sym]['highhight2'] = round($highhigh4ht2, 2);

                $highlowt0Data[$sym] = $highlow4ht0;
                $highlowt1Data[$sym] = $highlow4ht1;
                $highlowt2Data[$sym] = $highlow4ht2;

                $highhight0Data[$sym] = $highhigh4ht0;
                $highhight1Data[$sym] = $highhigh4ht1;
                $highhight2Data[$sym] = $highhigh4ht2;
            }

            $highlowData[$sym] = $highlowval;
            $highhighData[$sym] = $highhighsum;
            $lowlowData[$sym] = $lowlowsum;
            $closelowData[$sym] = $closelowsum;
        }

        // calculate rank for avg data
        arsort($highlowData);
        arsort($highhighData);
        arsort($lowlowData);
        arsort($closelowData);

        $rank = 0;
        foreach ($highlowData as $sym => $val) {
            $rank++;
            $result[$sym]['highlowrank'] = $rank;
        }
        $rank = 0;
        foreach ($highhighData as $sym => $val) {
            $rank++;
            $result[$sym]['highhighrank'] = $rank;
        }
        $rank = 0;
        foreach ($lowlowData as $sym => $val) {
            $rank++;
            $result[$sym]['lowlowrank'] = $rank;
        }
        $rank = 0;
        foreach ($closelowData as $sym => $val) {
            $rank++;
            $result[$sym]['closelowrank'] = $rank;
        }

        if ($key == '4H-3D' || $key == '1D-3D') {
            // calculate rank for t data
            arsort($highlowt0Data);
            arsort($highlowt1Data);
            arsort($highlowt2Data);

            $rank = 0;
            foreach ($highlowt0Data as $sym => $val) {
                $rank++;
                $result[$sym]['highlowt0rank'] = $rank;
            }
            $rank = 0;
            foreach ($highlowt1Data as $sym => $val) {
                $rank++;
                $result[$sym]['highlowt1rank'] = $rank;
            }
            $rank = 0;
            foreach ($highlowt2Data as $sym => $val) {
                $rank++;
                $result[$sym]['highlowt2rank'] = $rank;
            }

            arsort($highhight0Data);
            arsort($highhight1Data);
            arsort($highhight2Data);

            $rank = 0;
            foreach ($highhight0Data as $sym => $val) {
                $rank++;
                $result[$sym]['highhight0rank'] = $rank;
            }
            $rank = 0;
            foreach ($highhight1Data as $sym => $val) {
                $rank++;
                $result[$sym]['highhight1rank'] = $rank;
            }
            $rank = 0;
            foreach ($highhight2Data as $sym => $val) {
                $rank++;
                $result[$sym]['highhight2rank'] = $rank;
            }
        }



        return $result;
    }



    private function checkAlarm($data, $symbol)
    {

        foreach ($this->alarmCfg as $alarm) {
            if (isset($alarm['active']) && $alarm['active'] == 0) continue;
            $id = $symbol . "_" . $alarm['id'];
            $checkResult = $this->checkCondition($data, $alarm['condition']);
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

    private function checkCondition($data, $condition)
    {
        $result = true;
        foreach ($condition as $con) {
            $compareResult = $this->compare($data, $con);
            if ($compareResult === null) return null;
            if (!$compareResult) {
                $result = false;
                break;
            }
        }
        return $result;
    }

    private function compare($data, $condition)
    {


        $com1 = $this->calCom1($data, $condition);
        $logic = $condition['logic'];
        $com2 = $condition['value'];

        if ($com1 === null || $com2 === null) return null;

        if ($logic == '=') return $com1 == $com2;
        if ($logic == '>') return $com1 > $com2;
        if ($logic == '<') return $com1 < $com2;
        if ($logic == '>=') return $com1 >= $com2;
        if ($logic == '<=') return $com1 <= $com2;
    }


    private function calCom1($data, $condition)
    {

        $volatility = get($condition['volatility'], '');
        $frame = get($condition['frame'], '');
        $object = get($condition['object'], '');
        $avg = get($condition['avg']);

        $colName = 'volatility_' . $frame . "_" . $volatility . "_avg" . $avg . "_" . $object;

        if (isset($data[$colName])) {
            return doubleval($data[$colName]);
        } else {
            return null;
        }
    }

    private function makeAlert($alarm, $symbol)
    {
        $icon = $alarm['icon'];
        $content = $alarm['content'];
        $botId = $alarm['bot'];
        $groupId = $alarm['group'];
        echo "\n[" . $symbol . "] " . $content;
        $message = $icon . " [" . $symbol . "] " . $content;
        Ctrl::set('volatility_alert_message', $message);
        Telegram::send($icon . " [" . $symbol . "] " . $content, $groupId, $botId);
    }
}

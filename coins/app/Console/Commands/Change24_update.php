<?php

namespace App\Console\Commands;

use App\Crawler\Caculator\Change24\AltsUpEma;
use App\Crawler\Caculator\Change24\AltsUpEma50;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;


class Change24_update extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'change24_update';

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
        set_time_limit(0);


        $this->update();
    }


    private function update()
    {

        try {
            $time = floor(time() / 60) * 60 * 1000;

            $this->change24Model = Models::get('Admin/Change_24h');

            $result = Query::make('https://api.binance.com/api/v3/ticker/24hr', 'get', null, ['dataType' => 'json']);
            if (!$result) return;



            $asc = 0;
            $desc = 0;
            $keep = 0;
            $ascBTC = 0;
            $descBTC = 0;
            $keepBTC = 0;
            $asc10 = 0;
            $asc7_10 = 0;
            $asc5_7 = 0;
            $asc3_5 = 0;
            $asc0_3 = 0;
            $desc0_3 = 0;
            $desc3_5 = 0;
            $desc5_7 = 0;
            $desc7_10 = 0;
            $desc10 = 0;

            $up5m = 0;
            $up15m = 0;
            $up1h = 0;
            $up4h = 0;
            $down5m = 0;
            $down15m = 0;
            $down1h = 0;
            $down4h = 0;

            $top50U = 0;
            $top50D = 0;
            $top50K = 0;

            $usdtData = [];

            $usdtDatas = [];

            $btc = null;

            $top50 = [
                'BTCUSDT',
                'ETHUSDT',
                'BNBUSDT',
                'ADAUSDT',
                'SOLUSDT',
                'XRPUSDT',
                'DOTUSDT',
                'DOGEUSDT',
                'LUNAUSDT',
                'AVAUSDT',
                'WBTCUSDT',
                'UNIUSDT',
                'LTCUSDT',
                'LINKUSDT',
                'BCHUSDT',
                'ALGOUSDT',
                'XLMUSDT',
                'SHIBUSDT',
                'VETUSDT',
                'ICPUSDT',
                'ATOMUSDT',
                'FTTUSDT',
                'AXSUSDT',
                'ETCUSDT',
                'TRXUSDT',
                'BTCBUSDT',
                'DAIUSDT',
                'THETAUSDT',
                'XTZUSDT',
                'FTMUSDT',
                'HBARUSDT',
                'EGLDUSDT',
                'XMRUSDT',
                'CROUSDT',
                'NEARUSDT',
                'CAKEUSDT',
                'EOSUSDT',
                'GRTUSDT',
                'FLOWUSDT',
                'AAVEUSDT',
                'KLAYUSDT',
                'MIOTAUSDT',
                'XECUSDT',
                'QUNTUSDT',
                'BSVUSDT',
                'NEOUSDT',
                'LEOUSDT',
                'KSMUSDT',
                'WAVESUSDT',
                'STXUSDT',
            ];

            $top50Data = [];

            foreach ($result as $data) {
                if (strpos($data['symbol'], 'USDT') === false) continue;
                if ($data['symbol'] == 'BTCUSDT') {
                    $btc = $data;
                }
                $usdtData[] = $data;
                $usdtDatas[$data['symbol']] = $data;
                if (in_array($data['symbol'], $top50)) {
                    $top50Data[] = $data;
                }
            }
            if (!$btc) return;

            $btcChange = doubleval($btc['priceChangePercent']);
            $total = count($usdtData);
            $total50 = count($top50Data);

            if ($total50 != 50) echo "Can not get full top 50 \n";

            $old5mData = $this->getUsdtData('5m');
            $old15mData = $this->getUsdtData('15m');
            $old1hData = $this->getUsdtData('1h');
            $old4hData = $this->getUsdtData('4h');

            foreach ($usdtData as $data) {

                $symbol = $data['symbol'];

                $changePer = doubleval($data['priceChangePercent']);
                if ($changePer > 0) $asc++;
                if ($changePer < 0) $desc++;
                if ($changePer == 0) $keep++;

                if ($changePer > $btcChange) $ascBTC++;
                if ($changePer < $btcChange) $descBTC++;
                if ($changePer == $btcChange) $keepBTC++;

                if ($changePer < -10) $desc10++;
                if ($changePer >= -10 && $changePer < -7) $desc7_10++;
                if ($changePer >= -7 && $changePer < -5) $desc5_7++;
                if ($changePer >= -5 && $changePer < -3) $desc3_5++;
                if ($changePer >= -3 && $changePer < 0) $desc0_3++;
                if ($changePer > 0 && $changePer <= 3) $asc0_3++;
                if ($changePer > 3 && $changePer <= 5) $asc3_5++;
                if ($changePer > 5 && $changePer <= 7) $asc5_7++;
                if ($changePer > 7 && $changePer <= 10) $asc7_10++;
                if ($changePer > 10) $asc10++;

                if (isset($old5mData[$symbol])) {
                    if ($changePer > doubleval($old5mData[$symbol]['priceChangePercent'])) {
                        $up5m++;
                    } else if ($changePer < doubleval($old5mData[$symbol]['priceChangePercent'])) {
                        $down5m++;
                    }
                }
                if (isset($old15mData[$symbol])) {
                    if ($changePer > doubleval($old15mData[$symbol]['priceChangePercent'])) {
                        $up15m++;
                    } else if ($changePer < doubleval($old15mData[$symbol]['priceChangePercent'])) {
                        $down15m++;
                    }
                }
                if (isset($old1hData[$symbol])) {
                    if ($changePer > doubleval($old1hData[$symbol]['priceChangePercent'])) {
                        $up1h++;
                    } else if ($changePer < doubleval($old1hData[$symbol]['priceChangePercent'])) {
                        $down1h++;
                    }
                }
                if (isset($old4hData[$symbol])) {
                    if ($changePer > doubleval($old4hData[$symbol]['priceChangePercent'])) {
                        $up4h++;
                    } else if ($changePer < doubleval($old4hData[$symbol]['priceChangePercent'])) {
                        $down4h++;
                    }
                }
            }

            foreach ($top50Data as $data) {

                $symbol = $data['symbol'];
                $changePer = doubleval($data['priceChangePercent']);
                if ($changePer > 0) $top50U++;
                if ($changePer < 0) $top50D++;
                if ($changePer == 0) $top50K++;
            }

            $this->change24Model->add([[
                CHANGE24H_TIME => $time,
                CHANGE24H_TOTAL => $total,
                CHANGE24H_UP => round($asc * 10000 / $total) / 100,
                CHANGE24H_DOWN => round($desc * 10000 / $total) / 100,
                CHANGE24H_KEEP => round($keep * 10000 / $total) / 100,
                CHANGE24H_BTC_ASC => round($ascBTC * 10000 / $total) / 100,
                CHANGE24H_BTC_DESC => round($descBTC * 10000 / $total) / 100,
                CHANGE24H_BTC_KEEP => round($keepBTC * 10000 / $total) / 100,
                CHANGE24H_UP_10 => round($asc10 * 10000 / $total) / 100,
                CHANGE24H_UP_7_10 => round($asc7_10 * 10000 / $total) / 100,
                CHANGE24H_UP_5_7 => round($asc5_7 * 10000 / $total) / 100,
                CHANGE24H_UP_3_5 => round($asc3_5 * 10000 / $total) / 100,
                CHANGE24H_UP_0_3 => round($asc0_3 * 10000 / $total) / 100,
                CHANGE24H_DOWN_10 => round($desc10 * 10000 / $total) / 100,
                CHANGE24H_DOWN_7_10 => round($desc7_10 * 10000 / $total) / 100,
                CHANGE24H_DOWN_5_7 => round($desc5_7 * 10000 / $total) / 100,
                CHANGE24H_DOWN_3_5 => round($desc3_5 * 10000 / $total) / 100,
                CHANGE24H_DOWN_0_3 => round($desc0_3 * 10000 / $total) / 100,
                CHANGE24H_BTC_CHANGE => $btcChange,
                CHANGE24H_DATA => json_encode($usdtDatas),
                CHANGE24H_5M_UP => round($up5m * 10000 / $total) / 100,
                CHANGE24H_5M_DOWN => round($down5m * 10000 / $total) / 100,
                CHANGE24H_15M_UP => round($up15m * 10000 / $total) / 100,
                CHANGE24H_15M_DOWN => round($down15m * 10000 / $total) / 100,
                CHANGE24H_1H_UP => round($up1h * 10000 / $total) / 100,
                CHANGE24H_1H_DOWN => round($down1h * 10000 / $total) / 100,
                CHANGE24H_4H_UP => round($up4h * 10000 / $total) / 100,
                CHANGE24H_4H_DOWN => round($down4h * 10000 / $total) / 100,
                CHANGE24H_UP50 => round($top50U * 10000 / $total50) / 100,
                CHANGE24H_DOWN50 => round($top50D * 10000 / $total50) / 100,
                CHANGE24H_KEEP50 => round($top50K * 10000 / $total50) / 100,

            ]]);

            $startObject = [];
            foreach ([5, 9, 13] as $N) {
                AltsUpEma::caculate($N, $startObject);
            }
            foreach ([5, 9, 13] as $N) {
                AltsUpEma50::caculate($N, $startObject);
            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }

    private function getUsdtData($frame)
    {
        $time = floor(time() / 60) * 60 * 1000;
        $frameTime = [
            '5m' => 5 * 60 * 1000,
            '15m' => 15 * 60 * 1000,
            '1h' => 3600 * 1000,
            '4h' => 4 * 3600 * 1000,
        ];

        $searchTime = floor($time / $frameTime[$frame]) * $frameTime[$frame];

        $lastData = $this->change24Model->read([[[CHANGE24H_TIME, '<=', $searchTime]]], function ($db) {
            $db->orderBy(CHANGE24H_TIME, 'DESC')->limit(1);
        });
        if (!$lastData['result'] || !isset($lastData['data'][0])) return [];
        $lastData = $lastData['data'][0];

        if ($lastData->{CHANGE24H_DATA} == null) return [];

        $oldUsdtData = json_decode($lastData->{CHANGE24H_DATA}, true);

        return $oldUsdtData;
    }
}

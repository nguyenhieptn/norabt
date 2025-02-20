<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Helpers\Admin\CoinMarket;
use App\Helpers\DB\Models;
use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use Exception;

class Crawler_CoinMarket extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'coin_market';

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
            // $startTime = microtime(true);
            $this->alarmCfg = Ctrl::get('coin_market_alter', null);
            $this->alarmCfg = json_decode($this->alarmCfg, true);
            if ($this->alarmCfg == null) $this->alarmCfg = [];


            $this->coinMarket = new CoinMarket();
            $Model =  Models::get('Admin/CoinMarket');

            $readData = $Model->read([]);
            if (!$readData['result']) return $readData;
            $readData = $readData['data'];

            if (!isset($readData[0])) {
                $this->getData($Model);
                return;
            }

            $oldData = [];
            foreach ($readData as $row) {
                $oldData[$row->{COINMARKET_SYMBOL}] = $row;
            }

            $addData = $this->getData($Model);

            // echo "execute time = " . (microtime(true) - $startTime) . "\n";

            $newData = [];
            foreach ($addData as $row) {
                $newData[$row[COINMARKET_SYMBOL]] = $row;
            }



            foreach ($newData as $symbol => $row) {

                $newRank = $row[COINMARKET_RANK];
                if (isset($oldData[$symbol])) {
                    $oldRank = $oldData[$symbol]->{COINMARKET_RANK};
                    $this->checkAlarm($newRank, $oldRank, $symbol);
                }
            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }


    private  function getData($Model)
    {

        $result = $this->coinMarket->getTop150Coin();
        print_r($result);
        if($result['result']){
            $result =  $result['data']['data'];
            $addData = [];

            foreach ($result as $row) {
    
                $data = [
                    COINMARKET_SYMBOL => '',
                    COINMARKET_RANK => 0,
                    COINMARKET_PRICE => 0,
                    COINMARKET_VOLUME_24H => 0,
                    COINMARKET_PERCENT_CHANGE_1H => 0,
                    COINMARKET_PERCENT_CHANGE_24H => 0,
                    COINMARKET_PERCENT_CHANGE_7D => 0,
                    COINMARKET_PERCENT_CHANGE_30D => 0,
                    COINMARKET_MARKET_CAP => 0,
                    COINMARKET_LAST_UPDATED => 0,
                ];
                if(!isset($row['symbol'])) continue;
                $data[COINMARKET_SYMBOL] = $row['symbol'] . 'USDT';
                $data[COINMARKET_RANK] = $row['cmc_rank'];
                $data[COINMARKET_PRICE] = $row['quote']['USD']['price'];
                $data[COINMARKET_PERCENT_CHANGE_1H] = $row['quote']['USD']['percent_change_1h'];
                $data[COINMARKET_PERCENT_CHANGE_24H] = $row['quote']['USD']['percent_change_24h'];
                $data[COINMARKET_PERCENT_CHANGE_7D] = $row['quote']['USD']['percent_change_7d'];
                $data[COINMARKET_PERCENT_CHANGE_30D] = $row['quote']['USD']['percent_change_30d'];
                $data[COINMARKET_MARKET_CAP] = $row['quote']['USD']['market_cap'];
                $data[COINMARKET_VOLUME_24H] = $row['quote']['USD']['volume_24h'];
                $data[COINMARKET_LAST_UPDATED] = strtotime($row['quote']['USD']['last_updated']);
    
                $addData[] = $data;
            }
    
            $Model->drop('All');
            $Model->add($addData);
    
            return $addData;
        }else{
            throw new Exception($result['message']);
        }
     
    }

    private function checkAlarm($newRank, $oldRank, $symbol)
    {

        foreach ($this->alarmCfg as $alarm) {
            if (isset($alarm['active']) && $alarm['active'] == 0) continue;

            $checkResult = $this->checkCondition($newRank, $oldRank, $alarm['condition']);

            if ($checkResult === false || $checkResult === null) continue;

            $this->makeAlert($alarm, $symbol, $oldRank, $newRank);
        }
    }

    private function checkCondition($newRank, $oldRank, $condition)
    {
        $result = true;
        foreach ($condition as $con) {
            $compareResult = $this->compare($newRank, $oldRank, $con);
            if ($compareResult === null) return null;
            if (!$compareResult) {
                $result = false;
                break;
            }
        }
        return $result;
    }

    private function compare($newRank, $oldRank, $condition)
    {


        $logic = $condition['logic'];
        $com2 = $condition['value'];

        if ($com2 === null) return null;

        if ($logic == '>') return $newRank > $com2 && $oldRank < $com2;
        if ($logic == '<') return $newRank < $com2 && $oldRank > $com2;
        if ($logic == '>=') return $newRank >= $com2 && $oldRank < $com2;
        if ($logic == '<=') return $newRank <= $com2 && $oldRank > $com2;

        if ($logic == 'change') {

            if ($oldRank <= $com2) return $newRank != $oldRank;

            return false;
        }
    }



    private function makeAlert($alarm, $symbol, $oldRank, $newRank)
    {
        $icon = $alarm['icon'];
        $content = $alarm['content'];

        $content = str_replace('$new_rank', $newRank, $content);
        $content = str_replace('$old_rank', $oldRank, $content);
        $content = str_replace(['$new_rank', '$old_rank'], '', $content);

        $botId = $alarm['bot'];
        $groupId = $alarm['group'];
        echo "\n[" . $symbol . "] " . $content;
        Telegram::send($icon . " [" . $symbol . "] " . $content, $groupId, $botId);
    }
}

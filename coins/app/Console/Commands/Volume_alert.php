<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;

class Volume_alert extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * Service Name: volatility_alert
     */
    protected $signature = 'volume_alert';

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


            $this->alarmCfg = Ctrl::get('volume_alarm_configuration', null);
            $this->alarmCfg = json_decode($this->alarmCfg, true);
            if ($this->alarmCfg == null) $this->alarmCfg = [];
            $this->alarmResult = [];
            $this->candle24hModel = Models::get('Admin/Candle_24h');

            while (true) {

                $currentData = $this->getCurrentData();
                if (!$currentData['result']) return $currentData;
                $currentData = $currentData['data'];

                foreach ($currentData as $sym => $data) {
                    print_r($this->checkAlarm($data, $sym));
                }

                sleep(300);
            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }


    private function getCurrentData()
    {

        $startTime = round(microtime(true) * 1000);
        $dateTime = floor($startTime / 86400000) * 86400000;
        $currentData = $this->candle24hModel->read([[[CANDLE_24H_DATE, '=', $dateTime]]], function ($db) {
            $db->orderBy(CANDLE_24H_VOLUME_USDT, 'DESC');
        });

        if (!$currentData['result']) return $currentData;

        $currentData = $currentData['data'];

        $indexData = [];

        foreach ($currentData as $key => $data) {
            $data->{'index'} = $key + 1;
            $indexData[$data->{CANDLE_24H_SYMBOL}] = $data;
        }

        return Reply::make(true, 'success', $indexData);
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

        $col = $condition['column'];
        $com1 = $this->calCom1($data, $col);

        $logic = $condition['logic'];
        $com2 = $condition['value'];

        if ($com1 === null || $com2 === null) return null;

        if ($logic == '=') return $com1 == $com2;
        if ($logic == '>') return $com1 > $com2;
        if ($logic == '<') return $com1 < $com2;
        if ($logic == '>=') return $com1 >= $com2;
        if ($logic == '<=') return $com1 <= $com2;
    }


    private function calCom1($data, $col)
    {

        if ($col == 'index') {
            return intval($data->{'index'});
        }

        if ($col == 'volume') {
            return doubleval($data->{CANDLE_24H_VOLUME_USDT});
        }

        return null;
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

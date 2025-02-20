<?php

namespace App\Console\Commands;

use App\Crawler\System\History\CandleHistory;
use App\Crawler\System\Service\CandleRealtime;
use App\Event\Lab\EventCheck;
use App\Event\Lab\EventCheck15m;
use App\Event\Lab\EventCheck15MH3;
use App\Event\Lab\EventCheck15MH4;
use App\Event\Lab\EventCheck15MH5;
use App\Event\Lab\EventCheck15MH6;
use App\Event\Lab\EventCheck15MH93MH51MH5;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Split_wma extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'split_wma {strategy}';

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
       
        $strategyName = $this->argument('strategy');

        $strategyModel = Models::get('Admin/Lab_strategies');
        $resultModel = Models::get('Admin/Lab_results');

        $strategy = $strategyModel->read([[[LAB_STRATEGY_NAME, '=', $strategyName]]]);
        if(!$strategy['result'] || !isset($strategy['data'][0])) return Reply::make(false, 'Can not get strategy');

        $strategy = $strategy['data'][0];

        $results= $resultModel->read([[[LAB_RESULT_STRATEGY, '=', $strategy->{LAB_STRATEGY_ID}]]]);
        if(!$results['result']) return $results;

        $results = $results['data'];

        echo "Process " . count($results) . " results \n";
        $process = 0;

        foreach($results as $result){
            $process ++;
            $baseOn = $result->{LAB_RESULT_BASE};
            $baseOn = json_decode($baseOn, true);
            if(isset($baseOn[0]) && isset($baseOn[0]['BTCUSDT'])){

                $editData = [];
                if(isset($baseOn[0]['BTCUSDT']['1d']) && isset($baseOn[0]['BTCUSDT']['1d'][0][LAB_CANDLE_1D_RSI_WMA])){
                    $editData[LAB_RESULT_BTC_WMA45_1D] = $baseOn[0]['BTCUSDT']['1d'][0][LAB_CANDLE_1D_RSI_WMA];
                }
                if(isset($baseOn[0]['BTCUSDT']['1w']) && isset($baseOn[0]['BTCUSDT']['1w'][0][LAB_CANDLE_1W_RSI_WMA])){
                    $editData[LAB_RESULT_BTC_WMA45_1W] = $baseOn[0]['BTCUSDT']['1w'][0][LAB_CANDLE_1W_RSI_WMA];
                }
                if(count($editData) > 0){
                    
                    $resultModel->edit([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $result->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => $editData
                    ]);
                }
                
            }

            echo "\r Processed : $process";
        }

    }
}

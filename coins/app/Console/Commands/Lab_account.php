<?php

namespace App\Console\Commands;

use App\Event\Lab\EventCheckContainer;
use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;


class Lab_account extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'lab_account {account}';

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

        $time_start = microtime(true);
        $timePoint = microtime(true);

        $accountId = $this->argument('account');
        if ($accountId == null) return;
        set_time_limit(0);

        $dbName = Ctrl::get('control_lab_db', 'coin_crawler');
        $model = Models::get('Admin/Lab_campaigns');
        $accountModel = Models::get('Admin/Lab_account');
        $Candle1mModel = Models::get('Admin/Lab_candle_1m');
        $trackBlModel = Models::get('Admin/Lab_track_balance');
        $Candle1mModel->query_builder = DB::connection($dbName)->table('lab_candle_1m');

        //get account
        $account = $accountModel->read([[[LAB_ACCOUNT_ID, '=', $accountId]]]);
        if (!$account['result'] || !isset($account['data'][0])) {
            return Reply::make(false, 'Account not found');
        }
        $account = $account['data'][0];
        
        // get all campaign of an account
        $campains = $model->read([[[LAB_CAMPAIGN_ACCOUNT, '=', $accountId]]]);
        if(!$campains['result']) return $campains;
        $campains = $campains['data'];

        //Update status
        $model->edit([
            DATA_KEY => [[[LAB_CAMPAIGN_ACCOUNT, '=', $accountId]]],
            DATA_EDITOR => [
                LAB_CAMPAIGN_LAST => time(),
                LAB_CAMPAIGN_RUNNING => 1,
                LAB_CAMPAIGN_STATUS => "0,0", 
            ],
        ]);

        $accountModel->edit([
            DATA_KEY => [[[LAB_ACCOUNT_ID, '=', $accountId]]],
            DATA_EDITOR => [
                LAB_ACCOUNT_RUNNING => 1,
            ],
        ]);

        $trackBlModel->drop([[[LAB_TRACK_BL_ACCOUNT, '=', $accountId]]]);
        Models::get('Admin/Lab_results')->drop([[[LAB_RESULT_ACCOUNT, '=', $accountId]]]);
        echo "Event check clean data " . $accountId . " Excute time " . (microtime(true) - $time_start) . " second\n";

        //create Eventcheck for all campaign
        $eventProcessors = [];
        $totalNeedData = [];
        $startTime = null;
        $stopTime = null;
       
        foreach($campains as $campain){

            $tempStartTime =get($campain->{LAB_CAMPAIGN_START}, 0) * 1000;
            $tempStopTime =get($campain->{LAB_CAMPAIGN_STOP}, 0) * 1000;
            if(is_null($startTime)){
                $startTime = $tempStartTime;
            }else{
                if($tempStartTime < $startTime){
                    $startTime = $tempStartTime;
                }
            }

            if(is_null($stopTime)){
                $stopTime = $tempStopTime;
            }else{
                if($tempStopTime < $stopTime){
                    $stopTime = $tempStopTime;
                }
            }

            $eventProcessor = new EventCheckContainer($campain);
            $eventProcessors[$campain->{LAB_CAMPAIGN_ID}] = $eventProcessor;
            Models::get('Admin/Lab_event_logs')->drop([[[LAB_ELOG_CAMPAIGN, '=', $campain->{LAB_CAMPAIGN_ID}]]]);
            echo "Event check clean data " . $campain->{LAB_CAMPAIGN_NAME} . " Excute time " . (microtime(true) - $time_start) . " second\n";

            $needData = $eventProcessor->needData;
            foreach($needData as $symbol => $data){
                if(!isset($totalNeedData[$symbol])){
                    $totalNeedData[$symbol] = $data;
                }else{
                    foreach ($data as $frame=>$max){
                        if(!isset($totalNeedData[$symbol][$frame])){
                            $totalNeedData[$symbol][$frame] = $max;
                        }else{
                            if($max < $totalNeedData[$symbol][$frame]){
                                $totalNeedData[$symbol][$frame] = $max;
                            }
                        }
                    }
                }
            }

        }

        $longSymbol = null;
        $total = null;
        foreach($campains as $campain){
            $symbol = $campain->{LAB_CAMPAIGN_SYMBOL};
            $campaignTotal = $Candle1mModel->count([[[LAB_CANDLE_1M_SYMBOL, '=', $symbol], [LAB_CANDLE_1M_TIME, '>=', $startTime], [LAB_CANDLE_1M_TIME, '<=', $stopTime]]]);
            $campaignTotal = $campaignTotal['data'];
            if(is_null($total)){
                $longSymbol = $symbol;
                $total = $campaignTotal;
            }else{
                if($campaignTotal > $total){
                    $longSymbol = $symbol;
                    $total = $campaignTotal;
                }
            }
        }

       
        

        $processed = 0;
        try {

            $getDataStartTime = $startTime;
            $getDataStopTime = $getDataStartTime + 30 * 86400 * 1000;
            if($getDataStopTime > $stopTime) $getDataStopTime = $stopTime;
            while ($processed < $total) {
                $time_start = microtime(true);

                $indexData = [];
               
                foreach ($totalNeedData as $sym => $needDataSym) {
                    
                    $indexData[$sym] = [];
                    foreach ($needDataSym as $frame => $val) {
                        
                        $frameModel = Models::get('Admin/Lab_candle_' . $frame);
                        $frameModel->query_builder = DB::connection($dbName)->table('lab_candle_' . $frame);

                        $symbolColName = "lab_candle_" . $frame . "_symbol";
                        $timeColName = "lab_candle_" . $frame . "_time";
                        echo "Get data $sym $frame from $getDataStartTime to $getDataStopTime\n";
                        $frameData = $frameModel->read([[[$symbolColName, '=', $sym], [$timeColName, '>', $getDataStartTime], [$timeColName, '<=', $getDataStopTime]]], 
                        function ($db) use ($timeColName) {
                            $db->orderBy($timeColName, 'ASC');
                        });
                        
                        if (!$frameData['result']) return $frameData;
                        $frameData = $frameData['data'];
                        echo "Index data $sym $frame ".count($frameData)." rows\n";
                        $indexData[$sym][$frame] = [];
                        foreach ($frameData as $data) {
                            $indexData[$sym][$frame][$data->{$timeColName}] = $data;
                        }
                    }
                }
                // print_r($indexData);
                echo $account->{LAB_ACCOUNT_NAME} . " Get block data time  " . (microtime(true) - $time_start) . " second\n";

                $longSymbolData = $indexData[$longSymbol]['1m'];
                if(count($longSymbolData) <= 0) break;

                

                foreach($longSymbolData as $time => $data){
                    $time_start = microtime(true);
                    $pendingEvents = [];
                    $khung1ms = [];
                    foreach($campains as $campain){
                        $symbol = $campain->{LAB_CAMPAIGN_SYMBOL};
                        if(!isset($indexData[$symbol])) continue;
                        if(!isset($indexData[$symbol]['1m'])) continue;
                        if(!isset($indexData[$symbol]['1m'][$time])) continue;
                        $result = $eventProcessors[$campain->{LAB_CAMPAIGN_ID}]->check($indexData[$symbol]['1m'][$time], $indexData);
                        if (!$result['result']) {
                            throw new \Exception($campain->{LAB_CAMPAIGN_NAME} . " " .$result['message']);  
                        }else{
                            if($result['message'] == 'pending'){
                                $pendingEvents[] = $result['data'];
                                $khung1ms[$symbol] = $indexData[$symbol]['1m'][$time];
                            }
                        }


                        if ($processed % 50 == 0) {
                            $model->edit([
                                DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $campain->{LAB_CAMPAIGN_ID}]]],
                                DATA_EDITOR => [
                                    LAB_CAMPAIGN_STATUS => $total . "," . $processed, 
                                    LAB_CAMPAIGN_RUNNING => 1,
                                    LAB_CAMPAIGN_RUNTIME => $time
                                ],
                            ]);
                        }
                    }

                    if(count($pendingEvents) > 0){
                        $isLiquid = $this->checkLiquidation($account, $pendingEvents, $khung1ms, $time);
                        if(!$isLiquid['result']){
                            throw new \Exception($isLiquid['message']);  
                        }
                        if($isLiquid['data']){
                            throw new \Exception('Account is liquidation');
                        }
                    }
                    

                    $processed ++;
                    $getDataStartTime = $time;
                    // echo $account->{LAB_ACCOUNT_NAME} . " Process 1 event " . (microtime(true) - $time_start) . " second\n";
                }

                $getDataStopTime = $getDataStartTime + 30 * 86400 * 1000;
                if($getDataStopTime > $stopTime) $getDataStopTime = $stopTime;
                
            }

            $model->edit([
                DATA_KEY => [[[LAB_CAMPAIGN_ACCOUNT, '=', $accountId]]],
                DATA_EDITOR => [
                    LAB_CAMPAIGN_STATUS => $total . "," . $processed, 
                    LAB_CAMPAIGN_RUNNING => 0,
                    LAB_CAMPAIGN_RUNTIME => null
                ],
            ]);

            $accountModel->edit([
                DATA_KEY => [[[LAB_ACCOUNT_ID, '=', $accountId]]],
                DATA_EDITOR => [
                    LAB_ACCOUNT_RUNNING => 0,
                ],
            ]);

      
            Telegram::send(TELE_ICON_STOP . " " . $account->{LAB_ACCOUNT_NAME} . ' Finished ' . $total . ' Events', TELE_SIMULATE);
            echo "Total Time " . $accountId . " Excute time " . (microtime(true) - $timePoint) . " second\n";
        
        } catch (\Exception $th) {

            $model->edit([
                DATA_KEY => [[[LAB_CAMPAIGN_ACCOUNT, '=', $accountId]]],
                DATA_EDITOR => [
                    LAB_CAMPAIGN_RUNNING => 0,
                ],
            ]);
    
            $accountModel->edit([
                DATA_KEY => [[[LAB_ACCOUNT_ID, '=', $accountId]]],
                DATA_EDITOR => [
                    LAB_ACCOUNT_RUNNING => 0,
                ],
            ]);

            $ms = $th->getFile() .' '. $th->getLine() .' '. $th->getMessage();
            Telegram::send(TELE_ICON_ERROR . "[" . $account->{LAB_ACCOUNT_NAME} . "]" .  $ms, TELE_SIMULATE_ERROR);
            die;
        }

        echo "Success \n";
        return Reply::make(true);
    }


    private function checkLiquidation($account, $events, $khung1ms, $time){
        if($account->{LAB_ACCOUNT_MARGIN_TYPE} == 'CROSS' || $account->{LAB_ACCOUNT_TRACK_BALANCE} == 1){
            $totalUnrelize = 0;
            $totalInvest = 0;
            $totalBudget = 0;

            foreach($events as $event){
                $khung1m = $khung1ms[$event->{LAB_RESULT_SYMBOL}];
                $high = doubleval($khung1m->{LAB_CANDLE_1M_HIGH});
                $low = doubleval($khung1m->{LAB_CANDLE_1M_LOW});
                $matchedQty = doubleval($event->{LAB_RESULT_MATCHED_QTY});
                $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});
                $margin = doubleval($event->{LAB_RESULT_MARGIN});
                if($margin == 0) $margin = 1;
                $budget = doubleval($event->{LAB_RESULT_BUDGET});
                
                $invest = $matchedQty * $matchedPrice / $margin;
                if($event->{LAB_RESULT_TYPE} == LAB_RESULT_TYPE_LONG){
                    $worstPrice = $low;
                    $loss = ($matchedPrice - $worstPrice) * $matchedQty;
                }else{
                    $worstPrice = $high;
                    $loss = ($high - $matchedPrice) * $matchedQty;
                }

                $totalUnrelize += $loss;
                $totalInvest += $invest;
                $totalBudget += $budget;

            }

            $updatedAccount = null;

            if($account->{LAB_ACCOUNT_TRACK_BALANCE} == 1 && $totalInvest > 0){
                if(is_null($updatedAccount)) $updatedAccount = $this->getAccount($account->{LAB_ACCOUNT_ID});
                $balance = doubleval($updatedAccount->{LAB_ACCOUNT_BALANCE});
                Models::get('Admin/Lab_track_balance')->add([[
                    LAB_TRACK_BL_TIME => $time,
                    LAB_TRACK_BL_ACCOUNT => $account->{LAB_ACCOUNT_ID},
                    LAB_TRACK_BL_MARGIN_BL => $balance - $totalUnrelize,
                    LAB_TRACK_BL_INVEST => $totalInvest,
                    LAB_TRACK_BL_BALANCE => $balance,
                    LAB_TRACK_BL_UNREALIZE => -$totalUnrelize,
                ]]);
            }

            if($account->{LAB_ACCOUNT_MARGIN_TYPE} == 'CROSS' && $totalInvest > 0){
                if($totalUnrelize > ($invest * 90/100)){
                    if(is_null($updatedAccount)) $updatedAccount = $this->getAccount($account->{LAB_ACCOUNT_ID});
                    $balance = doubleval($updatedAccount->{LAB_ACCOUNT_BALANCE});
                    if($totalUnrelize > ($balance * 90/100)){
                        return Reply::make(true, 'Liquid', true);
                    }
                }
            }

        } 

        return Reply::make(true, 'Dont need to check', false);
        
    }


    private function getAccount($accountId){
        //get account
        // echo "Get Account \n";
        $accountModel = Models::get('Admin/Lab_account');
        $account = $accountModel->read([[[LAB_ACCOUNT_ID, '=', $accountId]]]);
        return $account['data'][0];
    }
}

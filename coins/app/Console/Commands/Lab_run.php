<?php

namespace App\Console\Commands;

use App\Event\Lab\EventCheck;
use App\Event\Lab\EventCheck15m;
use App\Event\Lab\EventCheck15MH3;
use App\Event\Lab\EventCheck15MH4;
use App\Event\Lab\EventCheck15MH5;
use App\Event\Lab\EventCheck15MH6;
use App\Event\Lab\EventCheck15MH93MH51MH5;
use App\Event\Lab\EventCheckContainer;
use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;


class Lab_run extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'lab_run {campaign}';

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

        $id = $this->argument('campaign');
        if ($id == null) return;
        set_time_limit(0);

        $model = Models::get('Admin/Lab_campaigns');

        $campain = $model->read([[[LAB_CAMPAIGN_ID, '=', $id]]]);
        if (!$campain['result'] || !isset($campain['data'][0])) {
            echo "Campaign not found\n";
            return Reply::make(false, 'Campaign not found');
        }
        $campain = $campain['data'][0];

        $eventProcessor = new EventCheckContainer($campain);

        $dbName = Ctrl::get('control_lab_db', 'coin_crawler');

        if (!$eventProcessor) {
            echo "Can not find any stratergy\n";
            return Reply::make(false, 'Can not find any stratergy');
        }

        $symbol = $campain->{LAB_CAMPAIGN_SYMBOL};
        $startTime = get($campain->{LAB_CAMPAIGN_START}, 0) * 1000;
        $stopTime = get($campain->{LAB_CAMPAIGN_STOP}, 0) * 1000;
        $needData = $eventProcessor->needData;

        Models::get('Admin/Lab_results')->drop([[[LAB_RESULT_CAMPAIGN, '=', $id]]]);
        Models::get('Admin/Lab_event_logs')->drop([[[LAB_ELOG_CAMPAIGN, '=', $id]]]);
        echo "Event check clean data " . $campain->{LAB_CAMPAIGN_NAME} . " Excute time " . (microtime(true) - $time_start) . " second\n";

        $Candle1mModel = Models::get('Admin/Lab_candle_1m');
        $Candle1mModel->query_builder = DB::connection($dbName)->table('lab_candle_1m');

        $model->edit([
            DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
            DATA_EDITOR => [LAB_CAMPAIGN_LAST => time()],
        ]);

        $processed = 0;
        $total = $Candle1mModel->count([[[LAB_CANDLE_1M_SYMBOL, '=', $symbol], [LAB_CANDLE_1M_TIME, '>=', $startTime], [LAB_CANDLE_1M_TIME, '<=', $stopTime]]]);
        $total = $total['data'];

        echo "Event check count " . $campain->{LAB_CAMPAIGN_NAME} . " Excute time " . (microtime(true) - $time_start) . " second\n";

        try {

            $getDataStartTime = $startTime;
            $getDataStopTime = $getDataStartTime + 30 * 86400 * 1000;
            if($getDataStopTime > $stopTime) $getDataStopTime = $stopTime;
            while ($processed < $total) {
                $time_start = microtime(true);

                $indexData = [];

                foreach($needData as $sym => $needDataSym){
                    $indexData[$sym] = [];
                    foreach($needDataSym as $frame=>$val){
                        $frameModel = Models::get('Admin/Lab_candle_'.$frame);
                        $frameModel->query_builder = DB::connection($dbName)->table('lab_candle_'.$frame);
    
                        $symbolColName = "lab_candle_".$frame."_symbol";
                        $timeColName = "lab_candle_".$frame."_time";
                        $frameData = $frameModel->read([[[$symbolColName, '=', $sym], [$timeColName, '>', $getDataStartTime], [$timeColName, '<=', $getDataStopTime]]], 
                        function ($db) use ($timeColName) {
                            $db->orderBy($timeColName, 'ASC');
                        });
                        if(!$frameData['result']) return $frameData;
                        $frameData = $frameData['data'];
                        
                        $indexData[$sym][$frame] = [];
                        foreach($frameData as $data){
                            $indexData[$sym][$frame][$data->{$timeColName}] = $data;
                        }
                    }
                }
                echo $campain->{LAB_CAMPAIGN_NAME} . " Get block data time  " . (microtime(true) - $time_start) . " second\n";
                $events = $indexData[$symbol]['1m'];
                if (count($events) == 0) break;

                foreach ($events as $event) {
                    $time_start = microtime(true);
                    $result = $eventProcessor->check($event, $indexData);
                    
                    if (!$result['result']) {
                        throw new \Exception($campain->{LAB_CAMPAIGN_NAME} . " " .$result['message']);  
                    }

                    if ($processed % 50 == 0) {
                        $model->edit([
                            DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
                            DATA_EDITOR => [
                                LAB_CAMPAIGN_STATUS => $total . "," . $processed, 
                                LAB_CAMPAIGN_RUNNING => 1,
                                LAB_CAMPAIGN_RUNTIME => $event->{LAB_CANDLE_1M_CLOSE_TIME}
                            ],
                        ]);
                    }

                    $processed++;
                    $getDataStartTime = $event->{LAB_CANDLE_1M_TIME};

                    // echo $campain->{LAB_CAMPAIGN_NAME} . " Process 1 event " . (microtime(true) - $time_start) . " second\n";
                }

                $getDataStopTime = $getDataStartTime + 30 * 86400 * 1000;
                if($getDataStopTime > $stopTime) $getDataStopTime = $stopTime;

                $model->edit([
                    DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
                    DATA_EDITOR => [LAB_CAMPAIGN_STATUS => $total . "," . $processed, LAB_CAMPAIGN_RUNNING => 1],
                ]);
            }

            $model->edit([
                DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
                DATA_EDITOR => [LAB_CAMPAIGN_STATUS => $total . "," . $processed, LAB_CAMPAIGN_RUNNING => 0],
            ]);

            Telegram::send(TELE_ICON_STOP . ' Campain: ' . $campain->{LAB_CAMPAIGN_NAME} . ' Finished ' . $total . ' Events', TELE_SIMULATE);
            //code...
        } catch (\Exception $th) {
            $ms = $th->getFile() .' '. $th->getLine() .' '. $th->getMessage();
            Telegram::send(TELE_ICON_ERROR . "[" . $campain->{LAB_CAMPAIGN_NAME} . "]" .  $ms, TELE_SIMULATE_ERROR);
            die;
        }

        echo "Success \n";
        return Reply::make(true);
    }
}

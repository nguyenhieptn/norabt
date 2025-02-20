<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\LabQuery;
use App\Helpers\Admin\LabSocket;
use App\Helpers\Admin\Services;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Exception;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;


class Lab_opt_schedule extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'lab_opt_schedule';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'schedule for optimization system';

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
            $this->model = Models::get('Admin/Lab_opt_schedule');
            $this->optModel = Models::get('Admin/Lab_optimization');

            $runningSchedules = $this->model->read([[[LAB_OPT_SCHE_STATUS, '=', 1]]]);
            if (!$runningSchedules['result']) throw new \Exception($runningSchedules['message']);
            $runningSchedules = $runningSchedules['data'];

            foreach ($runningSchedules as $schedule) {
                $this->checkSchedule($schedule);
            }
        } catch (\Exception $th) {
            Telegram::handleException($th, TELE_SIMULATE_ERROR);
        }
    }

    private function checkSchedule($schedule)
    {
        $params = $schedule->{LAB_OPT_SCHE_PARAM};
        $params = json_decode($params, true);
        if (!$params) throw new \Exception("Can not get params of schedule");

        $isFree = true;
        $isComplete = false;
        $opts = [];
        #Check if have any running optimization
        foreach ($params as $key => $param) {

            $status = $param['status'];

            #get optimization on database
            $optId = get($param['opt'], null);
            if (!$optId > 0) continue;
            $opt = $this->optModel->read([[[LAB_OPT_ID, '=', $optId]]]);
            if (!$opt['result'] || !isset($opt['data'][0])) {
                Telegram::send(TELE_ICON_ERROR . " Schedule: Can not find Optimization id = " . $optId, TELE_SIMULATE_ERROR);
                continue;
            }
            $opt = $opt['data'][0];
            $opts[$optId] = $opt;

            #check if is it running or not
            $isRunning = $this->isRunning($opt);
            
            if (!$isRunning['result']) {
                Telegram::send(TELE_ICON_ERROR . " Schedule [" . $schedule->{LAB_OPT_SCHE_NAME} . "] can not get status " . $opt->{LAB_OPT_NAME} . ". " . $isRunning['message'], TELE_SIMULATE_ERROR);
                $isFree = false;
                break;
            }

            if ($isRunning['data']) {
                $params[$key]['status'] = LAB_OPT_SCHE_PARAM_STATUS_RUNNING;
                $isFree = false;
            } else {
                if($status != LAB_OPT_SCHE_PARAM_STATUS_PENDING)
                    $params[$key]['status'] = LAB_OPT_SCHE_PARAM_STATUS_DONE;
            }

            if ($params[$key]['status'] != $status) {
                $this->model->edit([
                    DATA_KEY => [[[LAB_OPT_SCHE_ID, '=', $schedule->{LAB_OPT_SCHE_ID}]]],
                    DATA_EDITOR => [LAB_OPT_SCHE_PARAM => json_encode($params)]
                ]);
            }

            if (!$isFree) {
                break;
            }
        }
       

        if ($isFree) {

            $isComplete = true;
            foreach ($params as $key => $param) {
                $status = $param['status'];
                if ($status == LAB_OPT_SCHE_PARAM_STATUS_PENDING) {
                    $isComplete = false;
                    $optId = get($param['opt'], null);
                    if (!isset($opts[$optId])) continue;
                    $opt = $opts[$optId];

                    $result = $this->startOptimization($opt);
                    if(!$result['result']){
                        Telegram::send(TELE_ICON_ERROR . " Schedule [" . $schedule->{LAB_OPT_SCHE_NAME} . "] can not start " . $opt->{LAB_OPT_NAME} . ". " . $isRunning['message'], TELE_SIMULATE_ERROR);
                    }else{
                        $params[$key]['status'] = LAB_OPT_SCHE_PARAM_STATUS_SENT;
                        $this->model->edit([
                            DATA_KEY => [[[LAB_OPT_SCHE_ID, '=', $schedule->{LAB_OPT_SCHE_ID}]]],
                            DATA_EDITOR => [LAB_OPT_SCHE_PARAM => json_encode($params)]
                        ]);
                        Telegram::send(TELE_ICON_WARNING . " Schedule [" . $schedule->{LAB_OPT_SCHE_NAME} . "] start " . $opt->{LAB_OPT_NAME}, TELE_SIMULATE); 
                    }

                    break;
                }

                
            }
        }

        if ($isComplete) {
            $this->model->edit([
                DATA_KEY => [[[LAB_OPT_SCHE_ID, '=', $schedule->{LAB_OPT_SCHE_ID}]]],
                DATA_EDITOR => [
                    LAB_OPT_SCHE_STATUS => 0,
                    LAB_OPT_SCHE_STOP => time()
                ]
            ]);
            Telegram::send(TELE_ICON_WARNING . " Schedule [" . $schedule->{LAB_OPT_SCHE_NAME} . "] Done", TELE_SIMULATE); 

        }
    }


    private function isRunning($opt)
    {
        try {
            if ($opt->{LAB_OPT_SERVER} == 'localhost') {
                $isRunning = Services::isRunning("lab_optimization " . $opt->{LAB_OPT_ID} . " ");
                return Reply::make(true, 'success', $isRunning);
            } else {
                $server = get($opt->{LAB_OPT_SERVER}, 'Localhost');
                $isRunning = LabSocket::makeRemoteQuery(
                    $server,
                    'optimization',
                    'getStatus',
                    ['ids' => [$opt->{LAB_OPT_ID}]]
                );

                if (!$isRunning['result']) return $isRunning;
                if (isset($isRunning['data'][$opt->{LAB_OPT_ID}]) && $isRunning['data'][$opt->{LAB_OPT_ID}]) {
                    $isRunning = true;
                } else {
                    $isRunning = false;
                }
                return Reply::make(true, 'success', $isRunning);
            }
        } catch (\Throwable $th) {
            return Reply::make(false, $th->getMessage());
        }
    }

    private function startOptimization($opt)
    {
        try {
            $server = get($opt->{LAB_OPT_SERVER}, 'Localhost');
            $id = $opt->{LAB_OPT_ID};
            return LabSocket::makeRemoteQuery($server, 'optimization', 'start', ['id' => $id]);
        } catch (\Throwable $th) {
            return Reply::make(false, $th->getMessage());
        }
    }
}

<?php

namespace App\Console\Commands;

use App\Helpers\Admin\LabSocket;
use App\Helpers\Admin\Services;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;

class Lab_schedule extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'lab_schedule';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'schedule for lab system';

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
            $this->model = Models::get('Admin/Lab_schedule');
            $this->accountModel = Models::get('Admin/Lab_account');

            $runningSchedules = $this->model->read([[[LAB_SCHE_STATUS, '=', 1]]]);
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
        $params = $schedule->{LAB_SCHE_PARAM};
        $params = json_decode($params, true);
        if (!$params) throw new \Exception("Can not get params of lab schedule");
        $isFree = true;
        $isComplete = false;
        $accounts = [];
        #Check if have any running lab schedule
        foreach ($params as $key => $param) {

            $status = $param['status'];

            #get account on database
            $accountId = get($param['account'], null);
            if (!$accountId > 0) continue;
            $account = $this->accountModel->read([[[LAB_ACCOUNT_ID, '=', $accountId]]]);
            if (!$account['result'] || !isset($account['data'][0])) {
                Telegram::send(TELE_ICON_ERROR . " Lab Schedule: Can not find account id = " . $accountId, TELE_SIMULATE_ERROR);
                continue;
            }
            $account = $account['data'][0];
            $accounts[$accountId] = $account;

            #check if is it running or not
            $isRunning = $this->isRunning($account);
            
            if (!$isRunning['result']) {
                Telegram::send(TELE_ICON_ERROR . " Lab Schedule [" . $schedule->{LAB_SCHE_NAME} . "] can not get status " . $account->{LAB_ACCOUNT_NAME} . ". " . $isRunning['message'], TELE_SIMULATE_ERROR);
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
                    DATA_KEY => [[[LAB_SCHE_ID, '=', $schedule->{LAB_SCHE_ID}]]],
                    DATA_EDITOR => [LAB_SCHE_PARAM => json_encode($params)]
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
                    $accountId = get($param['account'], null);
                    if (!isset($accounts[$accountId])) continue;
                    $account = $accounts[$accountId];

                    $result = $this->startLabAccount($account);
                    if(!$result['result']){
                        Telegram::send(TELE_ICON_ERROR . " Schedule [" . $schedule->{LAB_SCHE_NAME} . "] can not start " . $account->{LAB_ACCOUNT_NAME} . ". " . $isRunning['message'], TELE_SIMULATE_ERROR);
                    }else{
                        $params[$key]['status'] = LAB_OPT_SCHE_PARAM_STATUS_SENT;
                        $this->model->edit([
                            DATA_KEY => [[[LAB_SCHE_ID, '=', $schedule->{LAB_SCHE_ID}]]],
                            DATA_EDITOR => [LAB_SCHE_PARAM => json_encode($params)]
                        ]);
                        Telegram::send(TELE_ICON_WARNING . " Schedule [" . $schedule->{LAB_SCHE_NAME} . "] start " . $account->{LAB_ACCOUNT_NAME}, TELE_SIMULATE); 
                    }

                    break;
                }

                
            }
        }

        if ($isComplete) {
            $this->model->edit([
                DATA_KEY => [[[LAB_SCHE_ID, '=', $schedule->{LAB_SCHE_ID}]]],
                DATA_EDITOR => [
                    LAB_SCHE_STATUS => 0,
                    LAB_SCHE_STOP => time()
                ]
            ]);
            Telegram::send(TELE_ICON_WARNING . " Schedule [" . $schedule->{LAB_SCHE_NAME} . "] Done", TELE_SIMULATE); 

        }
    }

    private function isRunning($account)
    {
        try {
            if ($account->{LAB_ACCOUNT_SERVER} == 'localhost') {
                $isRunning = Services::isRunning("lab_account " . $account->{LAB_ACCOUNT_ID} . " ");
                return Reply::make(true, 'success', $isRunning);
            } else {
                $server = get($account->{LAB_ACCOUNT_SERVER}, 'Localhost');
                $isRunning = LabSocket::makeRemoteQuery(
                    $server,
                    'account',
                    'getStatus',
                    ['ids' => [$account->{LAB_ACCOUNT_ID}]]
                );

                if (!$isRunning['result']) return $isRunning;
                if (isset($isRunning['data'][$account->{LAB_ACCOUNT_ID}]) && $isRunning['data'][$account->{LAB_ACCOUNT_ID}]) {
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

    private function startLabAccount($account)
    {
        try {
            $server = get($account->{LAB_ACCOUNT_SERVER}, 'Localhost');
            $id = $account->{LAB_ACCOUNT_ID};
            return LabSocket::makeRemoteQuery($server, 'account', 'start', ['id' => $id]);
        } catch (\Throwable $th) {
            return Reply::make(false, $th->getMessage());
        }
    }
}

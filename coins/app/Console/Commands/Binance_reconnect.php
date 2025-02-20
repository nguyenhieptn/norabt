<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Services;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;

class Binance_reconnect extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'binance_reconnect';

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
        $actionModel = Models::get('Admin/Actions');
        $accountModel = Models::get('Admin/Accounts');

        $accounts = $accountModel->read();
        if(!$accounts['result']) return $accounts;
        $accounts = $accounts['data'];

        foreach($accounts as $account){
            $id = $account->{ACCOUNT_ID};
            $serviceName = "binance_update@$id";
            if(!Services::isActive($serviceName)) continue;
            if(!$actionModel->is_exist([
                [ [ACTION_ACCOUNT, '=', $id], [ACTION_PENDING, '=', 1], [ACTION_STATUS, '=', ACTION_STATUS_PENDING] ],
                [ [ACTION_ACCOUNT, '=', $id], [ACTION_PENDING, '=', 1], [ACTION_STATUS, '=', ACTION_STATUS_PHASE_PENDING] ],
                [ [ACTION_ACCOUNT, '=', $id], [ACTION_PENDING, '=', 1], [ACTION_STATUS, '=', ACTION_STATUS_STOP_PENDING] ],
            ])){

                echo "Restart service $serviceName\n";
                exec("sudo systemctl restart $serviceName");
                $accountModel->edit([
                    DATA_KEY => [[[ACCOUNT_ID, '=', $id]]],
                    DATA_EDITOR => [ACCOUNT_START_TIME => time(), ACCOUNT_STOP_TIME => null],
                ]);
            }
        }
        
    }

    
}

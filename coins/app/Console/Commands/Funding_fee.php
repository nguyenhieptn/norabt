<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Binancer;
use Illuminate\Console\Command;
use App\Helpers\DB\Models;

class Funding_fee extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'funding_fee';

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
        $accountModel = Models::get('Admin/Accounts');
        $Funding_feeModel = Models::get('Admin/Funding_fee');

        //get all account from accountBinance
        $accounts = $accountModel->read([]);
        if (!$accounts['result']) return $accounts;
        $accounts = $accounts['data'];

        foreach ($accounts as $account) {
            $id = $account->{ACCOUNT_ID};
            $binance = new Binancer($id);

            $startTime = time() * 1000 - 86400000 * 365;

            //get lastTime crawler user
            $lastrow = $Funding_feeModel->read([[[FUNDING_FEE_ACCOUNT, '=', $id]]], function ($db) {
                $db->orderBy(FUNDING_FEE_TIME, 'DESC')->limit(1);
            });

            if (!$lastrow['result']) continue;
            if (isset($lastrow['data'][0])) {
                $startTime = $lastrow['data'][0]->{FUNDING_FEE_TIME};
            }

            //call api get incom from Binance
            $info = $binance->getIncomeHistory('FUNDING_FEE', $startTime, time() * 1000);
            if (!$info['result']) continue;
            $info = (array) $info['data'];

            $addData = [];
            foreach ($info as $key => $row ) {
                if($key == 'msg') continue;
                if(!$Funding_feeModel->is_exist([[ [ FUNDING_FEE_ACCOUNT, '=', $id], [FUNDING_FEE_SYMBOL, '=', $row['symbol'] ], [FUNDING_FEE_TIME , '=' ,$row['time'] ] ]])){
                    $addData[] = [
                        FUNDING_FEE_ACCOUNT => $id,
                        FUNDING_FEE_SYMBOL => $row['symbol'],
                        FUNDING_FEE_INCOME => $row['income'],
                        FUNDING_FEE_TIME => $row['time'],
    
                    ];
                }
             
            }

            echo $id . 'add' . count($addData) . "\n";

            $Funding_feeModel->add($addData);
        }
    }
}

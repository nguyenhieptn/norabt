<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Helpers\DB\Models;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;

class Referral extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'referral';

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
            $accountModel = Models::get('Admin/Accounts');
            $ReferralModel = Models::get('Admin/Referral');

            //get all account from accountBinance
            $accounts = $accountModel->read([]);
            if (!$accounts['result']) return $accounts;
            $accounts = $accounts['data'];

            foreach ($accounts as $account) {
                $id = $account->{ACCOUNT_ID};
                $binance = new Binancer($id);

                $startTime = time() * 1000 - 86400000 * 365;

                // get lastTime crawler user
                $lastrow = $ReferralModel->read([[[REFERRAL_ACCOUNT, '=', $id]]], function ($db) {
                    $db->orderBy(REFERRAL_TIME, 'DESC')->limit(1);
                });

                if (!$lastrow['result']) continue;
                if (isset($lastrow['data'][0])) {
                    $startTime = $lastrow['data'][0]->{REFERRAL_TIME};
                }

                //call api get incom from Binance
                $info = $binance->getIncomeHistory('REFERRAL_KICKBACK', $startTime, time() * 1000);
                if (!$info['result']) continue;
                $info = (array) $info['data'];

                $addData = [];
                foreach ($info as $key => $row) {
                    if ($key == 'msg') continue;
                    if (!$ReferralModel->is_exist([[[REFERRAL_ACCOUNT, '=', $id], [REFERRAL_SYMBOL, '=', $row['symbol']], [REFERRAL_TIME, '=', $row['time']]]])) {
                        $addData[] = [
                            REFERRAL_ACCOUNT => $id,
                            REFERRAL_SYMBOL => $row['symbol'],
                            REFERRAL_INCOME => $row['income'],
                            REFERRAL_TIME => $row['time'],

                        ];
                    }
                }

                $ReferralModel->add($addData);
            }
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }
}

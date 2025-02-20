<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Telegram;
use Illuminate\Console\Command;

use App\Helpers\DB\Models;


class Testnet_track_balance extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'testnet_track_balance';

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

        $startTime = microtime(true) * 1000;
        date_default_timezone_set('Asia/Ho_Chi_Minh');


        $accountModel = Models::get('Admin/Testnet_account');
        $resultModel = Models::get('Admin/Testnet_results');
        $testnetTrackBalanceModel = Models::get('Admin/Testnet_track_balance');

        $accounts = $accountModel->read([]);
        if (!$accounts['result']) return $accounts;
        $accounts = $accounts['data'];
        $accountData = [];

        $accountName = [];
        // lay data from testnet_account
        foreach ($accounts as $account) {
            $accountData[$account->{TESTNET_ACCOUNT_ID}] = [
                TESTNET_TRACK_BL_ACCOUNT => $account->{TESTNET_ACCOUNT_ID},
                TESTNET_TRACK_BL_TIME => time() * 1000,
                TESTNET_TRACK_BL_MARGIN_BL => null,
                TESTNET_TRACK_BL_INVEST => null,
                TESTNET_TRACK_BL_UNREALIZE => null,
                TESTNET_TRACK_BL_BALANCE => $account->{TESTNET_ACCOUNT_BALANCE},

            ];

            $accountName[$account->{TESTNET_ACCOUNT_ID}] = $account->{TESTNET_ACCOUNT_NAME};
        }

        // lay data from testnet_result
        $results = $resultModel->read([[[TESTNET_RESULT_PENDING, '=', '1']]]);
        if (!$results['result']) return $results;
        $results = $results['data'];



        //gop dl cac account
        $resultData = [];
        foreach ($results as $result) {
            $resultData[$result->{TESTNET_RESULT_ACCOUNT}][] = $result;
        }

        //tinh dl cho tung account
        foreach ($resultData as $account => $row) {

            $totalInvest = 0;
            $totalUnrealize = 0;


            foreach ($row as $result) {
                $invest = $result->{TESTNET_RESULT_MATCHED_PRICE} * $result->{TESTNET_RESULT_MATCHED_QTY};
                $unrealize = ($result->{TESTNET_RESULT_PROFIT} *   $invest) / 100;

                $totalInvest += $invest;
                $totalUnrealize += $unrealize;
            }

            // if ($totalInvest == 0) {
            //     unset($accountData[$account]);
            // } else {
            $accountData[$account][TESTNET_TRACK_BL_INVEST] =  $totalInvest;
            $accountData[$account][TESTNET_TRACK_BL_UNREALIZE] =  $totalUnrealize;
            $accountData[$account][TESTNET_TRACK_BL_MARGIN_BL] =  $accountData[$account][TESTNET_TRACK_BL_BALANCE] + $totalUnrealize;

            //check Liquidation 
            // if ($totalUnrealize >  ($accountData[$account][TESTNET_TRACK_BL_BALANCE] * 90) / 100) {
            //     Telegram::send(TELE_ICON_WARNING . $accountName[$account] . " Liquidation"
            //         . "\n Unrelizeprofit: " . $totalUnrealize
            //         . "\n Balance: " .  $accountData[$account][TESTNET_TRACK_BL_BALANCE], TELE_TEST_ERROR);
            // }
            // }
        }
        //loai bo account dang ko choi
        foreach ($accountData as $account => $row) {
            if (!isset($row[TESTNET_TRACK_BL_INVEST])) {
                unset($accountData[$account]);
            }
        }

        $testnetTrackBalanceModel->add($accountData);

        $stopTime = microtime(true) * 1000;

        echo "execute time " . ($stopTime - $startTime) . "ms \n";
    }
}

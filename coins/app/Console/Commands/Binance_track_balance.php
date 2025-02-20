<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;

class Binance_track_balance extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'binance_track_balance';

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
            $startTime = microtime(true) * 1000;
            date_default_timezone_set('Asia/Ho_Chi_Minh');


            $accountModel = Models::get('Admin/Accounts');
            $accountSummaryModel = Models::get('Admin/Account_summary');
            $actionsModel = Models::get('Admin/Actions');
            $bianceTrackBalanceModel = Models::get('Admin/Binance_track_balance');

            //get data form account_summary -> account_balance
            $accountSummarys = $accountSummaryModel->read([]);
            if (!$accountSummarys['result']) return $accountSummarys;
            $accountSummarys = $accountSummarys['data'];

            $accountSummaryData = [];
            foreach ($accountSummarys as $accountSummary) {
                $accountSummaryData[$accountSummary->{AC_SUM_ACCOUNT}] = $accountSummary->{AC_SUM_BALLANCE};
            }


            // lay data from accounts
            $accounts = $accountModel->read([]);
            if (!$accounts['result']) return $accounts;
            $accounts = $accounts['data'];

            $accountData = [];

            foreach ($accounts as $account) {
                if (isset($accountSummaryData[$account->{ACCOUNT_ID}])) {
                    $accountData[$account->{ACCOUNT_ID}] = [
                        BINANCE_TRACK_BL_ACCOUNT => $account->{ACCOUNT_ID},
                        BINANCE_TRACK_BL_TIME => time() * 1000,
                        BINANCE_TRACK_BL_MARGIN_BL => null,
                        BINANCE_TRACK_BL_INVEST => null,
                        BINANCE_TRACK_BL_UNREALIZE => null,
                        BINANCE_TRACK_BL_BALANCE => $accountSummaryData[$account->{ACCOUNT_ID}],

                    ];
                }
            }

            // lay data from actions
            $actions = $actionsModel->read([[[ACTION_PENDING, '=', '1']]]);
            if (!$actions['result']) return $actions;
            $actions = $actions['data'];

            //gop dl cac account
            $resultData = [];
            foreach ($actions as $result) {
                $resultData[$result->{ACTION_ACCOUNT}][] = $result;
            }

            //tinh dl cho tung account
            foreach ($resultData as $account => $row) {

                if (!isset($accountData[$account])) continue;

                $totalInvest = 0;
                $totalUnrealize = 0;


                foreach ($row as $result) {
                    $invest = $result->{ACTION_MATCHED_PRICE} * $result->{ACTION_MATCHED_QTY};
                    $unrealize = ($result->{ACTION_PROFIT} *   $invest) / 100;

                    $totalInvest += $invest;
                    $totalUnrealize += $unrealize;
                }

                $accountData[$account][BINANCE_TRACK_BL_INVEST] =  $totalInvest;
                $accountData[$account][BINANCE_TRACK_BL_UNREALIZE] =  $totalUnrealize;
                $accountData[$account][BINANCE_TRACK_BL_MARGIN_BL] =  $accountData[$account][BINANCE_TRACK_BL_BALANCE] + $totalUnrealize;
            }
            //loai bo account dang ko choi
            foreach ($accountData as $account => $row) {
                if (!isset($row[BINANCE_TRACK_BL_INVEST]) || !isset($row[BINANCE_TRACK_BL_BALANCE]) || $row[BINANCE_TRACK_BL_BALANCE] == 0) {
                    unset($accountData[$account]);
                }
            }

            // print_r($accountData);

            $bianceTrackBalanceModel->add($accountData);

            $stopTime = microtime(true) * 1000;

            echo "execute time " . ($stopTime - $startTime) . "ms \n";
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }
}

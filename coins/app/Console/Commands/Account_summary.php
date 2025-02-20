<?php

namespace App\Console\Commands;

use App\Event\Lab\EventCheck;
use App\Event\Lab\EventCheck15m;
use App\Event\Lab\EventCheck15MH3;
use App\Event\Lab\EventCheck15MH4;
use App\Event\Lab\EventCheck15MH5;
use App\Event\Lab\EventCheck15MH6;
use App\Event\Lab\EventCheck15MH93MH51MH5;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;


class Account_summary extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'account_summary';

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

            $accountData = [];

            $accountModel = Models::get('Admin/Accounts');
            $accounts = $accountModel->read([]);
            if (!$accounts['result']) return $accounts;
            $accounts = $accounts['data'];

            foreach ($accounts as $account) {
                $accountData[$account->{ACCOUNT_ID}] = [
                    AC_SUM_ID => $account->{ACCOUNT_ID},
                    AC_SUM_FREE => 0,
                    AC_SUM_USED => 0,
                    AC_SUM_ACCOUNT => $account->{ACCOUNT_ID},
                    AC_SUM_TRADING => 0,
                    AC_SUM_BALLANCE => 0,
                    AC_SUM_INVESTING => 0,
                    AC_SUM_MONTHPROFIT => 0,
                    AC_SUM_TODAYPROFIT => 0,
                    AC_SUM_TOTALPROFIT => 0,
                    AC_SUM_UNREALIZED_PROFIT => 0,
                    AC_SUM_MAINT_MARGIN => null,
                    AC_SUM_MARGIN_BALANCE  => null,
                    AC_SUM_MARGIN_RATIO  => null,
                    AC_SUM_AVAILABLE => null,
                    AC_SUM_INITIAL_MARGIN => null,
                    AC_SUM_FUNDING_FEE => null,
                    AC_SUM_COMMISSION => null,
                    AC_SUM_REFERAL => null,
                ];
            }

            $actionModel = Models::get('Admin/Actions');
            $actions = $actionModel->read([], function ($db) {
                $db->orderBy(ACTION_SELL_TIME, 'ASC');
            });

            if (!$actions['result']) return $actions;
            $actions = $actions['data'];

            $startOfDay = strtotime('today', time()) * 1000;
            $startOfMonth = strtotime(date('Y-m-1')) * 1000;

            foreach ($actions as $action) {
                $accountId = $action->{ACTION_ACCOUNT};
                if (!isset($accountData[$accountId])) {
                    continue;
                }

                if ($action->{ACTION_PENDING} == 1) {
                    $margin = doubleval($action->{ACTION_MARGIN});
                    if ($margin == 0) $margin = 1;
                    $accountData[$accountId][AC_SUM_TRADING]++;
                    $accountData[$accountId][AC_SUM_INVESTING] += $action->{ACTION_MATCHED_QTY} * $action->{ACTION_MATCHED_PRICE} / $margin;
                    $accountData[$accountId][AC_SUM_UNREALIZED_PROFIT] += ($action->{ACTION_MATCHED_QTY} * $action->{ACTION_MATCHED_PRICE}) * (doubleval($action->{ACTION_EVENTPROFIT}) + $action->{ACTION_PROFIT}) / 100;
                } else {
                    if ($action != ACTION_STATUS_CANCLE) {
                        $accountData[$accountId][AC_SUM_TOTALPROFIT] += $action->{ACTION_PNL} - $action->{ACTION_COMMIT};
                        if ($action->{ACTION_SELL_TIME} >= $startOfDay) $accountData[$accountId][AC_SUM_TODAYPROFIT] += $action->{ACTION_PNL} - $action->{ACTION_COMMIT};
                        if ($action->{ACTION_SELL_TIME} >= $startOfMonth) $accountData[$accountId][AC_SUM_MONTHPROFIT] += $action->{ACTION_PNL} - $action->{ACTION_COMMIT};
                    }
                }
            }

            $tradeModel = Models::get('Admin/Trades');

            $trades = $tradeModel->read([]);
            if (!$trades['result']) return $trades;
            $trades = $trades['data'];

            foreach ($trades as $trade) {
                $accountId = $trade->{TRADE_ACCOUNT};
                if (!isset($accountData[$accountId])) {
                    continue;
                }
                $accountData[$accountId][AC_SUM_USED] += $trade->{TRADE_BUDGET};
            }

            // print_r($accountData);


            $Funding_feeModel = Models::get('Admin/Funding_fee');

            $OrdersModel =  Models::get('Admin/Orders');
            $ReferralModel = Models::get('Admin/Referral');
            foreach ($accountData as $accountId => $data) {
                $binancer = new Binancer($accountId);
                $info = $binancer->getAccountInfo();

                //cal funding fee
                $Funding_feedb = $Funding_feeModel->db();
                $totalFundingFee = $Funding_feedb->where(FUNDING_FEE_ACCOUNT, '=', $accountId)->sum(FUNDING_FEE_INCOME);


                //cal commission
                $Ordersdb = $OrdersModel->db();
                $totalCommission = $Ordersdb->where(ORDER_ACCOUNT, '=', $accountId)->sum(ORDER_COMMIT);


                //cal referral
                $Referraldb = $ReferralModel->db();
                $totalReferral = $Referraldb->where(REFERRAL_ACCOUNT, '=', $accountId)->sum(REFERRAL_INCOME);
               
                if ($info['result']) {
                    $info = $info['data'];
                    // print_r($info);
                    $totalWalletBalance = doubleval(get($info['totalWalletBalance'], null));
                    $availableBalance = doubleval(get($info['availableBalance'], null));
                    $totalInitialMargin = doubleval(get($info['totalInitialMargin'], null));
                    $totalMarginBalance = doubleval(get($info['totalMarginBalance'], null));
                    $totalMaintMargin = doubleval(get($info['totalMaintMargin'], null));
                    $accountData[$accountId][AC_SUM_BALLANCE] = $totalWalletBalance;
                    $accountData[$accountId][AC_SUM_FREE] = $accountData[$accountId][AC_SUM_BALLANCE] - $accountData[$accountId][AC_SUM_USED];

                    $accountData[$accountId][AC_SUM_AVAILABLE] = $availableBalance;
                    $accountData[$accountId][AC_SUM_INITIAL_MARGIN] = $totalInitialMargin;
                    $accountData[$accountId][AC_SUM_MAINT_MARGIN] = $totalMaintMargin;
                    $accountData[$accountId][AC_SUM_MARGIN_BALANCE] = $totalMarginBalance;
                    $accountData[$accountId][AC_SUM_MARGIN_RATIO] = $totalMarginBalance > 0 ? round(($totalMaintMargin / $totalMarginBalance * 100), 3) : null;

                    $accountData[$accountId][AC_SUM_FUNDING_FEE] =  $totalFundingFee;
                    $accountData[$accountId][AC_SUM_COMMISSION] =  $totalCommission;
                    $accountData[$accountId][AC_SUM_REFERAL] =  $totalReferral;
                }
            }

            $sumModel = Models::get('Admin/Account_summary');
            $sumModel->drop('All');
            $addResult = $sumModel->add(array_values($accountData));

            if (!$addResult['result']) {
                print($addResult);
            }


            $stopTime = microtime(true) * 1000;

            echo "execute time " . ($stopTime - $startTime) . "ms \n";
        } catch (\Throwable $th) {
            Telegram::handleException($th, TELE_REAL_ERROR);
        }
    }
}

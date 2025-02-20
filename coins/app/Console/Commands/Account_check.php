<?php

namespace App\Console\Commands;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;


class Account_check extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'account_check';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Check if trading of account is matched with Action on system';

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

        $periodCheck = Redis::get('periodLocalAccountPending');
        if($periodCheck == null){
            $periodCheck = [];
        }else{
            $periodCheck = json_decode($periodCheck, true);
        }
        

        $startTime = microtime(true)*1000;
        date_default_timezone_set('Asia/Ho_Chi_Minh');

        $actionModel = Models::get('Admin/Actions');
        $pendingEvent = $actionModel->read([[
            [ACTION_PENDING, '=', 1],
            [ACTION_MATCHED_QTY, '>', 0]
        ]]);

        if(!$pendingEvent) return $pendingEvent;
        $pendingEvent = $pendingEvent['data'];
        $localAccountPending = [];
        foreach($pendingEvent as $event){
            $accountId = $event->{ACTION_ACCOUNT};
            if(!isset($localAccountPending[$accountId])){
                $localAccountPending[$accountId] = [];
            }
            $localAccountPending[$accountId][$event->{ACTION_SYMBOL}] = $event->{ACTION_MATCHED_QTY};
        }

        if($this->isSame($localAccountPending, $periodCheck)){
            return;
        }

        Redis::set('periodLocalAccountPending', json_encode($localAccountPending));

        $accountModel = Models::get('Admin/Accounts');
        $accounts = $accountModel->read([]);
        if(!$accounts['result']) return $accounts;
        $accounts = $accounts['data'];
        $accountIndex = [];

        $diff = [];
        foreach($accounts as $account){
            $accountId = $account->{ACCOUNT_ID};
            if($accountId == 5 || $accountId == 6) continue;
            $accountIndex[$accountId] = $account;
            $binance = new Binancer($accountId);
            $positions = $binance->getPosition();
            if(!$positions['result']) continue;
            $positions = $positions['data'];
            foreach($positions as $position){
                $symbol = $position['symbol'];
                $qty = doubleval($position['positionAmt']);
                if($qty != 0){
                    $quantity = $qty > 0 ? $qty: -$qty;
                    if(!isset($localAccountPending[$accountId]) || !isset($localAccountPending[$accountId][$symbol])){
                        $diff[] = [
                            'account' => $account->{ACCOUNT_NAME},
                            'symbol' => $symbol,
                            'log' => "Tồn tại trên Binance nhưng không có trên hệ thống"
                        ];
                    }else if($localAccountPending[$accountId][$symbol] != $quantity){
                        $diff[] = [
                            'account' => $account->{ACCOUNT_NAME},
                            'symbol' => $symbol,
                            'log' => "Số lượng khác với binance"
                        ];
                    }
                }
            }
        }

        if(count($diff) > 0){
            $ms = "";
            foreach($diff as $df){
                $ms .= "- ". $df['account']. " [" . $df['symbol'] . "]: " . $df['log'] . "\n";
            }
            Telegram::send(TELE_ICON_ERROR . " Sai khác với Binance\n" . $ms, TELE_REAL_ERROR, TELE_BOT_DEFAULT);

        }

    }


    private function isSame($oldObj, $newObj){
        
        foreach ($oldObj as $key=>$value){
            if(!isset($newObj[$key])) return false;
            if(is_array($newObj[$key]) && is_array($value)){
                if(!$this->isSame($value, $newObj[$key])){
                    return false;
                }
            }else{
                if($newObj[$key] != $value){
                    return false;
                }
            }

        }
        return true;
    }

   
}

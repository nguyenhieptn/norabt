<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Clean_data extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'clean_data';

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
        // $start = microtime(true);
        // Telegram::send('#BTCUSDT Long Order');
        // $start = microtime(true)-$start;
        // echo $start;
        // return;

        $time = time();

        # drop all cancel action of account
        Models::get('Admin/Actions')->drop([[[ACTION_STATUS, '=', ACTION_STATUS_CANCLE], [ACTION_CHART, '<', ($time - 24*60*60)*1000] ]]);

        #drop all cancle action of testnet
        Models::get('Admin/Testnet_results')->drop([[[TESTNET_RESULT_STATUS, '=', TESTNET_RESULT_STATUS_CANCLE], [TESTNET_RESULT_CHART, '<', ($time - 24*60*60)*1000] ]]);

        #drop old used weight
        Models::get('Admin/Used_weight')->drop([[[USED_W_TIME, '<', ($time - 30*24*60*60)*1000]]]);

        // Models::get('Admin/Candle_4h')->drop([[[CANDLE_4H_CLOSE_TIME, '<', ($time - 5000*60*60)*1000]]]);
        // Models::get('Admin/Candle_1h')->drop([[[CANDLE_1H_CLOSE_TIME, '<', ($time - 5000*60*60)*1000]]]);
        // Models::get('Admin/Candle_15m')->drop([[[CANDLE_15M_CLOSE_TIME, '<', ($time - 5000*15*60)*1000]]]);
        // Models::get('Admin/Candle_3m')->drop([[[CANDLE_3M_CLOSE_TIME, '<', ($time - 5000*3*60)*1000]]]);
        // Models::get('Admin/Candle_1m')->drop([[[CANDLE_1M_CLOSE_TIME, '<', ($time - 5000*60)*1000]]]);

        // Models::get('Admin/Lab_candle_1h')->drop([[[LAB_CANDLE_1H_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);
        // Models::get('Admin/Lab_candle_15m')->drop([[[LAB_CANDLE_15M_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);
        // Models::get('Admin/Lab_candle_3m')->drop([[[LAB_CANDLE_3M_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);
        // Models::get('Admin/Lab_candle_1m')->drop([[[LAB_CANDLE_1M_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);

       
    }
}

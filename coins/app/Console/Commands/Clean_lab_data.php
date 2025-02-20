<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Clean_lab_data extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'clean_lab_data';

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

        // $time = time();
        // date_default_timezone_set('Asia/Ho_Chi_Minh');

        // $today  = mktime(23, 59, 59, date("m")  , date("d"), date("Y"));
        // $todayPath = date("mdy", $today);
        // $todayLimit = date($today)*1000;

        // $tomorrow  = mktime(23, 59, 59, date("m")  , date("d")+1, date("Y"));
        // $newPart = date("mdy", $tomorrow);
        // $newPartLimit = date($tomorrow)*1000;

        // $tomorrow2  = mktime(23, 59, 59, date("m")  , date("d")+2, date("Y"));
        // $newPart2 = date("mdy", $tomorrow2);
        // $newPart2Limit = date($tomorrow2)*1000;

        // $tomorrow3  = mktime(23, 59, 59, date("m")  , date("d")+3, date("Y"));
        // $newPart3 = date("mdy", $tomorrow3);
        // $newPart3Limit = date($tomorrow3)*1000;

        // $history = mktime(23, 59, 59, date("m")  , date("d")-30, date("Y"));
        // $oldPath = date("mdy", $history);

        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_3M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_15M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_4H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$newPart3 VALUES LESS THAN ($newPart3Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        

        // Models::get('Admin/Lab_candle_1h')->drop([[[LAB_CANDLE_1H_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);
        // Models::get('Admin/Lab_candle_15m')->drop([[[LAB_CANDLE_15M_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);
        // Models::get('Admin/Lab_candle_3m')->drop([[[LAB_CANDLE_3M_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);
        // Models::get('Admin/Lab_candle_1m')->drop([[[LAB_CANDLE_1M_CLOSE_TIME, '<', ($time - 3*86400)*1000]]]);


        $daykeep = 30;
        $dayFuture = 8;

        date_default_timezone_set('Asia/Ho_Chi_Minh');

        for($i = 0; $i <= $dayFuture; $i++){
            $today  = mktime(23, 59, 59, date("m")  , date("d") + $i, date("Y"));
            $partName = date("mdy", $today);
            $partLimit = date($today)*1000;

            echo "create $partName \n";

            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1W_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            
        }

        for($i = 0; $i < 2; $i++){
            $history = mktime(23, 59, 59, date("m")  , date("d")-$daykeep-$i, date("Y"));
            $oldPath = date("mdy", $history);
            echo "delete $oldPath \n";

            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_3M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_15M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_4H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1D_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::connection('coin_crawler')->statement("ALTER TABLE ".LAB_CANDLE_1W_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        }
       
    }
}

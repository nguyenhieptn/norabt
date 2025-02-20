<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Clean_candle_data extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'clean_candle_data';

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

        // $history = mktime(23, 59, 59, date("m")  , date("d")-14, date("Y"));
        // $oldPath = date("mdy", $history);

        // $history1d = mktime(23, 59, 59, date("m")  , date("d")-365, date("Y"));
        // $oldPath1d = date("mdy", $history1d);

        // try { DB::statement("ALTER TABLE ".CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::statement("ALTER TABLE ".CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_3M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::statement("ALTER TABLE ".CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_15M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::statement("ALTER TABLE ".CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::statement("ALTER TABLE ".CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_4H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}

        // try { DB::statement("ALTER TABLE ".CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        // try { DB::statement("ALTER TABLE ".CANDLE_1D_TABLE." DROP PARTITION p$oldPath1d"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}



        $daykeep = 30;
        $extendDayKeep = 365;
        $dayFuture = 8;

        date_default_timezone_set('Asia/Ho_Chi_Minh');

        for($i = 0; $i <= $dayFuture; $i++){
            $today  = mktime(23, 59, 59, date("m")  , date("d") + $i, date("Y"));
            $partName = date("mdy", $today);
            $partLimit = date($today)*1000;

            echo "create $partName \n";

            try { DB::statement("ALTER TABLE ".CANDLE_1M_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_3M_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_15M_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_1H_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_4H_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_1D_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_1W_TABLE." ADD PARTITION (PARTITION p$partName VALUES LESS THAN ($partLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            
        }

        for($i = 0; $i < 2; $i++){
            $history = mktime(23, 59, 59, date("m")  , date("d")-$daykeep-$i, date("Y"));
            $oldPath = date("mdy", $history);
            echo "delete $oldPath \n";

            try { DB::statement("ALTER TABLE ".CANDLE_1M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_3M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_15M_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_1H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_4H_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            
            $history = mktime(23, 59, 59, date("m")  , date("d")-$extendDayKeep-$i, date("Y"));
            $oldPath = date("mdy", $history);
            echo "delete $oldPath \n";
            
            try { DB::statement("ALTER TABLE ".CANDLE_1D_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
            try { DB::statement("ALTER TABLE ".CANDLE_1W_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        }
       
    }
    

}

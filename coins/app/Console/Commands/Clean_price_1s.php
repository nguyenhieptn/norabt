<?php

namespace App\Console\Commands;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Clean_price_1s extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'clean_price_1s';

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
        date_default_timezone_set('Asia/Ho_Chi_Minh');

        $today  = mktime(23, 59, 59, date("m")  , date("d"), date("Y"));
        $todayPath = date("mdy", $today);
        $todayLimit = date($today)*1000;

        $tomorrow  = mktime(23, 59, 59, date("m")  , date("d")+1, date("Y"));
        $newPart = date("mdy", $tomorrow);
        $newPartLimit = date($tomorrow)*1000;

        $tomorrow2  = mktime(23, 59, 59, date("m")  , date("d")+2, date("Y"));
        $newPart2 = date("mdy", $tomorrow2);
        $newPart2Limit = date($tomorrow2)*1000;

        $history = mktime(23, 59, 59, date("m")  , date("d")-30, date("Y"));
        $oldPath = date("mdy", $history);


        try { DB::connection('coin_chart')->statement("ALTER TABLE ".PRICE_1S_TABLE." ADD PARTITION (PARTITION p$todayPath VALUES LESS THAN ($todayLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        try { DB::connection('coin_chart')->statement("ALTER TABLE ".PRICE_1S_TABLE." ADD PARTITION (PARTITION p$newPart VALUES LESS THAN ($newPartLimit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        try { DB::connection('coin_chart')->statement("ALTER TABLE ".PRICE_1S_TABLE." ADD PARTITION (PARTITION p$newPart2 VALUES LESS THAN ($newPart2Limit));"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        try { DB::connection('coin_chart')->statement("ALTER TABLE ".PRICE_1S_TABLE." DROP PARTITION p$oldPath"); } catch (\Throwable $th) {echo $th->getMessage() . "\n";}
        


       
    }
}

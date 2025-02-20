<?php

namespace App\Console\Commands;

use App\Crawler\System\History\CandleHistory;
use App\Crawler\System\Service\CandleRealtime;
use App\Crawler\System\Service\CandleRealtimeRedis;
use App\Crawler\Test\CandleRealtimeTest;
use App\Event\Lab\EventCheck;
use App\Event\Lab\EventCheck15m;
use App\Event\Lab\EventCheck15MH3;
use App\Event\Lab\EventCheck15MH4;
use App\Event\Lab\EventCheck15MH5;
use App\Event\Lab\EventCheck15MH6;
use App\Event\Lab\EventCheck15MH93MH51MH5;
use App\Events\UpdateUserEvent;
use App\Helpers\Admin\LabSocket;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;
use DateTime;
use DateTimeZone;
use App\Helpers\Admin\CoinMarket;
class Test extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'duy_test {accountId}';

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

        $this->mainModel = Models::get('Admin/Lab_track_balance_gen');
        $account_id = intval($this->argument('accountId'));


        if($account_id == '')  Reply::finish(false , 'no account id', '' );


        $ModelLabTrackBalance = Models::get('Admin/Lab_track_balance');

        $DataBalance =  $ModelLabTrackBalance->read([[ [LAB_TRACK_BL_ACCOUNT , '=' , $account_id] ]] );

        if (!$DataBalance['result']) return $DataBalance;
        $DataBalance = $DataBalance['data'];
        print("get data success \n");

        $top20DicInvest = [];
        $top20Invest = [];

        $maxPerInBa = 0;
        $daymaxPerInBa = 0;

        foreach ($DataBalance as $row) {
            $time = intval($row->{LAB_TRACK_BL_TIME});
    
            $perInBa = floatval($row->{LAB_TRACK_BL_INVEST}) / floatval($row->{LAB_TRACK_BL_BALANCE});

            $startOfDay = floor($time / 86400000) * 86400000;

            // if (!isset($maxPerInBa)) {
            //     $maxPerInBa = $perInBa;
            //     $daymaxPerInBa = $time;
            // } else {
            //     if ($maxPerInBa < $perInBa) {
            //         $maxPerInBa = $perInBa;
            //         $daymaxPerInBa = $time;
            //     }

            // }

            if (!isset($top20DicInvest[$startOfDay])) {
                $top20DicInvest[$startOfDay] = [
                    'x2' => date('j/n/Y', $time/1000),
                    'x' => $time,
                    'y' => $perInBa
                ];
            } else {
                if (floatval($perInBa) > floatval($top20DicInvest[$startOfDay]['y'])) {
                    $top20DicInvest[$startOfDay] = [
                        'x2' => date('j/n/Y', $time/1000),
                        'x' => $time,
                        'y' => $perInBa
                    ];
                }
            }


        
        }

        $top20 = array_values($top20DicInvest);
        $ys1 = array_column($top20, 'y');
        array_multisort($ys1, SORT_DESC, $top20);
        $top20 = array_slice($top20, 0, 19);


        // $top20Invest = array_values($top20DicInvest);
        // $ys = array_column($top20Invest, 'y');
        // array_multisort($ys, SORT_DESC, $top20Invest);
        // $top20Invest = array_slice($top20Invest, 0, 19);


        print_r($top20);

        // print($maxPerInBa);
        // print("\n");
        // print($daymaxPerInBa);
        // print("\n");

    }

   
}

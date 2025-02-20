<?php

namespace App\Console\Commands;

use App\Crawler\Caculator\EmaRealtime;
use App\Crawler\Caculator\RsiEmaRealtime;
use App\Crawler\Caculator\RsiRealtime;
use App\Crawler\Caculator\SignalRealtime;
use App\Crawler\History\Candle;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

//DO NOT USED
class Candle_start extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'candle_start {symbol?} {frame?}';

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
        set_time_limit(0);
        $symbol = $this->argument('symbol');
        $frame = $this->argument('frame');

        $frames = ['4h', '1h', '15m', '3m', '1m'];
        if($frame != null && in_array($frame, $frames)){
            $frames = [$frame];
        }

        $command = 'sudo php ' . base_path() . '/artisan clean_candle_data';
        $result = exec($command);

        if ($symbol == null || $symbol == '') return;

        echo exec('systemctl stop candle_realtime@' . $symbol . '*');

        echo "\n Crawl history candle data \n";
        foreach ($frames as $interval) {
            echo "Crawl history candle data $interval\n";
            $result = Candle::craw($symbol, $interval, 500);
            if (!$result['result']) return $result;
        }

        $startObject = [];
        $pids = [];

        foreach ($frames as $interval) {
            $pid = pcntl_fork();
            if ($pid == -1) {
                echo "Can not fork";
                return;
            } else if ($pid == 0) {
                foreach ([5, 9, 12, 13, 26] as $N) {
                    echo "Caculate EMA$N $interval\n";
                    $result = EmaRealtime::caculate($symbol, $interval, $N, $startObject, null, false, true);
                    if (!$result['result']) return $result;
                }
                foreach ([9,2,3,4,5] as $N) {
                    $result = SignalRealtime::caculate($symbol, $interval, $N, $startObject, null, false, true);
                    if (!$result['result']) return $result;
                }
                if($interval == '15m' || $interval == '1h' || $interval == '4h'){
                    foreach ([14] as $N) {
                        RsiRealtime::caculate($symbol, $interval, $N, $this->startObject, null, false, true);
                    }
                    foreach ([9,5,4] as $N) {
                        RsiEmaRealtime::caculate($symbol, $interval, $N, $this->startObject, null, false, true);
                    }
                }
                echo "Finished caculator for $interval \n";
                return;
            } else {
                $pids[] = $pid;
            }
        }

        foreach ($pids as $pid) {
            pcntl_waitpid($pid, $status);
        }


        foreach($frames as $interval){
            $numberCandle = 1;
            if($interval == '15m') $numberCandle = 2;
            if($interval == '3m') $numberCandle = 5;
            if($interval == '1m') $numberCandle = 15;

            echo "Crawl history candle data 1h\n";
            $result = Candle::craw($symbol, $interval, $numberCandle, true);
            if (!$result['result']) return $result;
        }

        
        foreach ($frames as $interval) {
            echo "Start service candle_realtime@" . $symbol . "_" . $interval;
            echo exec('systemctl start candle_realtime@' . $symbol . "_" . $interval);
        }
    }
}

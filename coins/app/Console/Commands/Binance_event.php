<?php

namespace App\Console\Commands;

use App\Crawler\Caculator\Ema;
use App\Crawler\Caculator\Signal;
use App\Crawler\History\Candle;
use App\Crawler\Realtime\CandleRealtime;
use App\Event\EventRun15m;
use App\Event\Real\EventRun;
use App\Event\Real\EventRun_linhvhv;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Exception;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Binance_event extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * 
     * service name : binance_event
     */
    protected $signature = 'binance_event {symbol_account}';

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
        try {
            //code...

            $data = $this->argument('symbol_account');

            $data = explode('_', $data);
            if (count($data) == 2) {
                $symbol = $data[0];
                $account = $data[1];
                if ($account == 5 || $account == 6) {
                    $binancer = new EventRun_linhvhv($symbol, $account);
                } else {
                    $binancer = new EventRun($symbol, $account);
                }

                $result = $binancer->check();

                if (!$result['result']) {
                    throw new Exception($result['message']);
                }
            }
        } catch (\Exception $th) {
            $ms = $th->getFile() . " " . $th->getLine() . " " . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . " " . $ms, TELE_REAL_ERROR);
            $pid = $binancer->stopService();
            pcntl_waitpid($pid, $status);
        }
    }
}

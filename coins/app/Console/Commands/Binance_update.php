<?php

namespace App\Console\Commands;

use App\Crawler\Caculator\Ema;
use App\Crawler\Caculator\Signal;
use App\Crawler\History\Candle;
use App\Crawler\Realtime\CandleRealtime;
use App\Event\EventCheck;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Binance_update extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * service name: binance_update
     */
    protected $signature = 'binance_update {account}';

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
        $account = $this->argument('account');

        try {
            $binancer = new Binancer($account);
            $binancer->getPrecision('');
            print_r($binancer->liveStream());
        } catch (\Exception $th) {
            $ms = $th->getFile() . " " . $th->getLine() . " " . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . " " . $ms, TELE_REAL_ERROR);
        }
        
    }
}

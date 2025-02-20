<?php

namespace App\Console\Commands;

use App\Crawler\Caculator\Ema;
use App\Crawler\Caculator\Signal;
use App\Crawler\History\Candle;
use App\Crawler\Lab\Service\CandleRealtime;
use App\Event\EventRun15m;
use App\Helpers\Admin\Binancer;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Lab_candle extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * 
     * service name: lab_candle
     */
    protected $signature = 'lab_candle {symbol}';

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
        $crawler = new CandleRealtime($symbol);
        print_r($crawler->crawl());
        
    }
}

<?php

namespace App\Console\Commands;

use App\Crawler\System\Service\CandleRealtime;
use App\Crawler\System\Service\CandleRealtimeRedis;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Candle_realtime extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * service name: candle_realtime
     */
    protected $signature = 'candle_realtime {symbol?}';

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
        $crawler = new CandleRealtimeRedis($symbol);
        
        print_r($crawler->crawl());
        
    }
    
   
    
}

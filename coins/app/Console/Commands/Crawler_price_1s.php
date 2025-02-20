<?php

namespace App\Console\Commands;

use App\Crawler\Chart\Price1s;
use App\Event\Lab\EventCheck;
use App\Event\Lab\EventCheck15m;
use App\Event\Lab\EventCheck15MH3;
use App\Event\Lab\EventCheck15MH4;
use App\Event\Lab\EventCheck15MH5;
use App\Event\Lab\EventCheck15MH6;
use App\Event\Lab\EventCheck15MH93MH51MH5;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Crawler_price_1s extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * service name: price_1s
     */
    protected $signature = 'crawl_price_1s';

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
        $command = 'sudo php ' . base_path() . '/artisan clean_price_1s';
        $result = exec($command);
        $crawler = new Price1s();
        $crawler->crawl();
    }
}

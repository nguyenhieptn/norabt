<?php

namespace App\Console\Commands;

use App\Crawler\Analytics\Candle24hCrawler;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Crawler_candle24h extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     * service name: candle24h
     */
    protected $signature = 'crawl_candle24h';

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
        $crawler = new Candle24hCrawler();
        $crawler->crawl();
    }
}

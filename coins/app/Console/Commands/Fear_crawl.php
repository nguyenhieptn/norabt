<?php

namespace App\Console\Commands;

use App\Crawler\Fear\FearCrawler;
use Illuminate\Console\Command;

class Fear_crawl extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'fear_crawl';

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
        $crawler = new FearCrawler();
        print_r($crawler->crawl());
    }
}

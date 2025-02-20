<?php

namespace App\Console\Commands;

use App\Event\Check\EventCheck;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
//DO NOT USED
class Check_event extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'check_event {symbol?}';

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

        $crawler = new EventCheck($symbol);
        print_r($crawler->check());
    }
}

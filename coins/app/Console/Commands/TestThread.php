<?php

namespace App\Console\Commands;

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

class TestThread extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'test_thread';

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
        $pid = pcntl_fork(); // fork
        $needStop = false;

        if ($pid < 0)
            exit;
        else if ($pid) // parent
        {
            pcntl_wait($status);
            for ($i = 0; $i <= 5; $i++) { // do something for 5 minutes
                echo "parent " . $i . "\n";
                echo $z;
                sleep(1);
               
            }
            $needStop = true;
            exit;
        } else { // child
            for ($i = 0; $i <= 10; $i++) { // do something for 5 minutes
                if($needStop) exit;
                echo "child " . $i . "\n";
                sleep(1);
            }
        }
    }
}

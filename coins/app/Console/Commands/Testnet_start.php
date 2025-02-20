<?php

namespace App\Console\Commands;

use App\Event\Testnet\EventCheck;
use App\Event\Testnet\EventCheckContainer;
use App\Helpers\Admin\Telegram;
use Exception;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Testnet_start extends Command
{
    /**
     * The name and signature of the console command.
     *service name: testnet_start
     * @var string
     */
    protected $signature = 'testnet_start {campaign}';

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
        $campaign = $this->argument('campaign');
        // $crawler = new EventCheck($campaign);
        $crawler = new EventCheckContainer($campaign);

        try {
            
            $result = $crawler->check();
            print_r($result);
            if(!$result['result']){
                echo $result['message'] . "\n";
                Telegram::send(TELE_ICON_ERROR . " " . $result['message'], TELE_TEST_ERROR);
                throw new Exception($result['message']);
            }
        } catch (\Exception $th) {
            $ms = $th->getFile() . " " . $th->getLine(). " ". $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . " " . $ms, TELE_TEST_ERROR);
            $pid = $crawler->stopService($campaign);
            pcntl_waitpid($pid, $status);
        }

        
    }
}

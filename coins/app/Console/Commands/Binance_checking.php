<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;

class Binance_checking extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'binance_checking';

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
        $this->fail = 0;
    }

    /**
     * Execute the console command.
     *
     * @return mixed
     */
    public function handle()
    {
        set_time_limit(0);
        
        while (true) {
            sleep(5);
            $pingResult = $this->pingAddress('fapi.binance.com');
            if(!$pingResult){
                $this->fail ++;
                if($this->fail >= 3){
                    echo "Can not connect to fapi.binance.com \n";
                    Telegram::send(TELE_ICON_ERROR . ' [ERROR] Can not connect to fapi.binance.com', TELE_REAL_ERROR);
                }
            }else{

                if($this->fail >= 3){
                    exec('sudo systemctl restart candle_realtime@*');
                    exec('sudo systemctl restart lab_candle@*');
                    exec('sudo systemctl restart binance_update@*');
                }

                $this->fail = 0;
                
            }
            
        }
        
    }

    private function pingAddress($ip) {
        $pingresult = exec("ping -c 1 $ip", $outcome, $status);
        if (0 == $status) {
            $status = true;
        } else {
            $status = false;
        }
        return $status;
    }
}

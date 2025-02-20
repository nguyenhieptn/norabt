<?php

namespace App\Console\Commands;

use App\Crawler\Caculator\Ema;
use App\Crawler\Caculator\Signal;
use App\Crawler\History\Candle;
use App\Crawler\Realtime\CandleRealtime;
use App\Event\EventRun15m;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class Telegram_send extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'telegram_send {text} {chatId} {botId}';

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
        $data = $this->argument('text');
        $chartId = $this->argument('chatId');
        $botId = $this->argument('botId');

        if($chartId[0] == '+'){
            $chartId = substr($chartId, 1);
            Query::make('https://api.telegram.org/bot'.$botId.'/sendMessage?chat_id='.$chartId.'&text=' . urlencode($data));
        }else{
            Query::make('https://api.telegram.org/bot'.$botId.'/sendMessage?chat_id=-'.$chartId.'&text=' . urlencode($data));
        }

        
        


    }
}

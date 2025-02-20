<?php

namespace App\Console\Commands;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;


class fixOpt extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'fixOpt';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Check if trading of account is matched with Action on system';

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
        $model = Models::get('Admin/Lab_opt_result');
        $results = $model->read([[[LAB_OPT_RESULT_OPTIMIZATION, '=', 580]]]);
        $results = $results['data'];
        print(count($results));
        foreach($results as $res){
            $param = json_decode($res->{LAB_OPT_RESULT_PARAMS}, true);
            $param['#baseprofit_1#'] = $param['#baseprofit_0#'];
            $model->edit([
                DATA_KEY => [[[LAB_OPT_RESULT_ID, '=', $res->{LAB_OPT_RESULT_ID}]]],
                DATA_EDITOR => [LAB_OPT_RESULT_PARAMS => json_encode($param)]
            ]);

        }
        
    }


    

   
}

<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use App\Http\Controllers\Controller;

use Illuminate\Support\Facades\DB;


class ChartflexController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();
        
    }

    public function getDatabase(Request $request){
        try {
            return Reply::make(true, 'success', [
                'backtest_data' => 'backtest_data',
                'backtest_data_1m' => 'backtest_data_1m',
                'backtest_data_1m_full' => 'backtest_data_1m_full',
                'backtest_data_1m_spot' => 'backtest_data_1m_spot',
                'backtest_data_1m_custom' => 'backtest_data_1m_custom',
                'realtime_data' => 'realtime_data'
            ]);
        } catch (\Exception $th) {
            return Reply::make(false, $th->getMessage());
        }
        
    }

    public function getChartSource(Request $request){
        try {
            $database = $request->input('database', 'backtest_data');
            $this->btModel = DB::connection($database);
            $returnData = [];
            foreach ($this->btModel->getMongoDB()->listCollections() as $coll){
                $returnData[] = $coll->getName();
            }
            sort($returnData);
            return Reply::make(true, 'success', $returnData);
        } catch (\Exception $th) {
            return Reply::make(false, $th->getMessage());
        }
        
    }

    public function getChartField(Request $request){
        try {
            $source = $request->input('source');
            if(!$source) Reply::finish(false, "No Source");
            $database = $request->input('database', 'backtest_data');
            // var_dump($database);
            $this->btModel = DB::connection($database);

            $lastRows = $this->btModel->collection($source)->orderBy('_id', 'DESC')->skip(100)->limit(1)->get();
            $fields = [];
            if($lastRows->count() > 0){
                $lastRows = $lastRows[0];
                unset($lastRows['_id']);
                unset($lastRows['symbol']);
                $fields = array_keys($lastRows);
            }

            $midRow = $this->btModel->collection($source)->orderBy('_id', 'ASC')->skip(10000000)->limit(1)->get();
            if($midRow->count() > 0){
                $midRow = $midRow[0];
                unset($midRow['_id']);
                unset($midRow['symbol']);
                $fields += array_keys($midRow);
            }

            $firstRows = $this->btModel->collection($source)->orderBy('_id', 'ASC')->skip(100)->limit(1)->get();
            if($firstRows->count() > 0){
                $firstRows = $firstRows[0];
                unset($firstRows['_id']);
                unset($firstRows['symbol']);
                $fields += array_keys($firstRows);
            }
            return Reply::make(true, 'success', array_values(array_unique($fields)));
        } catch (\Throwable $th) {
            return Reply::make(false, $th->getMessage());
        }
    }

    public function getData(Request $request){
        try {

            $config = $request->input('configuration');
            if(!$config) Reply::finish(false, "No Source");

            $startTime = $request->input('start_time');
            $stopTime = $request->input('stop_time');

            if(!Checker::validate([$startTime, $stopTime], 'Number')) Reply::finish(false, "Wrong format");
            $cmd = '/var/www/html/coins/python/crypto_services/manage.py get_chart_data --config ' . escapeshellarg(json_encode($config)) . ' --start ' . escapeshellarg($startTime) . ' --stop ' . escapeshellcmd($stopTime);
            $output = shell_exec($cmd);
            return $output;
            

        } catch (\Throwable $th) {
            return Reply::make(false, $th->getMessage());
        }
    }


    public function getPosition(Request $request){
        $startTime = $request->input('startTime');
        $stopTime = $request->input('stopTime');
        $accountId = $request->input('account');
        $symbol = $request->input('symbol');
        $mode = $request->input('mode');
        if($mode == 'test_net'){
            $positionModel = Models::get('Admin/Testnet_results');
            $orderModel = Models::get('Admin/Testnet_order');
            
            $positions = $positionModel->read([[
                [TESTNET_RESULT_ACCOUNT, '=', $accountId], 
                [TESTNET_RESULT_SYMBOL, '=', $symbol], 
                [TESTNET_RESULT_CHART, '>=', $startTime], 
                [TESTNET_RESULT_CHART, '<=', $stopTime]
            ]]);
            if(!$positions['result']) return $positions;
            $positions = $positions['data'];
            $orders = $orderModel->read([[
                [TESTNET_ORDER_ACCOUNT, '=', $accountId], 
                [TESTNET_ORDER_SYMBOL, '=', $symbol], 
                [TESTNET_ORDER_TIME, '>=', $startTime], 
                [TESTNET_ORDER_TIME, '<=', $stopTime]]
            ]);
            if(!$orders['result']) return $orders;
            $orders = $orders['data'];

            return Reply::make(true, 'success', ['position' => $positions, 'orders' => $orders]);
        }else{
            $positionModel = Models::get('Admin/Lab_results');
            $orderModel = Models::get('Admin/Lab_order');
            
            $positions = $positionModel->read([[
                [LAB_RESULT_ACCOUNT, '=', $accountId], 
                [LAB_RESULT_SYMBOL, '=', $symbol], 
                [LAB_RESULT_CHART, '>=', $startTime], 
                [LAB_RESULT_CHART, '<=', $stopTime]
            ]]);
            if(!$positions['result']) return $positions;
            $positions = $positions['data'];
            $orders = $orderModel->read([[
                [LAB_ORDER_ACCOUNT, '=', $accountId], 
                [LAB_ORDER_SYMBOL, '=', $symbol], 
                [LAB_ORDER_TIME, '>=', $startTime], 
                [LAB_ORDER_TIME, '<=', $stopTime]]
            ]);
            if(!$orders['result']) return $orders;
            $orders = $orders['data'];

            return Reply::make(true, 'success', ['position' => $positions, 'orders' => $orders]);
        }
       
        

    }
}
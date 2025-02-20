<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Crawler_yearController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();
        $this->mainModel = Models::get('Crawler/Crawler_year_tracking');
        $this->tableName = CRAWLER_YEAR_TRACKING_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[CRAWLER_YEAR_TRACKING_ID] = true;

        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ''); 
        
    }

    

    public function crawler(Request $request)
    {
        $reset = $request->input('reset', 0);
        $exchange = $request->input('exchange', 'future');
        $frame = $request->input('frame', 'all');
        $symbol = $request->input('symbol', []);

        
       
        $url = 'http://192.168.68.25:18000/api/crawler_year';
        $data =  Query::make($url, 'post', ['reset' => $reset , 'exchange' => $exchange , 'frame' => $frame , 'symbol' => json_encode($symbol)] , [], []);


        return Reply::make(true, 'success', $data);

    }

    public function getRuning(Request $request)
    {
       
        // $url = 'http://192.168.68.25:18000/api/crawler_year/getRuning';
        // $data =  Query::make($url, 'get', [] , ['dataType' => 'json'], []);

        // $line1 = [];
        // if($data['result']){
        //     $data = $data['data'];
        //     foreach(preg_split("/((\r?\n)|(\r\n?))/", $data) as $line){
        //         $line1[] = substr($line,strpos($line , 'crawler_year '));
        //     } 
        // }

       

        $result = $this->mainModel->read();

        return $result;

    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $data) {
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    
   
   
    
}
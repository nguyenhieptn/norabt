<?php

namespace App\Http\Controllers\Admin;

use App\Crawler\Caculator\Ema;
use App\Crawler\Caculator\EmaRealtime;
use App\Crawler\Caculator\Signal;
use App\Crawler\Caculator\SignalRealtime;
use App\Crawler\History\Candle;
use App\Event\EventFunc;
use App\Helpers\Admin\Services;
use App\Helpers\Auth\Detect;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use App\Model\Admin\Requests;

use Illuminate\Support\Facades\Redis;



class TestController extends Controller
{

    use EventFunc;

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

       
    }

    public function test(Request $request){
       
        $id = $request->input('id');
        return $this->processLabStrategy($id);

    }

    public function testRedis(Request $request){
        return Redis::get('candle_data_ETHUSDT');
    }

    public function testBinance(){
        $startTime = microtime(true);
        $headers = [];
        $url = "https://fapi.binance.com/fapi/v1/exchangeInfo";
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_HEADERFUNCTION,
            function ($curl, $header) use (&$headers) {
                $len = strlen($header);
                $header = explode(':', $header, 2);
                if (count($header) < 2) // ignore invalid headers
                    return $len;

                $headers[trim($header[0])] = trim($header[1]);

                return $len;
            }
        );
        $response = curl_exec($ch);
        echo "Excute time " . (microtime(true) - $startTime);
        print_r($headers);
        echo $response;
    }


    



}
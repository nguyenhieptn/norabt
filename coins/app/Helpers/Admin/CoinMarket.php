<?php

namespace App\Helpers\Admin;

use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;

class CoinMarket
{
    function __construct()
    {
        $this->url = 'https://pro-api.coinmarketcap.com';
        $this->apiKey = 'db5e9ebc-61de-4166-8215-c872e437ed4c';
    }


    public function getTop150Coin(){
        $result =$this->query('/v1/cryptocurrency/listings/latest','GET',['start' => 1, 'limit' => 500]);
        // if (!$result['result']) return $result;
        // return $result['data']['data'];
        return $result;
     
    }


    public function query($path, $method = 'GET', $data = [])
    {
        try {
            $time = round(microtime(true) * 1000);

            $queryArray = [];

            foreach ($data as $key => $value) {
                $queryArray[] = $key . '=' . $value;
            }

            $curl = curl_init();



            $queryString = trim(implode('&', $queryArray));
            $url = $this->url . $path . '?' . $queryString;


            // echo $url . "\n";
            curl_setopt_array($curl, array(
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                // CURLOPT_ENCODING => '',
                // CURLOPT_MAXREDIRS => 10,
                // CURLOPT_TIMEOUT => 0,
                // CURLOPT_FOLLOWLOCATION => true,
                // CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                CURLOPT_CUSTOMREQUEST => $method,
                CURLOPT_HTTPHEADER => array(
                    'Accepts: application/json',
                    'X-CMC_PRO_API_KEY: ' . $this->apiKey,                 
                ),
            ));

            $responseString = curl_exec($curl);

            // echo $responseString . "\n";

            $code = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);

            curl_close($curl);

            $response = json_decode($responseString, true);
            if (json_last_error() != JSON_ERROR_NONE) {
                echo $responseString;
                return Reply::make(false, 'Data is not a json', $responseString . $url);
            }

            $result =  Reply::make($code == 200, get($response['msg'], ''), $response, $code);

            return $result;
        } catch (\Exception $th) {
            return Reply::make(false, $th->getMessage() . "($url)");
        }
    }
}

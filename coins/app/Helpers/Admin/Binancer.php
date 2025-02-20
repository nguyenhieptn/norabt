<?php

namespace App\Helpers\Admin;

use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

include('BinancerConnector.php');

class Binancer
{

    private $account;
    private $apiKey;
    private $secret;

    function __construct($id)
    {
        date_default_timezone_set('Asia/Ho_Chi_Minh');

        $this->accountModel = Models::get('Admin/Accounts');

        $this->actionModel = Models::get('Admin/Actions');
        $this->orderModel = Models::get('Admin/Orders');

        $this->tradesModel = Models::get('Admin/Trades');
        $this->strategyModel = Models::get('Admin/Strategies');

        $this->Candle15mModel = Models::get('Admin/Candle_15m');
        $this->Candle3mModel = Models::get('Admin/Candle_3m');
        $this->Candle1mModel = Models::get('Admin/Candle_1m');

        $this->usedWeightModel = Models::get('Admin/Used_weight');

        $account = $this->accountModel->read([[[ACCOUNT_ID, '=', $id]]]);

        if (!$account['result'] || !isset($account['data'][0])) {
            echo "No account";
            return;
        }

        $account = $account['data'][0];

        $this->apiKey = $account->{ACCOUNT_API_KEY};
        $this->secret = $account->{ACCOUNT_SECRET_KEY};

        if ($account->{ACCOUNT_TYPE} == ACCOUNT_TYPE_LAB) {
            $this->url = 'https://testnet.binancefuture.com';
            $this->stream = 'stream.binancefuture.com';
        } else {
            $this->url = 'https://fapi.binance.com';
            $this->stream = 'fstream.binance.com';
        }

        $this->account = $account;

        $this->strategyCfg = [];

        $this->currentMargin = [];

        //Telegram bot

        $this->teleBot = get($account->{ACCOUNT_TELE_BOT}, null);
        $this->teleGrNotice = get($account->{ACCOUNT_TELE_GR_NOTICE}, null);
        $this->teleGrError = get($account->{ACCOUNT_TELE_GR_ERROR}, TELE_REAL_ERROR);
        $this->teleGrSummary = get($account->{ACCOUNT_TELE_GR_SUMMARY}, null);
        if ($this->teleGrSummary != null) $this->teleGrSummary = explode(',', $this->teleGrSummary);
    }

    public function getAccount()
    {
        return $this->account;
    }

    public function getAccountInfo()
    {
        return $this->query('/fapi/v2/account');
    }

    public function getIncomeHistory($incomeType=null, $startTime = null, $stopTime= null){

        return $this->query('/fapi/v1/income', 'GET', ['incomeType' => $incomeType, 'startTime' => $startTime, 'stopTime'=>$stopTime, 'limit' => 1000]);
    }

    public function query($path, $method = 'GET', $data = [], $signature = true)
    {
        try {
            $headers = [];
            $time = round(microtime(true) * 1000);

            $queryArray = [];

            foreach ($data as $key => $value) {
                $queryArray[] = $key . '=' . $value;
            }

            $curl = curl_init();

            if ($signature) {
                $queryArray[] = 'timestamp=' . $time;
                $queryString = trim(implode('&', $queryArray));

                $signal = hash_hmac('sha256', $queryString, $this->secret);

                $url = $this->url . $path . '?' . $queryString . '&signature=' . $signal;
            } else {

                $queryString = trim(implode('&', $queryArray));
                $url = $this->url . $path . '?' . $queryString;
            }

            // echo $url . "\n";
            curl_setopt_array($curl, array(
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_ENCODING => '',
                CURLOPT_MAXREDIRS => 10,
                CURLOPT_TIMEOUT => 0,
                CURLOPT_FOLLOWLOCATION => true,
                CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                CURLOPT_CUSTOMREQUEST => $method,
                CURLOPT_HTTPHEADER => array(
                    'Content-Type: application/json',
                    'X-MBX-APIKEY: ' . $this->apiKey
                ),
            ));

            curl_setopt($curl, CURLOPT_HEADERFUNCTION,
                function ($curl, $header) use (&$headers) {
                    $len = strlen($header);
                    $header = explode(':', $header, 2);
                    if (count($header) < 2) // ignore invalid headers
                        return $len;
                    $headers[trim($header[0])] = trim($header[1]);
                    return $len;
                }
            );

            $responseString = curl_exec($curl);

            // echo $responseString . "\n";

            $code = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);

            curl_close($curl);

            if(isset($headers['X-MBX-USED-WEIGHT-1M']) && is_numeric($headers['X-MBX-USED-WEIGHT-1M'])){
                $this->usedWeightModel->add([[
                    USED_W_URL => $url,
                    USED_W_TIME => round(microtime(true) * 1000),
                    USED_W_DOMAIN => $this->url,
                    USED_W_VALUE => $headers['X-MBX-USED-WEIGHT-1M']
                ]]);
            }

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


    public function makeOrder($symbol, $qty, $price, $side, $takeprofit, $stoploss, $matchedQty = 0, $matchedPrice = 0, $fault=0)
    {
        // set margin
        $startTime = microtime(true);
        $time = round($startTime * 1000);
        // $result = $this->setMargin($symbol, $margin);
        // if (!$result['result']) return $result;
        //cancle all open order
        // $result = $this->query('/fapi/v1/allOpenOrders', 'DELETE', ['symbol' => $symbol]);
        // if (!$result['result']) return $result;
        // make order

        $matchPrice = null;
        $limit = false;
        $returnData = [];
        $returnData['matched'] = false;

        if ($qty == 0) return Reply::make(false, 'Quantity must be greater than 0');


        if ($price == 'market') {

            $result = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => $side, 'type' => 'MARKET', 'quantity' => $qty]);
            $orderTime = microtime(true) - $startTime;

            if (!$result['result']) return $result;

            $orderData = $result['data'];
            $orderId = $orderData['orderId'];

            foreach ([0, 1, 2, 3, 4, 5, 6, 7, 8] as $i) {
                $orderData = $this->getOrder($symbol, $orderId);
                if (!$orderData['result']) {
                    usleep(500000);
                    continue;
                }
                $orderData = $orderData['data'];
                $avgprice = doubleval($orderData['avgPrice']);
                $exeQty = doubleval($orderData['executedQty']);
                $orderTime = doubleval($orderData['time']);

                if ($avgprice > 0 && $exeQty == $qty) {
                    $matchPrice = $avgprice;

                    $returnData['matched'] = true;
                    $returnData['matched_price'] = $avgprice;
                    $returnData['matched_time'] = $orderTime;

                    break;
                }
                usleep(500000);
            }

            if ($matchPrice === null) $matchPrice = $price;

        } else {

            $result = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => $side, 'type' => 'LIMIT', 'quantity' => $qty, 'price' => $price, 'timeInForce' => 'GTC']);
            $orderTime = microtime(true) - $startTime;

            if (!$result['result']) return $result;

            $orderData = $result['data'];
            $orderId = $orderData['orderId'];

            foreach ([0, 1, 2, 3] as $i) {
                $orderData = $this->getOrder($symbol, $orderId);
                if (!$orderData['result']) {
                    usleep(500000);
                    continue;
                }
                $orderData = $orderData['data'];
                $avgprice = doubleval($orderData['avgPrice']);
                $exeQty = doubleval($orderData['executedQty']);

                if ($avgprice > 0 && $exeQty == $qty) {
                    $matchPrice = $avgprice;

                    $returnData['matched'] = true;
                    $returnData['matched_price'] = $avgprice;
                    $returnData['matched_time'] = $time;
                    break;
                } 

                usleep(500000);
            }

            if ($matchPrice === null) $matchPrice = $price;
        }

        $avgPrice = ($matchPrice * $qty + $matchedPrice * $matchedQty) / ($qty + $matchedQty);

        $stopTakeResult = $this->createTakeStop($symbol, $avgPrice, $side, $stoploss, $takeprofit);

        if (!$stopTakeResult['result']) {
            usleep(500000);
            $stopTakeResult = $this->createTakeStop($symbol, $avgPrice, $side, $stoploss, $takeprofit);
        }

        if (!$stopTakeResult['result']) {
            usleep(500000);
            $stopTakeResult = $this->createTakeStop($symbol, $avgPrice, $side, $stoploss, $takeprofit);
        }

        if (!$stopTakeResult['result']) {
            // $result = $this->canclePosition($symbol);
            // if (!$result['result']) return Reply::make(false, 'Can not create stoploss/takeprofit, can not cancle position. ' . $stopTakeResult['message']);
            // $this->stopService($symbol, 0);
            return Reply::make(false, 'Can not create stoploss/takeprofit. ' . $stopTakeResult['message']);
        }

        return Reply::make(true, "Order: $orderTime second", $returnData);
    }


    public function createTakeStop($symbol, $matchPrice, $side, $stoploss, $takeprofit)
    {

        $pre = $this->getPrecision($symbol);
        if (!$pre) return Reply::make(false, 'Can not get Precision');

        $prePrice = $pre['price'];

        $result = $this->cancleTakeStop($symbol);
        if (!$result) return $result;

        if ($side == 'SELL') {

            if ($stoploss !== false) {
                $stoplossPrice = $matchPrice + ($matchPrice * $stoploss / 100);
                $stoplossPrice = round($stoplossPrice * (10 ** $prePrice)) / (10 ** $prePrice);
                if (isset($pre['tickSize'])) {
                    $stoplossPrice = round($stoplossPrice / $pre['tickSize']) * $pre['tickSize'];
                }
                if ($stoplossPrice > 0) {
                    $stoplossResult = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'BUY', 'type' => 'STOP_MARKET', 'stopPrice' => $stoplossPrice, 'closePosition' => 'true']);
                    if (!$stoplossResult['result']) return $stoplossResult;
                }
            }

            if ($takeprofit !== false) {
                $takeprofitPrice = $matchPrice - ($matchPrice * $takeprofit / 100);
                $takeprofitPrice = round($takeprofitPrice * (10 ** $prePrice)) / (10 ** $prePrice);

                if (isset($pre['tickSize'])) {
                    $takeprofitPrice = round($takeprofitPrice / $pre['tickSize']) * $pre['tickSize'];
                }
                if ($takeprofitPrice > 0) {
                    $takeProfitResult = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'BUY', 'type' => 'TAKE_PROFIT_MARKET', 'stopPrice' => $takeprofitPrice, 'closePosition' => 'true']);
                    if (!$takeProfitResult['result']) return $takeProfitResult;
                }
            }
        } else {

            if ($stoploss !== false) {
                $stoplossPrice = $matchPrice - ($matchPrice * $stoploss / 100);
                $stoplossPrice = round($stoplossPrice * (10 ** $prePrice)) / (10 ** $prePrice);
                if (isset($pre['tickSize'])) {
                    $stoplossPrice = round($stoplossPrice / $pre['tickSize']) * $pre['tickSize'];
                }
                if ($stoplossPrice > 0) {
                    $stoplossResult = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'SELL', 'type' => 'STOP_MARKET', 'stopPrice' => $stoplossPrice, 'closePosition' => 'true']);
                    if (!$stoplossResult['result']) return $stoplossResult;
                }
            }

            if ($takeprofit !== false) {
                $takeprofitPrice = $matchPrice + ($matchPrice * $takeprofit / 100);
                $takeprofitPrice = round($takeprofitPrice * (10 ** $prePrice)) / (10 ** $prePrice);
                if (isset($pre['tickSize'])) {
                    $takeprofitPrice = round($takeprofitPrice / $pre['tickSize']) * $pre['tickSize'];
                }
                if ($takeprofitPrice > 0) {
                    $takeProfitResult = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'SELL', 'type' => 'TAKE_PROFIT_MARKET', 'stopPrice' => $takeprofitPrice, 'closePosition' => 'true']);
                    if (!$takeProfitResult['result']) return $takeProfitResult;
                }
            }
        }

        return Reply::make(true, 'Success');
    }

    public function canclePosition($symbol, $release = null)
    {

        $result = $this->query('/fapi/v2/positionRisk', 'GET', ['symbol' => $symbol]);
        if (!$result['result']) return $result;

        if (isset($result['data'][0])) {

            $qty = doubleval($result['data'][0]['positionAmt']);

            if ($qty > 0) {

                if ($release !== null) {
                    if ($release > 0 && $release < $qty) {
                        $result = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'SELL', 'type' => 'MARKET', 'quantity' => $release]);
                    } else {
                        return Reply::make(false, "Can not Release $release");
                    }
                } else {
                    $result = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'SELL', 'type' => 'MARKET', 'quantity' => $qty]);
                }

                if (!$result['result']) return $result;

                $orderData = $result['data'];
                if (!isset($orderData['orderId'])) {
                    $this->stopService($symbol);
                    return Reply::make(false, 'Can not Cancle Position');
                }
            } else if ($qty < 0) {

                if ($release !== null) {
                    if ($release > 0 && $release < -$qty) {
                        $result = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'BUY', 'type' => 'MARKET', 'quantity' => $release]);
                    } else {
                        return Reply::make(false, "Can not Release $release");
                    }
                } else {
                    $result = $this->query('/fapi/v1/order', 'POST', ['symbol' => $symbol, 'side' => 'BUY', 'type' => 'MARKET', 'quantity' => -$qty]);
                }

                if (!$result['result']) return $result;

                $orderData = $result['data'];
                if (!isset($orderData['orderId'])) {
                    $this->stopService($symbol);
                    return Reply::make(false, 'Can not Cancle Position');
                }
            }

            #cancal all order
            if ($release === null) {
                $delResult = $this->cancleAllOrder($symbol);
                if (!$delResult['result']) return $delResult;
            }

            return Reply::make(true, 'Cancle all Position and Orders');
        }

        return Reply::make(true, 'Can not find any Position to cancle');
    }



    private $getPrecisionResult = null;

    public function getPrecision($symbol)
    {
        if ($this->getPrecisionResult == null) {

            $precision = Ctrl::get('getPrecisionResult', null, true);
            if ($precision == null || intval($precision['time']) < (time() - 86400)) {
                $this->getPrecisionResult = [];
                echo "Get exchangeInfo \n";
                $result = Query::make('https://fapi.binance.com/fapi/v1/exchangeInfo', 'GET', [], ['dataType' => 'json']);

                if (isset($result['symbols'])) {
                    $datas = (array)$result['symbols'];
                    foreach ($datas as $data) {
                        $this->getPrecisionResult[$data['symbol']] = [
                            'price' => doubleval($data['pricePrecision']),
                            'quantity' => doubleval($data['quantityPrecision']),
                        ];

                        if (isset($data['filters'])) {

                            $filters = $data['filters'];
                            foreach ($filters as $filter) {
                                if (isset($filter['tickSize'])) {
                                    $this->getPrecisionResult[$data['symbol']]['tickSize'] = doubleval($filter['tickSize']);
                                    break;
                                }
                            }
                        }
                    }

                    Ctrl::set('getPrecisionResult', json_encode([
                        'time' => time(),
                        'data' => $this->getPrecisionResult
                    ]));
                }
            }else{
                $this->getPrecisionResult = $precision['data'];
            }
        }

        if (isset($this->getPrecisionResult[$symbol])) return $this->getPrecisionResult[$symbol];
        return false;
    }


    public function getOrder($symbol, $orderId)
    {
        return $this->query('/fapi/v1/order', 'GET', ['symbol' => $symbol, 'orderId' => $orderId]);
    }


    /**
     * @return data: [
     *      {
     *          "entryPrice": "0.00000",
     *          "marginType": "isolated", 
     *          "isAutoAddMargin": "false",
     *          "isolatedMargin": "0.00000000", 
     *          "leverage": "10", 
     *          "liquidationPrice": "0", 
     *          "markPrice": "6679.50671178",   
     *          "maxNotionalValue": "20000000", 
     *          "positionAmt": "0.000", 
     *          "symbol": "BTCUSDT", 
     *          "unRealizedProfit": "0.00000000", 
     *          "positionSide": "BOTH",
     *          "updateTime": 0
     *      }
     *  ]
     */
    public function getPosition($symbol=null)
    {
        $result = $this->query('/fapi/v2/positionRisk', 'GET', ['symbol' => $symbol]);
        if (!$result['result']) return $result;
        return $result;
    }

    public function syncPosition($action)
    {

        $symbol = $action->{ACTION_SYMBOL};

        $actionEditData = [];

        $position = $this->getPosition($symbol);
        if (!$position['result']) return $position;
        if (!$position['data'][0]) return Reply::make(false, "Can not get postion $symbol from binance");

        $position = $position['data'][0];
        $positionPrice = get($position['entryPrice'], null);
        $positionQty = get($position['positionAmt'], null);
        $positionType = null;

        if ($positionQty !== null) {
            if ($positionQty >= 0) {
                $positionType = ACTION_TYPE_LONG;
            } else {
                $positionType = ACTION_TYPE_SHORT;
                $positionQty = -$positionQty;
            }
        }

        $actionEditData[ACTION_MATCHED_PRICE] = $positionPrice;
        $actionEditData[ACTION_MATCHED_QTY] = $positionQty;
        if ($positionType !== null) $actionEditData[ACTION_TYPE] = $positionType;

        $startTime = $action->{ACTION_CHART};
        $endTime = $action->{ACTION_SELL_TIME};

        $trades = $this->getAllTrade($symbol, $startTime, $endTime);
        if (!$trades['result']) return $trades;
        $trades = $trades['data'];

        if (count($trades) <= 0) return Reply::make(false, 'Can not get Trades');

        $orderData = [];
        foreach ($trades as $trade) {
            if (!isset($trade['orderId'])) continue;
            $id = $trade['orderId'];
            $price = doubleval(get($trade['price'], 0));
            $qty = doubleval(get($trade['qty'], 0));
            if ($qty < 0) $qty = -$qty;
            $commit = doubleval(get($trade['commission'], 0));
            $pnl = doubleval(get($trade['realizedPnl'], 0));
            $side = get($trade['side'], null);
            $time = intval($trade['time']);

            if (!isset($orderData[$id])) {
                $orderData[$id] = [
                    ORDER_ACTION => $action->{ACTION_ID},
                    ORDER_ACCOUNT => $this->account->{ACCOUNT_ID},
                    ORDER_SYMBOL => $symbol,
                    ORDER_BINANCE => $id,
                    ORDER_TIME => $time,
                    ORDER_PRICE => $price,
                    ORDER_QTY => $qty,
                    ORDER_COMMIT => $commit,
                    ORDER_PNL => $pnl,
                    ORDER_SIDE => $side,
                ];
            } else {
                $totalQty = $orderData[$id][ORDER_QTY] + $qty;
                $totalCommit = $orderData[$id][ORDER_COMMIT] + $commit;
                $totalPNL = $orderData[$id][ORDER_PNL] + $pnl;
                if ($totalQty > 0) {
                    $avg = ($orderData[$id][ORDER_QTY] * $orderData[$id][ORDER_PRICE] + $qty * $price) / $totalQty;
                } else {
                    $avg = null;
                }

                $orderData[$id][ORDER_PRICE] = $avg;
                $orderData[$id][ORDER_QTY] = $totalQty;
                $orderData[$id][ORDER_COMMIT] = $totalCommit;
                $orderData[$id][ORDER_PNL] = $totalPNL;
            }
        }

        $orderData = array_values($orderData);
        usort($orderData, function ($a, $b) {
            return $a[ORDER_TIME] - $b[ORDER_TIME];
        });

        foreach ($orderData as $order) {
            if ($this->orderModel->is_exist([[[ORDER_BINANCE, '=', $order[ORDER_BINANCE]]]])) {
                $this->orderModel->edit([
                    DATA_KEY => [[[ORDER_BINANCE, '=', $order[ORDER_BINANCE]]]],
                    DATA_EDITOR => $order
                ]);
            } else {
                $this->orderModel->add([$order]);
            }
        }

        $leng = count($orderData);
        if ($leng > 0) {
            $actionEditData[ACTION_FIRST_PRICE] = $orderData[0][ORDER_PRICE];
            $actionEditData[ACTION_LAST_PRICE] = $orderData[$leng - 1][ORDER_PRICE];
        }

        //['commit' => $commit, "pnl" => $PNL, 'position_qty' => $qty, 'position_price' => $avgPrice]
        $commission = $this->calCommit($action);

        $actionEditData[ACTION_COMMIT] = $commission['commit'];
        $actionEditData[ACTION_PNL] = $commission['pnl'];

        $realPNL = $commission['pnl'] - $commission['commit'];
        $budget = doubleval($positionQty) * doubleval($positionPrice);
        $eventProfit = $budget > 0 ? (($realPNL) * 100 / $budget) : 0;

        $actionEditData[ACTION_EVENTPROFIT] = $eventProfit;

        if ($positionQty == 0) {
            $actionEditData[ACTION_PENDING] = 0;
            if ($realPNL > 0) {
                $actionEditData[ACTION_STATUS] = ACTION_STATUS_TAKEPROFIT;
            } else {
                $actionEditData[ACTION_STATUS] = ACTION_STATUS_STOPLOSS;
            }
        }

        $this->actionModel->edit([
            DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
            DATA_EDITOR => $actionEditData,
        ]);

        return Reply::make(true, 'Success', $actionEditData);
    }

    public function cancleOrder($symbol, $orderId)
    {
        return $this->query('/fapi/v1/order', 'DELETE', ['symbol' => $symbol, 'orderId' => $orderId]);
    }

    /**
     * Get all open order
     */
    public function getAllOrder($symbol)
    {
        return $this->query('/fapi/v1/openOrders', 'GET', ['symbol' => $symbol]);
    }

    /**
     * Get all trades of a symbol
     * @return data: [
     *    {
     *      "buyer": false,
     *      "commission": "-0.07819010",
     *      "commissionAsset": "USDT",
     *      "id": 698759,
     *      "maker": false,
     *      "orderId": 25851813,
     *      "price": "7819.01",
     *      "qty": "0.002",
     *      "quoteQty": "15.63802",
     *      "realizedPnl": "-0.91539999",
     *      "side": "SELL",
     *      "positionSide": "SHORT",
     *      "symbol": "BTCUSDT",
     *      "time": 1569514978020
     *    }
     *  ]
     */
    public function getAllTrade($symbol, $startTime = null, $endTime = null)
    {
        $params = ['symbol' => $symbol];
        $trades = [];
        if ($startTime != null) $params['startTime'] = $startTime;
        if ($endTime != null) $params['endTime'] = $endTime;

        $tradeGet = $this->query('/fapi/v1/userTrades', 'GET', $params);
        if (!$tradeGet['result']) return $tradeGet;
        $tradeGet = (array)$tradeGet['data'];
        if (isset($tradeGet['msg']) || $tradeGet['msg'] == null) unset($tradeGet['msg']);
        $leng = count($tradeGet);
        $limit = 10;
        $trades = $tradeGet;
        while ($leng > 0 && $limit > 0) {
            $limit--;
            $lastTime = $tradeGet[$leng - 1]['time'] + 1;
            $params['startTime'] = $lastTime;
            $tradeGet = $this->query('/fapi/v1/userTrades', 'GET', $params);
            if (!$tradeGet['result']) return $tradeGet;
            $tradeGet = (array)$tradeGet['data'];
            if (isset($tradeGet['msg']) || $tradeGet['msg'] == null) unset($tradeGet['msg']);
            $leng = count($tradeGet);
            $trades = array_merge($trades, $tradeGet);
        }

        return Reply::make(true, 'success', $trades);
    }

    /**
     * Cancle all order
     */
    public function cancleAllOrder($symbol)
    {
        #cancal all order
        $delResult = $this->query('/fapi/v1/allOpenOrders', 'DELETE', ['symbol' => $symbol]);
        if (!$delResult['result']) return $delResult;
        return $delResult;
    }

    /**
     * Cancle all takeprofit and stoploss orders
     */
    public function cancleTakeStop($symbol)
    {
        $orders = $this->getAllOrder($symbol);
        if (!$orders['result']) return $orders;
        $orders = $orders['data'];
        foreach ((array)$orders as $order) {
            if ($order['type'] == 'TAKE_PROFIT_MARKET' || $order['type'] == 'STOP_MARKET' || $order['type'] == 'STOP' || $order['type'] == 'TAKE_PROFIT') {
                $result = $this->cancleOrder($symbol, $order['orderId']);
                if (!$result['result']) return $result;
            }
        }
        return Reply::make(true, "All Takeprofit/Stopoloss were cancled");
    }

    /**
     * Cancle all non-stoploss and non-takeprofit orders
     */
    public function cancleOrders($symbol)
    {
        $orders = $this->getAllOrder($symbol);
        if (!$orders['result']) return $orders;
        $orders = $orders['data'];
        foreach ((array)$orders as $order) {
            if ($order['type'] == 'TAKE_PROFIT_MARKET' || $order['type'] == 'STOP_MARKET' || $order['type'] == 'STOP' || $order['type'] == 'TAKE_PROFIT') {
                continue;
            } else {
                $result = $this->cancleOrder($symbol, $order['orderId']);
                if (!$result['result']) return $result;
            }
        }
        return Reply::make(true, "All Takeprofit/Stopoloss were cancled");
    }


    public function setMargin($symbol, $margin)
    {

        // Check if margin is set or not. If was set, ignore

        if (isset($this->currentMargin[$symbol]) && $this->currentMargin[$symbol] == $margin) {
            return Reply::make(true, 'Success');
        }
        echo $this->account->{ACCOUNT_NAME} . "Set margin $symbol: $margin \n";
        $result = $this->query('/fapi/v1/leverage', 'POST', ['symbol' => $symbol, 'leverage' => $margin]);
        if (!$result['result']) {
            $result = $this->query('/fapi/v1/leverage', 'POST', ['symbol' => $symbol, 'leverage' => $margin]);
            if (!$result['result']) return $result;
        }
        $this->currentMargin[$symbol] = $margin;

        return Reply::make(true, 'Success');
    }


    public function setMarginType($symbol)
    {
        echo $this->account->{ACCOUNT_NAME} . "Set margin $symbol CROSSED\n";
        $result = $this->query('/fapi/v1/marginType', 'POST', ['symbol' => $symbol, 'marginType' => 'CROSSED']);
        if (!$result['result']) return $result;
    }





    public function liveStream()
    {


        $errorLog = '';
        $refreshTime = time();

        try {

            $sp = $this->open_socket($errorLog);
            while (true) {

                if (!$sp || feof($sp)) {

                    $ms = 'Lost connection with Binance (' . $this->account->{ACCOUNT_NAME} . ')' . $errorLog;
                    echo $ms . "\n";
                    Telegram::send(TELE_ICON_ERROR . ' ' . $ms, TELE_REAL_ERROR);
                    echo "Try connect socket again\n";
                    $sp = $this->open_socket($errorLog);
                    if (!$sp || feof($sp)) {
                        echo "Socket not running sleep 15 seconds\n";
                        sleep(15);
                    }
                } else {
                    $data = websocket_read($sp, $errorLog);
                    if ($data) {
                        $this->catchEvent($data);
                    }

                    if (time() - $refreshTime > 1800) {
                        $refreshTime = time();
                        $this->query('/fapi/v1/listenKey', 'PUT');
                    }
                }
            }
        } catch (\Exception $th) {
            $ms = 'Exception Lost connection to market stream' . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . ' ' . $ms, TELE_REAL_ERROR);
        }
    }

    private function open_socket(&$errstr)
    {
        $keyId = $this->query('/fapi/v1/listenKey', 'POST');
        if (!$keyId['result']) {
            echo $keyId['message'] . "\n";
            return false;
        }
        $keyId = $keyId['data']['listenKey'];
        $sp = binancer_open($this->stream, "ssl://" . $this->stream . ':443',  "/ws/" . $keyId, [], $errstr, 10);
        return $sp;
    }

    private function catchEvent($ev)
    {
        // echo $ev . "\n";
        if ($ev == '') return;
        $response = json_decode($ev, true);
        if (json_last_error() != JSON_ERROR_NONE) return Reply::make(false, 'Data is not a json');

        $action = $response['e'];
        $time = $response['T'];

        if ($action == 'ORDER_TRADE_UPDATE' && isset($response['o'])) {

            $symbol = get($response['o']['s'], null);
            $price = doubleval($response['o']['ap']);
            $side = get($response['o']['S'], null);
            $type = get($response['o']['o'], null);
            $id = get($response['o']['i'], null);
            $status = get($response['o']['x'], null);
            $stopPrice = get($response['o']['sp'], null);
            $rp = get($response['o']['rp'], null);
            $qty = get($response['o']['z'], null);
            $commit = doubleval(get($response['o']['n'], null));

            $addData = [

                ORDER_SIDE => $side,
                ORDER_PRICE => $price,
                ORDER_TYPE => $type,
                ORDER_SYMBOL => $symbol,
                ORDER_ACCOUNT => $this->account->{ACCOUNT_ID},
                ORDER_BINANCE => $id,
                ORDER_DATA => $ev,
                ORDER_STATUS =>  $status,
                ORDER_STOP_PRICE => $stopPrice,
                ORDER_PNL => $rp,
                ORDER_QTY => $qty,
                ORDER_COMMIT => $commit,
            ];

            $actionData = $this->actionModel->read([[[ACTION_SYMBOL, '=', $symbol], [ACTION_ACCOUNT, '=', $this->account->{ACCOUNT_ID}], [ACTION_PENDING, '=', 1]]]);

            if ($actionData['result'] && isset($actionData['data'][0])) {
                $actionEvent = $actionData['data'][0];
            }

            $existOrder = $this->orderModel->read([[[ORDER_BINANCE, '=', $id]]]);
            if (!$existOrder['result']) return $existOrder;

            if (isset($existOrder['data'][0])) {

                $existOrder = $existOrder['data'][0];
                $addData[ORDER_PNL] = doubleval($addData[ORDER_PNL]) + doubleval($existOrder->{ORDER_PNL});
                $addData[ORDER_COMMIT] = doubleval($addData[ORDER_COMMIT]) + doubleval($existOrder->{ORDER_COMMIT});
                $addData[ORDER_DATA] = $addData[ORDER_DATA] . ",\n" . $existOrder->{ORDER_DATA};

                $this->orderModel->edit([
                    DATA_KEY => [[[ORDER_BINANCE, '=', $id]]],
                    DATA_EDITOR => $addData,
                ]);
            } else {
                if (isset($actionEvent))  $addData[ORDER_ACTION] = $actionEvent->{ACTION_ID};
                $addData[ORDER_TIME]  = $time;
                $this->orderModel->add([$addData]);
            }



            if (isset($actionEvent) && $price > 0) {

                $this->actionModel->edit([
                    DATA_KEY => [[[ACTION_ID, '=', $actionEvent->{ACTION_ID}]]],
                    DATA_EDITOR => [
                        ACTION_EVENTPROFIT => $this->calEventProfit($actionEvent)
                    ]
                ]);

                $actionId = $actionEvent->{ACTION_ID};
                $actionType = $actionEvent->{ACTION_TYPE};
                $flow = $actionEvent->{ACTION_FLOW};

                if ($addData[ORDER_QTY] >= $actionEvent->{ACTION_MATCHED_QTY} && $actionEvent->{ACTION_STATUS} != ACTION_STATUS_RELEASE_PENDING) {
                    if ($actionType == ACTION_TYPE_LONG && $side == 'SELL') {

                        $pnlData = $this->calCommit($actionEvent);
                        $commit = $pnlData['commit'];
                        $pnl = $pnlData['pnl'];
                        $status = $pnl > $commit;
                        $budget = doubleval($actionEvent->{ACTION_MATCHED_PRICE}) * doubleval($actionEvent->{ACTION_MATCHED_QTY});
                        $package = doubleval($actionEvent->{ACTION_BUDGET});
                        $totalBudget = doubleval($actionEvent->{ACTION_BUDGET_USED});
                        $profit = $budget > 0 ? ($pnl * 100 / $budget) : 0;
                        $realPNL = $pnl - $commit;
                        $eventProfit = $budget > 0 ? (($realPNL) * 100 / $budget) : 0;
                        $realProfit = $package > 0 ? (($realPNL) * 100 / $package) : 0;
                        $totalProfit = $totalBudget > 0 ? (($realPNL) * 100 / $totalBudget) : 0;
                        $profitOnActiveBudget = $actionEvent->{ACTION_BUDGET_ACTIVE} > 0 ? (($realPNL) * 100 / $actionEvent->{ACTION_BUDGET_ACTIVE}) : 0;

                        #cancal all order
                        $delResult = $this->cancleAllOrder($symbol);

                        $arrangeResult = $this->autoArrange($symbol, $realPNL);
                        if(!$arrangeResult['result']){
                            $ms = TELE_ICON_WARNING . " [" . $this->account->{ACCOUNT_NAME} . "] " . $arrangeResult['message'];
                            Telegram::send($ms, $this->teleGrError, $this->teleBot);
                        }

                        $this->actionModel->edit([
                            DATA_KEY => [[[ACTION_ID, '=', $actionId]]],
                            DATA_EDITOR => [
                                ACTION_SELL_PRICE => $price,
                                ACTION_SELL_TIME => $time,
                                ACTION_PENDING => '0',
                                ACTION_STATUS => $status ? ACTION_STATUS_TAKEPROFIT : ACTION_STATUS_STOPLOSS,
                                ACTION_PROFIT => $profit,
                                ACTION_EVENTPROFIT => $eventProfit,
                                ACTION_REALPROFIT => $realProfit,
                                ACTION_PNL => $pnl,
                                ACTION_COMMIT => $commit,
                                ACTION_TOTALPROFIT => $totalProfit,
                            ]
                        ]);



                        $ms = "============================="
                            . "\n" . ($status ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS) . " " . $this->account->{ACCOUNT_NAME} . " - TỔNG KẾT"
                            . "\nSymbol: " . $symbol
                            . "\nBắt đầu: " . date("d/m/Y H:i:s", $actionEvent->{ACTION_CHART} / 1000)
                            . "\nKết thúc: " . date("d/m/Y H:i:s", $time / 1000)
                            . "\nLoại vị thế: " . ($actionType == ACTION_TYPE_SHORT ? 'Short' : 'Long')
                            . "\nFlow: " . $flow
                            . "\nVốn đầu tư: " . $actionEvent->{ACTION_BUDGET_ACTIVE}
                            . "\nPhase tối đa: " . $actionEvent->{ACTION_PHASE}
                            . "\nMargin: x" . $actionEvent->{ACTION_MARGIN}
                            . "\nLợi nhuận ròng: " . round($realPNL * 1000) / 1000 . " USDT"
                            . "\nLợi nhuận trên vốn ĐT: " . round($profitOnActiveBudget * 1000) / 1000 . "%"
                            . "\nTông vốn: " . round($totalBudget * 1000) / 1000 . " USDT"
                            . "\nLợi nhuận trên tổng vốn: " . ($realPNL > 0 ? "+" : "") . round($totalProfit * 1000) / 1000 . "%"
                            . "\n=============================";
                        Telegram::send($ms, $this->teleGrNotice, $this->teleBot);
                        if ($this->teleGrSummary != null) {
                            foreach ($this->teleGrSummary as $gr) {
                                Telegram::send($ms, $gr, $this->teleBot);
                            }
                        }
                    }



                    if ($actionType == ACTION_TYPE_SHORT && $side == 'BUY') {

                        $pnlData = $this->calCommit($actionEvent);
                        $commit = $pnlData['commit'];
                        $pnl = $pnlData['pnl'];
                        $status = $pnl > $commit;
                        $budget = doubleval($actionEvent->{ACTION_MATCHED_PRICE}) * doubleval($actionEvent->{ACTION_MATCHED_QTY});
                        $package = doubleval($actionEvent->{ACTION_BUDGET});
                        $totalBudget = doubleval($actionEvent->{ACTION_BUDGET_USED});
                        $profit = $budget > 0 ? ($pnl * 100 / $budget) : 0;
                        $realPNL = $pnl - $commit;
                        $eventProfit = $budget > 0 ? (($realPNL) * 100 / $budget) : 0;
                        $realProfit = $package > 0 ? (($realPNL) * 100 / $package) : 0;
                        $totalProfit = $totalBudget > 0 ? (($realPNL) * 100 / $totalBudget) : 0;
                        $profitOnActiveBudget = $actionEvent->{ACTION_BUDGET_ACTIVE} > 0 ? (($realPNL) * 100 / $actionEvent->{ACTION_BUDGET_ACTIVE}) : 0;

                        #cancal all order
                        $delResult = $this->cancleAllOrder($symbol);

                        $arrangeResult = $this->autoArrange($symbol, $realPNL);
                        if(!$arrangeResult['result']){
                            $ms = TELE_ICON_WARNING . " [" . $this->account->{ACCOUNT_NAME} . "] " . $arrangeResult['message'];
                            Telegram::send($ms, $this->teleGrError, $this->teleBot);
                        }

                        $this->actionModel->edit([
                            DATA_KEY => [[[ACTION_ID, '=', $actionId]]],
                            DATA_EDITOR => [
                                ACTION_SELL_PRICE => $price,
                                ACTION_SELL_TIME => $time,
                                ACTION_PENDING => '0',
                                ACTION_STATUS => $status ? ACTION_STATUS_TAKEPROFIT : ACTION_STATUS_STOPLOSS,
                                ACTION_PROFIT => $profit,
                                ACTION_EVENTPROFIT => $eventProfit,
                                ACTION_REALPROFIT => $realProfit,
                                ACTION_PNL => $pnl,
                                ACTION_COMMIT => $commit,
                                ACTION_TOTALPROFIT => $totalProfit,
                                ACTION_INTERVAL => $time - $actionEvent->{ACTION_CHART}
                            ]
                        ]);



                        $ms = "============================="
                            . "\n" . ($status ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS) . " " . $this->account->{ACCOUNT_NAME} . " - TỔNG KẾT"
                            . "\nSymbol: " . $symbol
                            . "\nBắt đầu: " . date("d/m/Y H:i:s", $actionEvent->{ACTION_CHART} / 1000)
                            . "\nKết thúc: " . date("d/m/Y H:i:s", $time / 1000)
                            . "\nLoại vị thế: " . ($actionType == ACTION_TYPE_SHORT ? 'Short' : 'Long')
                            . "\nFlow: " . $flow
                            . "\nVốn đầu tư: " . $actionEvent->{ACTION_BUDGET_ACTIVE}
                            . "\nPhase tối đa: " . $actionEvent->{ACTION_PHASE}
                            . "\nMargin: x" . $actionEvent->{ACTION_MARGIN}
                            . "\nLợi nhuận ròng: " . round($realPNL * 1000) / 1000 . " USDT"
                            . "\nLợi nhuận trên vốn ĐT: " . round($profitOnActiveBudget * 1000) / 1000 . "%"
                            . "\nTông vốn: " . round($totalBudget * 1000) / 1000 . " USDT"
                            . "\nLợi nhuận trên tổng vốn: " . ($realPNL > 0 ? "+" : "") . round($totalProfit * 1000) / 1000 . "%"
                            . "\n=============================";
                        Telegram::send($ms, $this->teleGrNotice, $this->teleBot);
                        if ($this->teleGrSummary != null) {
                            foreach ($this->teleGrSummary as $gr) {
                                Telegram::send($ms, $gr, $this->teleBot);
                            }
                        }
                    }
                }

                if ($addData[ORDER_QTY] == $actionEvent->{ACTION_ORDER_QTY}) {

                    $editData = [
                        ACTION_LAST_PRICE => $price,
                        ACTION_MATCHED_TIME => $time,
                    ];

                    if ($actionEvent->{ACTION_FIRST_PRICE} == null) $editData[ACTION_FIRST_PRICE] = $price;

                    $this->actionModel->edit([
                        DATA_KEY => [[[ACTION_ID, '=', $actionId]]],
                        DATA_EDITOR => $editData
                    ]);

                    if ($actionType == ACTION_TYPE_LONG && $side == 'BUY') {
                        $ms = TELE_ICON_MATCHED . " [" . $this->account->{ACCOUNT_NAME} . "] #" . $symbol
                            . " Matched Phase " . $actionEvent->{ACTION_ORDER_PHASE}
                            . "\n- Time: " . date("d/m/Y H:i:s")
                            . "\n- Price: " . $price
                            . "\n- Flow: " . $flow;
                        Telegram::send($ms, $this->teleGrNotice, $this->teleBot);
                        if ($this->teleGrSummary != null) {
                            foreach ($this->teleGrSummary as $gr) {
                                Telegram::send($ms, $gr, $this->teleBot);
                            }
                        }
                    }

                    if ($actionType == ACTION_TYPE_SHORT && $side == 'SELL') {
                        $ms = TELE_ICON_MATCHED . " [" . $this->account->{ACCOUNT_NAME} . "] #" . $symbol
                            . " Matched Phase " . $actionEvent->{ACTION_ORDER_PHASE}
                            . "\n- Time: " . date("d/m/Y H:i:s")
                            . "\n- Price: " . $price
                            . "\n- Flow: " . $flow;
                        Telegram::send($ms, $this->teleGrNotice, $this->teleBot);
                        if ($this->teleGrSummary != null) {
                            foreach ($this->teleGrSummary as $gr) {
                                Telegram::send($ms, $gr, $this->teleBot);
                            }
                        }
                    }
                }
            }
        }


        if ($action == 'ACCOUNT_UPDATE' && isset($response['a']) && isset($response['a']['P'])) {

            $positions = $response['a']['P'];

            foreach ($positions as $position) {
                $symbol = get($position['s'], null);
                $qty = doubleval(get($position['pa'], null));
                $price = doubleval($position['ep']);

                $actionData = $this->actionModel->read([[[ACTION_SYMBOL, '=', $symbol], [ACTION_ACCOUNT, '=', $this->account->{ACCOUNT_ID}], [ACTION_PENDING, '=', 1]]]);

                if ($actionData['result'] && isset($actionData['data'][0])) {
                    $actionEvent = $actionData['data'][0];
                    $status = $actionEvent->{ACTION_STATUS};

                    if ($status != ACTION_STATUS_STOP_PENDING && $qty == 0) {
                        $this->actionModel->edit([
                            DATA_KEY => [[[ACTION_ID, '=', $actionEvent->{ACTION_ID}]]],
                            DATA_EDITOR => [
                                ACTION_STATUS => ACTION_STATUS_STOP_PENDING,
                            ]
                        ]);
                        $status = ACTION_STATUS_STOP_PENDING;
                    }

                    if ($status == ACTION_STATUS_PENDING || $status == ACTION_STATUS_PHASE_PENDING || $status == ACTION_STATUS_RELEASE_PENDING) {
                        $this->actionModel->edit([
                            DATA_KEY => [[[ACTION_ID, '=', $actionEvent->{ACTION_ID}]]],
                            DATA_EDITOR => [
                                ACTION_MATCHED_PRICE => $price,
                                ACTION_MATCHED_QTY => $qty > 0 ? $qty : -$qty,
                            ]
                        ]);
                    }
                }
            }
        }
    }


    public function stopService($symbol, $second = 5)
    {

        Telegram::send(TELE_ICON_ERROR . " [" . $this->account->{ACCOUNT_NAME} . "] #" . $symbol
            . " Stop Trading "
            . "\n- Time: " . date("d/m/Y H:i:s"), $this->teleGrError, $this->teleBot);

        Models::get('Admin/Trades')->edit([
            DATA_KEY => [[[TRADE_ACCOUNT, '=', $this->account->{ACCOUNT_ID}], [TRADE_SYMBOL, '=', $symbol]]],
            DATA_EDITOR => [TRADE_STOP_TIME => time()],
        ]);

        $pid = pcntl_fork();
        if ($pid == -1) {
            echo "Can not fork";
            return;
        } else if ($pid == 0) {
            sleep($second);
            $result = exec('sudo systemctl stop binance_event@' . $symbol . '_' . $this->account->{ACCOUNT_ID} . ' 2>&1');
            die();
        }
        return $pid;
    }

    private function calCommit($event)
    {
        $id = $event->{ACTION_ID};
        $type = $event->{ACTION_TYPE} == ACTION_TYPE_LONG ? 'BUY' : 'SELL';
        $commit = 0;
        $PNL = 0;

        $postitionQty = 0;
        $avgPrice = 0;

        $result = $this->orderModel->read([[[ORDER_ACTION, '=', $id]]]);
        if ($result['result']) {
            foreach ($result['data'] as $data) {
                $commit += doubleval($data->{ORDER_COMMIT});
                $PNL += doubleval($data->{ORDER_PNL});

                if ($type == $data->{ORDER_SIDE}) {
                    $avgPrice = ($postitionQty * $avgPrice + doubleval($data->{ORDER_QTY}) * doubleval($data->{ORDER_PRICE})) / ($postitionQty + doubleval($data->{ORDER_QTY}));
                    $postitionQty += doubleval($data->{ORDER_QTY});
                } else {
                    $postitionQty -= doubleval($data->{ORDER_QTY});
                }
            }
        }

        return ['commit' => $commit, "pnl" => $PNL, 'position_qty' => $postitionQty, 'position_price' => $avgPrice];
    }


    private function getEma5($symbol)
    {

        if (!isset($this->strategyCfg[$symbol])) {
            $trade = $this->tradesModel->read([[[TRADE_ACCOUNT, '=', $this->account->{ACCOUNT_ID}], [TRADE_SYMBOL, '=', $symbol]]]);
            if (!$trade['result'] || !isset($trade['data'][0])) return Reply::make(false, 'Can not find Trade');
            $trade = $trade['data'][0];

            $strategyId = $trade->{TRADE_STRATEGY};

            $strategy = $this->strategyModel->read([[[STRATEGY_ID, '=', $strategyId]]]);
            if (!$strategy['result'] || !isset($strategy['data'][0])) return Reply::make(false, 'Can not find Strategy');
            $this->strategyCfg[$symbol] = $strategy['data'][0];
        }

        $baseProfitOn = $this->strategyCfg[$symbol]->{STRATEGY_BASEPROFIT_BASEON};

        if ($baseProfitOn == 'ema5_3m') {
            $khung3m0 = $this->Candle3mModel->read([[
                [CANDLE_3M_SYMBOL, '=', $symbol],
            ]], function ($db) {
                $db->orderBy(CANDLE_3M_CLOSE_TIME, 'DESC')->limit(1);
            });
            if (!$khung3m0['result']) return $khung3m0;
            if (!isset($khung3m0['data'][0])) return Reply::make(true, 'success', 0);
            $ema5 = doubleval($khung3m0['data'][0]->{CANDLE_3M_EMA5});
            return Reply::make(true, 'success', $ema5);
        }

        if ($baseProfitOn == 'ema5_1m') {
            $khung1m0 = $this->Candle1mModel->read([[
                [CANDLE_1M_SYMBOL, '=', $symbol],
            ]], function ($db) {
                $db->orderBy(CANDLE_1M_CLOSE_TIME, 'DESC')->limit(1);
            });
            if (!$khung1m0['result']) return $khung1m0;
            if (!isset($khung1m0['data'][0])) return Reply::make(true, 'success', 0);
            $ema5 = doubleval($khung1m0['data'][0]->{CANDLE_1M_EMA5});
            return Reply::make(true, 'success', $ema5);
        }

        if ($baseProfitOn == 'ema5_15m') {
            $khung15m0 = $this->Candle15mModel->read([[
                [CANDLE_15M_SYMBOL, '=', $symbol],
            ]], function ($db) {
                $db->orderBy(CANDLE_15M_CLOSE_TIME, 'DESC')->limit(1);
            });
            if (!$khung15m0['result']) return $khung15m0;
            if (!isset($khung15m0['data'][0])) return Reply::make(true, 'success', 0);
            $ema5 = doubleval($khung15m0['data'][0]->{CANDLE_15M_EMA5});
            return Reply::make(true, 'success', $ema5);
        }

        return Reply::make(true, 'success', 0);
    }

    private function calEventProfit($event)
    {

        $commit = $this->calCommit($event);
        $realPNL = $commit['pnl'] - $commit['commit'];
        $budget = $commit['position_qty'] * $commit['position_price'];
        $eventProfit = 0;
        if ($budget > 0) {
            $eventProfit = ($realPNL) * 100 / $budget;
        }
        return $eventProfit;
    }


    private function autoArrange($actionSymbol, $profit=0)
    {

        $startTime = microtime(true);

        $account = $this->accountModel->read([[[ACCOUNT_ID, '=', $this->account->{ACCOUNT_ID}]]]);

        if (!$account['result'] || !isset($account['data'][0])) {
            return Reply::make(false, 'No account');
        }
        $account = $account['data'][0];

        if ($account->{ACCOUNT_COMPOUND} == 1) {
            foreach ([0, 1, 2] as $key) {
                $info = $this->getAccountInfo();
                if ($info['result']) {

                    $trades = $this->tradesModel->read([[[TRADE_ACCOUNT, '=', $this->account->{ACCOUNT_ID}]]]);
                    if (!$trades['result']) return $trades;
                    $trades = $trades['data'];

                    $reserve = get($account->{ACCOUNT_RESERVE}, 0);

                    $used = 0;

                    foreach ($trades as $trade) {
                        $used += doubleval($trade->{TRADE_BUDGET});
                    }

                    $info = $info['data'];
                    $balance = doubleval($info['totalWalletBalance']);
                    $balance = $balance * (100 - $reserve) / 100;

                    $free = $balance - $used;

                    if ($free <= 0) {
                        $ms = TELE_ICON_WARNING . " [" . $this->account->{ACCOUNT_NAME} . "] auto arrange fail"
                            . "\n- Symbol: " . $actionSymbol
                            . "\n- Free: " . round($free * 1000) / 1000 . " $"
                            . "\n- Time: " . date("d/m/Y H:i:s");
                        Telegram::send($ms, $this->teleGrError, $this->teleBot);

                        return Reply::make(true, 'Free less than 0');
                    }

                    $added = floor($free * 1000 / count($trades)) / 1000;

                    foreach ($trades as $trade) {
                        $result = $this->tradesModel->edit([
                            DATA_KEY => [[[TRADE_ID, '=', $trade->{TRADE_ID}]]],
                            DATA_EDITOR => [TRADE_BUDGET => doubleval($trade->{TRADE_BUDGET}) + $added]
                        ]);
                        if (!$result['result']) return $result;
                    }

                    $ms = TELE_ICON_WARNING . " [" . $this->account->{ACCOUNT_NAME} . "] auto arrange successfully"
                        . "\n- Symbol: " . $actionSymbol
                        . "\n- Free: " . round($free * 1000) / 1000 . " $"
                        . "\n- Added: " . round($added * 1000) / 1000 . " $"
                        . "\n- Excute Time: " . round((microtime(true) - $startTime) * 100) / 100 . ' s'
                        . "\n- Time: " . date("d/m/Y H:i:s");
                    Telegram::send($ms, $this->teleGrError, $this->teleBot);


                    return Reply::make(true, 'Success');
                }

                return Reply::make(false, 'Auto arrange failed. Can not get user data after 3 times');
            }
        }else{

            $trade = $this->tradesModel->read([[
                [TRADE_ACCOUNT, '=', $this->account->{ACCOUNT_ID}],
                [TRADE_SYMBOL, '=', $actionSymbol]
            ]]);
            if(!$trade['result'] || !isset($trade['data'][0])) return Reply::make(false, 'can not find trade '. $actionSymbol);
            $trade = $trade['data'][0];

            if($trade->{TRADE_COMPOUND} == 1){
                $autoArrangeResult = $this->tradesModel->edit([
                    DATA_KEY => [[[TRADE_ID, '=', $trade->{TRADE_ID}]]],
                    DATA_EDITOR => [TRADE_BUDGET => doubleval($trade->{TRADE_BUDGET}) + $profit]
                ]);

                if(!$autoArrangeResult['result']) return $autoArrangeResult;

                $ms = TELE_ICON_WARNING . " [" . $this->account->{ACCOUNT_NAME} . "] update budget successfully"
                . "\n- Symbol: " . $actionSymbol
                . "\n- Added: " . round($profit * 1000) / 1000 . " $"
                . "\n- Excute Time: " . round((microtime(true) - $startTime) * 100) / 100 . ' s'
                . "\n- Time: " . date("d/m/Y H:i:s");
                Telegram::send($ms, $this->teleGrError, $this->teleBot);

                return Reply::make(true, 'Success');
            }
        }

        return Reply::make(true, 'Compound is diabled');
    }
}

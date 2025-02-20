<?php

namespace App\Http\Controllers\Admin;

use App\Crawler\Caculator\Ema;
use App\Crawler\Caculator\EmaRealtime;
use App\Crawler\Caculator\Signal;
use App\Crawler\Caculator\SignalRealtime;
use App\Crawler\History\Candle;
use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use App\Model\Admin\Requests;


class WatchlistController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Watchlist');
        $this->tableName = WATCHLIST_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[WL_ID] = true;

        // if (!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $user = Auth::user();
        $datas[WL_UID] = $user->{AUTHEN_ID};
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        exec('sudo systemctl restart price_1s');
        exec('sudo systemctl restart phoenix_alert');
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[WL_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        exec('sudo systemctl restart price_1s');
        exec('sudo systemctl restart phoenix_alert');
        Reply::finish(true, 'success', $datas);
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
        exec('sudo systemctl restart price_1s');
        exec('sudo systemctl restart phoenix_alert');
        Reply::finish(true, 'success', $datas);
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][WL_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
        exec('sudo systemctl restart price_1s');
        exec('sudo systemctl restart phoenix_alert');
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas =  $this->mainModel->keyToCondition($datas);
        if(!Checker::validate($datas[WL_SYMBOL], 'Word')) return Reply::make(false, 'Wrong format');
        exec('sudo systemctl stop realtime_kline@' . $datas[WL_SYMBOL]);
        exec('sudo systemctl stop price_1s');
        $dropResult = $this->mainModel->drop([$datas]);
        exec('sudo systemctl start price_1s');
        exec('sudo systemctl restart phoenix_alert');
        sleep(5);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $data) {
            if(!Checker::validate($data[WL_SYMBOL], 'Word')) return Reply::make(false, 'Wrong format');
            exec('sudo systemctl stop realtime_kline@' . $data[WL_SYMBOL]);
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        exec('sudo systemctl stop price_1s');
        $result = $this->mainModel->drop($datas);
        exec('sudo systemctl start price_1s');
        exec('sudo systemctl restart phoenix_alert');
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        if (isset($datas[DATA_EDITOR][WL_SYMBOL])) unset($datas[DATA_EDITOR][WL_SYMBOL]);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key => $data) {
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        if (isset($datas[DATA_EDITOR][WL_SYMBOL])) unset($datas[DATA_EDITOR][WL_SYMBOL]);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        if (Role::checkMonitor()) {
            $readResult = $this->mainModel->read([$datas]);
        } else {
            $readResult = $this->mainModel->read([$datas], function ($db) {
                $db->where(WL_UID, '=', Auth::user()->{AUTHEN_ID});
            });
        }

        Reply::finish($readResult);
    }

    /**
     * Calculate Low-high, low-low, high-high avg for tracking
     */
    public function readCalAvg(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        if (Role::checkAdmin()) {
            $readResult = $this->mainModel->read([$datas]);
        } else {
            $readResult = $this->mainModel->read([$datas], function ($db) {
                $db->where(WL_UID, '=', Auth::user()->{AUTHEN_ID});
            });
        }

        $data = $readResult['data'];


        $Frame = [
            '1D-3D' => [
                'Model' => Models::get('Crawler/Candle_1d'),
                'CloseTime' => CANDLE_1D_CLOSE_TIME,
                'Time' => 3,
                'timeInterval' => 86400 * 1000,
                'Symbol' => CANDLE_1D_SYMBOL,
                'High' => CANDLE_1D_HIGH,
                'Low' => CANDLE_1D_LOW,

            ],
            '4H-3D' => [
                'Model' => Models::get('Crawler/Candle_4h'),
                'CloseTime' => CANDLE_4H_CLOSE_TIME,
                'Time' => 3,
                'timeInterval' => 4 * 3600 * 1000,
                'Symbol' => CANDLE_4H_SYMBOL,
                'High' => CANDLE_4H_HIGH,
                'Low' => CANDLE_4H_LOW,

            ],
            '1D-7D' => [
                'Model' => Models::get('Crawler/Candle_1d'),
                'CloseTime' => CANDLE_1D_CLOSE_TIME,
                'Time' => 7,
                'timeInterval' => 86400 * 1000,
                'Symbol' => CANDLE_1D_SYMBOL,
                'High' => CANDLE_1D_HIGH,
                'Low' => CANDLE_1D_LOW,

            ],
            '4H-7D' => [
                'Model' => Models::get('Crawler/Candle_4h'),
                'CloseTime' => CANDLE_4H_CLOSE_TIME,
                'Time' => 7,
                'timeInterval' => 4 * 3600 * 1000,
                'Symbol' => CANDLE_4H_SYMBOL,
                'High' => CANDLE_4H_HIGH,
                'Low' => CANDLE_4H_LOW,

            ],
        ];

        $result = [];


        foreach ($Frame as $key => $row) {

            $result[$key] =  $this->CalAvg($row);
        }







        foreach ($data as $row) {
            $symbol = $row->{WL_SYMBOL};
            $row->{'1d_high_low_avg3d'} = $result['1D-3D'][$symbol]['highlowval'];
            $row->{'1d_high_high_avg3d'} = $result['1D-3D'][$symbol]['highhighval'];
            $row->{'1d_low_low_avg3d'} = $result['1D-3D'][$symbol]['lowlowval'];



            $row->{'4h_high_low_avg3d'} = $result['4H-3D'][$symbol]['highlowval'];
            $row->{'4h_high_high_avg3d'} = $result['4H-3D'][$symbol]['highhighval'];
            $row->{'4h_low_low_avg3d'} = $result['4H-3D'][$symbol]['lowlowval'];



            $row->{'1d_high_low_avg7d'} = $result['1D-7D'][$symbol]['highlowval'];
            $row->{'1d_high_high_avg7d'} = $result['1D-7D'][$symbol]['highhighval'];
            $row->{'1d_low_low_avg7d'} = $result['1D-7D'][$symbol]['lowlowval'];


            $row->{'4h_high_low_avg7d'} = $result['4H-7D'][$symbol]['highlowval'];
            $row->{'4h_high_high_avg7d'} = $result['4H-7D'][$symbol]['highhighval'];
            $row->{'4h_low_low_avg7d'} = $result['4H-7D'][$symbol]['lowlowval'];
        }


        Reply::finish(true, 'success', $data);
    }


    private function CalAvg($Config)
    {
        $model = $Config['Model'];

        $time = floor(microtime(true) / 86400) * 86400 * 1000;

        $data_Candle = $model->read([[[$Config['CloseTime'], '>',  $time - $Config['Time'] * 86400 * 1000 - $Config['timeInterval']]]], function ($db) use ($Config) {
            $db->orderBy($Config['CloseTime'], 'ASC');
        });

        if (!$data_Candle['result']) return $data_Candle;
        $data_Candle = $data_Candle['data'];

        $arrayData = [];

        foreach ($data_Candle as $key => $row) {
            $arrayData[$row->{$Config['Symbol']}][] = $row;
        }


        $result = [];

        foreach ($arrayData as $key => $row) {

            $highlowval = 0;
            $count = 0;

            $lowlowsum = 0;
            $lowlowcount = 0;

            $highhighsum = 0;
            $highhighcount = 0;

            for ($i = 0; $i < count($row); $i++) {
                if ($i != 0) {


                    $highlowval += (($row[$i]->{$Config['High']} - $row[$i]->{$Config['Low']}) * 100) / $row[$i]->{$Config['Low']};
                    $count++;

                    $lowlowval = (($row[$i]->{$Config['Low']} - $row[$i - 1]->{$Config['Low']}) * 100) / $row[$i]->{$Config['Low']};

                    if ($lowlowval < 0) {
                        $lowlowsum += $lowlowval;
                        $lowlowcount++;
                    }

                    $highhighval = (($row[$i]->{$Config['High']} - $row[$i - 1]->{$Config['High']}) * 100) / $row[$i]->{$Config['High']};

                    if ($highhighval > 0) {
                        $highhighsum += $highhighval;
                        $highhighcount++;
                    }
                }
            }

            if ($count > 0) $highlowval = $highlowval / $count;
            if ($lowlowcount > 0) $lowlowsum = $lowlowsum / $lowlowcount;
            if ($highhighcount > 0) $highhighsum = $highhighsum / $highhighcount;



            $result[$key] = [
                'highlowval' => round($highlowval, 2),
                'lowlowval' => round($lowlowsum, 2),
                'highhighval' =>  round($highhighsum, 2),
            ];
        }


        return $result;
    }

    public function mapping()
    {
        $mapData = [];
        // $mapData[WL_STRATEGY] = Edge::mapping(Models::get('Admin/Strategies'), null, STRATEGY_ID, STRATEGY_NAME);
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[WL_SYMBOL, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{WL_ID} => $item->{WL_SYMBOL}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);

        if (!$responseData['result']) Reply::finish($responseData);

        foreach ($responseData['data'][DATA_TABLE] as $key => $val) {
            $responseData['data'][DATA_TABLE][$key]->{'crawler_service'} = Services::isActive('realtime_kline@' . $val->{WL_SYMBOL});
            $responseData['data'][DATA_TABLE][$key]->{'orderbook_service'} = Services::isActive('realtime_orderbook@' . $val->{WL_SYMBOL});
            $responseData['data'][DATA_TABLE][$key]->{'busd_service'} = Services::isActive('realtime_busd@' . $val->{WL_SYMBOL});
            // $responseData['data'][DATA_TABLE][$key]->{'lab_service'} = Services::isActive('check_event@'.$val->{WL_SYMBOL});
        }

        Reply::finish($responseData);
    }

    public function reloadAlert()
    {
        exec('sudo systemctl restart volatility_alert');
        Reply::finish(true, 'success');
    }



    // public function crawHistory(Request $request){
    //     set_time_limit(0);
    //     $symbol = $request->input('symbol');

    //     foreach(['1h', '15m', '3m', '1m', '4h'] as $interval){
    //         $result = Candle::craw($symbol, $interval, 1000, false);
    //         if(!$result['result']) return $result;
    //     }

    //     return Reply::make(true, 'success');

    // }

    // public function caculateEma(Request $request){
    //     set_time_limit(0);
    //     $symbol = $request->input('symbol');

    //     $startObject = [];

    //     foreach(['1m', '3m', '15m', '1h', '4h'] as $interval){
    //         foreach([5,9,12,13,26] as $N){
    //             echo "Caculate EMA$N $interval\n";
    //             $result = EmaRealtime::caculate($symbol, $interval, $N, $startObject);
    //             if(!$result['result']) return $result;
    //         }
    //         foreach([9,2,3,4,5] as $N){
    //             $result = SignalRealtime::caculate($symbol, $interval, $N, $startObject);
    //             if(!$result['result']) return $result;
    //         }
    //     }

    //     return Reply::make(true, 'success');

    // }

    // public function startService(Request $request){
    //     set_time_limit(0);
    //     $symbol = $request->input('symbol');
    //     $result = exec('sudo php '.base_path().'/artisan candle_start '.$symbol);
    //     $this->mainModel->edit([
    //         DATA_KEY => [[[WL_SYMBOL, '=', $symbol]]],
    //         DATA_EDITOR => [WL_TIME => time()]
    //     ]);
    //     return Reply::make(true, 'success', $result);

    // }

    public function stopService(Request $request)
    {
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl stop realtime_kline@' . $symbol);
        $this->mainModel->edit([
            DATA_KEY => [[[WL_SYMBOL, '=', $symbol]]],
            DATA_EDITOR => [WL_STOPTIME => time()]
        ]);
        exec('sudo systemctl restart phoenix_alert');
        return Reply::make(true, 'success', $result);
    }

    public function restartService(Request $request)
    {
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl restart realtime_kline@' . $symbol);
        $this->mainModel->edit([
            DATA_KEY => [[[WL_SYMBOL, '=', $symbol]]],
            DATA_EDITOR => [WL_TIME => time(), WL_STOPTIME => null]
        ]);
        exec('sudo systemctl restart phoenix_alert');
        return Reply::make(true, 'success', $result);
    }



    public function stopOrderBookService(Request $request)
    {
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl stop realtime_orderbook@' . $symbol);
        return Reply::make(true, 'success', $result);
    }

    public function restartOrderBookService(Request $request)
    {
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl restart realtime_orderbook@' . $symbol);
        return Reply::make(true, 'success', $result);
    }

    public function stopBusdService(Request $request)
    {
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl stop realtime_busd@' . $symbol);
        return Reply::make(true, 'success', $result);
    }

    public function restartBusdService(Request $request)
    {
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl restart realtime_busd@' . $symbol);
        return Reply::make(true, 'success', $result);
    }

    // public function stopEventService(Request $request){
    //     $symbol = $request->input('symbol');
    //     $result = exec('sudo systemctl stop check_event@'.$symbol);
    //     return Reply::make(true, 'success', $result);

    // }

    // public function startEventService(Request $request){
    //     $symbol = $request->input('symbol');
    //     $result = exec('sudo systemctl restart check_event@'.$symbol);
    //     return Reply::make(true, 'success', $result);

    // }

    public function cleanData(Request $request)
    {
        $symbol = $request->input('symbol');
        $result = Models::get('Admin/Candle_1m')->drop([[[CANDLE_1M_SYMBOL, '=', $symbol]]]);
        if (!$result['result']) return $result;
        $result = Models::get('Admin/Candle_3m')->drop([[[CANDLE_3M_SYMBOL, '=', $symbol]]]);
        if (!$result['result']) return $result;
        $result = Models::get('Admin/Candle_15m')->drop([[[CANDLE_15M_SYMBOL, '=', $symbol]]]);
        if (!$result['result']) return $result;
        $result = Models::get('Admin/Candle_1h')->drop([[[CANDLE_1H_SYMBOL, '=', $symbol]]]);
        if (!$result['result']) return $result;
        $result = Models::get('Admin/Candle_4h')->drop([[[CANDLE_4H_SYMBOL, '=', $symbol]]]);
        if (!$result['result']) return $result;

        return Reply::make(true, 'success');
    }


     //$$uploading$$
    public function uploader_upload(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Metadata']);
        $size = $file['size'] + 1024;
        $disk = resolve('Models')->getModel('Uploader/Uploader_disks')->read(
            [[[DISK_TYPE, '=', 'local'], [DISK_FREE, '>', $size], [DISK_ACTIVE, '=', 1]]],
            function ($db) {
                $db->orderBy(DISK_WEIGHT, 'DESC');
            }
        );
        $option = ['condition' => ['validation' => 'required|image']];

        if (!$disk['result']) Reply::finish($disk);
        if (!isset($disk['data'][0])) Reply::finish(false, 'All disk is fulled');

        $diskName = $disk['data'][0]->{DISK_NAME};
        $uploader = $disk['data'][0]->{DISK_UPLOADER};

        return FileFunc::upload($uploader, $diskName, $this->tableName, $column, Auth::user()->{AUTHEN_ID}, $option);
    }


    public function uploader_read(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        // $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $result = FileFunc::read(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_delete(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, 'No File Metadata');
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        // $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};

        $result = FileFunc::delete(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_get(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        return FileFunc::get($this->tableName, $column, Auth::user()->{AUTHEN_ID});
    }

    public function uploader_publish(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        // $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $ulink = $fileInfo[FILE_UPLOADER] . '/api/uploader/public/read?file=' . $file;
        return redirect($ulink);
    }
    
    //$$/uploading$$




}
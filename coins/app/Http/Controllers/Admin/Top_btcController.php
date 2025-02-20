<?php

namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Top_btcController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Crawler/Top_btc');
        $this->tableName = TOP_BTC_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[TOP_BTC_ID] = true;

        if (!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, '');
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas]);
        Reply::finish($readResult);
    }

    public function mapping()
    {
        $mapData = [];
        Reply::finish(true, 'Success', $mapData);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if (!$responseData['result']) Reply::finish($responseData);

        $filters = $request->input('data_filter');
        $db = $this->mainModel->db();
        $this->mainModel->buildFilter($db, $filters, 'and', true);

        $filterData = $db->sum(TOP_BTC_BTC);
        $totalBTC =  $filterData;
        $responseData['message'] = $totalBTC;
        Reply::finish($responseData);
    }

    public function getData(Request $request)
    {

        $time = $request->input('time');

        $Data = $this->mainModel->read([[[TOP_BTC_TIME, '=', $time]]]);
        if (!$Data['result']) return $Data;
        $Data = $Data['data'];


        return Reply::make(true, 'success', $Data);
    }

    public function getDataChart(Request $request)
    {

        $address = $request->input('address');

        $Data = $this->mainModel->read([[[TOP_BTC_ADDRESS, '=', $address]]]);
        if (!$Data['result']) return $Data;
        $Data = $Data['data'];


        return Reply::make(true, 'success', $Data);
    }
}

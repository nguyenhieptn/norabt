<?php

namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Funding_feeController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Funding_fee');
        $this->tableName = FUNDING_FEE_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[FUNDING_FEE_ID] = true;

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
        $mapData[FUNDING_FEE_SYMBOL] = Edge::mapping(Models::get('Admin/Watchlist'), null, WL_SYMBOL, WL_SYMBOL, null, function ($db) {
            $db->orderBy(WL_SYMBOL, 'DESC');
        });
        $mapData[FUNDING_FEE_ACCOUNT] = Edge::mapping(Models::get('Admin/Accounts'), null, ACCOUNT_ID, ACCOUNT_NAME);
        Reply::finish(true, 'Success', $mapData);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if (!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function get(Request $request)
    {
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);

        $selectColumn = array_keys($this->mainModel->struct);

        $result = $this->mainModel->read($data, function ($db) use ($limit, $skip, $orderBy, $orderAsc) {
            if ($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if ($skip !== null) $db->skip($skip);
            if ($limit !== null) $db->limit($limit);
        }, false, $selectColumn);

        return $result;
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
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


    //

    //




}

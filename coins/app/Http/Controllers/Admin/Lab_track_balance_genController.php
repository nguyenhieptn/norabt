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


class Lab_track_balance_genController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_track_balance_gen');
        $this->tableName = LAB_TRACK_BALANCE_GEN_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_TRACK_BALANCE_GEN_ID] = true;

        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ''); 
        
    }

    public function getExistId(Request $request)
    {
        $result = $this->mainModel->read([], false , false, [
            LAB_TRACK_BALANCE_GEN_ACCOUNT,
        ]);

        return $result;
    }

    public function test(Request $request)
    {
        set_time_limit(0);
        $account_id = $request->input('account_id', '');
        $offset = $request->input('offset', '');

        $account_id = intval($account_id);
        $offset = intval($offset);


        if($account_id == '')  Reply::finish(false , 'no account id', '' );


        $investDatas = [];
        $unrealizeDatas = [];
        $marginBalanceDatas = [];
        $balanceDatas = [];

        $ModelLabTrackBalance = Models::get('Admin/Lab_track_balance');
        // $DataBalance =  $ModelLabTrackBalance->read([[ [LAB_TRACK_BL_ACCOUNT , '=' , $account_id] ]], function ($db) use ($offset) {
        //     $db->limit(500000)->offset($offset);
  
        // } );
        $DataBalance =  $ModelLabTrackBalance->read([[ [LAB_TRACK_BL_ACCOUNT , '=' , $account_id] ]] );

        if (!$DataBalance['result']) return $DataBalance;
        $DataBalance = $DataBalance['data'];

        foreach ($DataBalance as $k => $row ) {
            if($k % 200 == 0){
                $time = intval($row->{LAB_TRACK_BL_TIME});

                $investDatas[] = [
                    'x' => $time,
                    'y' => floatval($row->{LAB_TRACK_BL_INVEST})
                ];
                $unrealizeDatas[] = [
                    'x' => $time,
                    'y' => floatval($row->{LAB_TRACK_BL_UNREALIZE})
                ];
                $marginBalanceDatas[] = [
                    'x' => $time,
                    'y' => floatval($row->{LAB_TRACK_BL_MARGIN_BL})
                ];
                $balanceDatas[] = [
                    'x' => $time,
                    'y' => floatval($row->{LAB_TRACK_BL_BALANCE})
                ];
            }
          

        
        }
        $data = [
            'invest' => $investDatas,
            'unrelize' => $unrealizeDatas,
            'maginBalance' => $marginBalanceDatas,
            'balance' => $balanceDatas
        ];
        Reply::finish(true , 'success', $data );



    }

    
    public function read(Request $request)
    {
        set_time_limit(0);
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);


        if($account_id == '')  Reply::finish(false , 'no account id', '' );

        $readResult =  $this->mainModel->read([[[LAB_TRACK_BALANCE_GEN_ACCOUNT, '=', $account_id]]]);

        // $ModelLabTrackBalance = Models::get('Admin/Lab_track_balance');
        // $DataBalance =  $ModelLabTrackBalance->read([[ [LAB_TRACK_BL_ACCOUNT , '=' , $account_id] ]] );

        // if (!$DataBalance['result']) return $DataBalance;
        // $DataBalance = $DataBalance['data'];

        // $readResult['message'] = count($DataBalance) ;

        Reply::finish($readResult);


    }

    public function check(Request $request)
    {
      
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);


        if($account_id == '')  Reply::finish(false , 'no account id', '' );

        $readResult =  $this->mainModel->count([[[LAB_TRACK_BALANCE_GEN_ACCOUNT, '=', $account_id]]]);

        Reply::finish($readResult);


    }

    public function updateData(Request $request){
        set_time_limit(0);

       
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);


        if($account_id == '')  Reply::finish(false , 'no account id', '' );

        $command = 'php ' . base_path() . '/artisan gen_chart_balance ' . $account_id . ' > /dev/null &' ;
        // print($command);
        // die();
        exec($command);
        Reply::finish(true, 'Success', 'ok');
    }
 





}
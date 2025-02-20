<?php

namespace App\Console\Commands;


use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Console\Command;

class Gen_chart_balance extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'gen_chart_balance {accountId}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Command description';

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

       
  
        set_time_limit(0);

       
        $this->mainModel = Models::get('Admin/Lab_track_balance_gen');
        $account_id = intval($this->argument('accountId'));


        if($account_id == '')  Reply::finish(false , 'no account id', '' );


        $ModelLabTrackBalance = Models::get('Admin/Lab_track_balance');

        $this->mainModel->drop([[[LAB_TRACK_BALANCE_GEN_ACCOUNT, '=', $account_id]]]);
        print("get data \n");
        $DataBalance =  $ModelLabTrackBalance->read([[ [LAB_TRACK_BL_ACCOUNT , '=' , $account_id] ]] );

        if (!$DataBalance['result']) return $DataBalance;
        $DataBalance = $DataBalance['data'];
        print("get data success \n");

        $investDatas = [];
        $unrealizeDatas = [];
        $marginBalanceDatas = [];
        $balanceDatas = [];
        //??
        $maxPerUreBa = 0;
        $daymaxPerUreBa = 0;
        $maxPerInBa = 0;
        $daymaxPerInBa = 0;

        $top20Dic = [];
        $top20 = [];
        $top20DicInvest = [];
        $top20Invest = [];

        $SLBalane = [];
        print("hangle data \n");
        foreach ($DataBalance as $row) {
            $time = intval($row->{LAB_TRACK_BL_TIME});


            $SLBalane[$time] = [
                'time'=> $time,
                'balance' => floatval($row->{LAB_TRACK_BL_BALANCE})
            ];


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

            $perUreBa = floatval($row->{LAB_TRACK_BL_UNREALIZE}) / floatval($row->{LAB_TRACK_BL_BALANCE});
            $perInBa = floatval($row->{LAB_TRACK_BL_INVEST}) / floatval($row->{LAB_TRACK_BL_BALANCE});

            $startOfDay = floor($time / 86400000) * 86400000;

            if (!isset($top20Dic[$startOfDay])) {

                $top20Dic[$startOfDay] = [
                    'x' => $time,
                    'y' => $perUreBa
                ];
            } else {
                if ($perUreBa < $top20Dic[$startOfDay]['y']) {
                    $top20Dic[$startOfDay] = [
                        'x' => $time,
                        'y' => $perUreBa
                    ];
                }
            }

            if (!isset($top20DicInvest[$startOfDay])) {
                $top20DicInvest[$startOfDay] = [
                    'x' => $time,
                    'y' => $perInBa
                ];
            } else {
                if ($perInBa > $top20DicInvest[$startOfDay]['y']) {
                    $top20DicInvest[$startOfDay] = [
                        'x' => $time,
                        'y' => $perInBa
                    ];
                }
            }

            if (!isset($maxPerUreBa)) {
                $maxPerUreBa = $perUreBa;
                $daymaxPerUreBa = $time;
                $maxPerInBa = $perInBa;
                $daymaxPerInBa = $time;

            } else {
                if ($maxPerUreBa > $perUreBa) {
                    $maxPerUreBa = $perUreBa;
                    $daymaxPerUreBa = $time;
                }
                if ($maxPerInBa < $perInBa) {
                    $maxPerInBa = $perInBa;
                    $daymaxPerInBa = $time;
                }

            }

        
        }


        print("end for data \n");

    

        $max_invest =[
            'max_invest' => $maxPerInBa ,
            'day_max_invest' => $daymaxPerInBa
        ];



        $max_drawdown = [
            'max_drawdown' => $maxPerUreBa ,
            'day_max_drawdown' => $daymaxPerUreBa
        ];

        
        
        $top20 = array_values($top20Dic);
        usort($top20, function ($item1, $item2) {
            return $item1['y'] <=> $item2['y'];
        });
        $top20 = array_slice($top20,0,19);


        // $top20 = array_values($top20Dic);
        // $ys1 = array_column($top20, 'y');
        // array_multisort($ys1, SORT_DESC, $top20);
        // $top20 = array_slice($top20, 0, 19);


        // $top20Invest = array_values($top20DicInvest);
        // usort($top20Invest, function ($item1, $item2) {
        //     return $item1['y'] <=> $item2['y'];
        // });
        // $top20Invest = array_slice($top20Invest,0,19);

        $top20Invest = array_values($top20DicInvest);
        $ys = array_column($top20Invest, 'y');
        array_multisort($ys, SORT_DESC, $top20Invest);
        $top20Invest = array_slice($top20Invest, 0, 19);

        

        $ModelLabResult = Models::get('Admin/Lab_results');

        print("fhdkshkfd data \n");
        $out =  $ModelLabResult->read([[ [LAB_RESULT_ACCOUNT , '=' , $account_id] , [LAB_RESULT_STATUS , '=' , LAB_RESULT_STATUS_STOPLOSS ]]] , function ($db)  {
            $db->orderBy(LAB_RESULT_SELL_TIME, 'ASC');
      
        },false,[
            LAB_RESULT_ID,
            LAB_RESULT_ORDER_TIME,
            LAB_RESULT_TYPE,
            LAB_RESULT_PROFIT,
            LAB_RESULT_REAL_PROFIT,
            LAB_RESULT_STATUS,
            LAB_RESULT_SYMBOL,
            LAB_RESULT_PENDING,
            LAB_RESULT_PARAMS,
            LAB_RESULT_STRATEGY,
            LAB_RESULT_CAMPAIGN,
            LAB_RESULT_SELL_TIME,
            LAB_RESULT_CHART,
            LAB_RESULT_PHASE,
            LAB_RESULT_REAL_PNL,
            LAB_RESULT_FLOW,
            LAB_RESULT_CONTAINER,
            LAB_RESULT_EVENT_PROFIT
        ]);
        // $out =  $ModelLabResult->read([[ [LAB_RESULT_ACCOUNT , '=' , $account_id] , [LAB_RESULT_STATUS , '=' , LAB_RESULT_STATUS_STOPLOSS ]]] );

        
        if (!$out['result']) return $out;
        //
       
        $out = $out['data'];
        $outT = array();

        foreach ($out as $k => $v) {
            $outT[$k] = clone $v;
        }


        
   
        $countLen = count($out);
        foreach ($out as $row) {
            $time;
            $y = 1;
      
            while (true) {
                // $a = intval($row->{LAB_RESULT_SELL_TIME}) - $y *60000;
                $a = intval($row->{LAB_RESULT_SELL_TIME}) - $y *1000;
            
                if( isset($SLBalane[$a])){
                    $time = $a;
                    break;
                }

                $y = $y+1  ;
            }

            if (  isset($SLBalane[$time])) {
                $row->{'balance'} = $SLBalane[$time]['balance'];
                $row->{'per'} =$row->{LAB_RESULT_REAL_PNL} * 100 / (floatval($SLBalane[$time]['balance']));


                foreach ($SLBalane as $key => $value) {
                        if (intval($key) > $time) {
                            // debugger
                            if (floatval($SLBalane[$key]['balance']) >= floatval($SLBalane[$time]['balance'])) {
                                $row->{'time_reach'} = $key;
                                $row->{'balance_reach'} = $SLBalane[$key]['balance'];

                                break;
                            }

                        }
                }

            
            }

      
        }
        //
        print("out ok \n");
        $lastTimeReach = false;
        $lastTimeReachInd = 1;
        foreach($outT as $i => $row){
            if ($i == 0) {
                // $time = intval($outT[$i]->{LAB_RESULT_SELL_TIME}) - 60000;

                $time;
                $y1 = 1;
                while (true) {
                    $a1 = intval($row->{LAB_RESULT_SELL_TIME}) - $y1 *1000;
                
                    if( isset($SLBalane[$a1])){
                        $time = $a1;
                        break;
                    }
    
                    $y1 = $y1+1  ;
                }
                
          
                
                if ( isset($SLBalane[$time])) {
                    $outT[$i]->{'balance'} = $SLBalane[$time]['balance'];
                    $outT[$i]->{'balancePre'} = $SLBalane[$time]['balance'] + floatval($outT[$i]->{LAB_RESULT_REAL_PNL});
                    $outT[$i]->{'timePre'} = $outT[$i]->{LAB_RESULT_SELL_TIME};
                    $outT[$i]->{'perT'} = $outT[$i]->{LAB_RESULT_REAL_PNL} * 100 / (floatval($SLBalane[$time]['balance']));

                 
          
                    foreach ($SLBalane as $key => $value) {
                        if (intval($key) > $time ) {
                            
                            if (floatval($SLBalane[$key]['balance']) >= floatval($SLBalane[$time]['balance'])) {
                                $outT[$i]->{'time_reach'} = $key;
                                $outT[$i]->{'balance_reach'} = $SLBalane[$key]['balance'];

                    
                                $lastTimeReach =  true;
                                
                                break;
                               
                            }else{
                                $lastTimeReach =  false;
                            }

                        }
                    }

                
              

                }
            }else{
              
                
                $timeNow = intval($outT[$i]->{LAB_RESULT_SELL_TIME}) ;

                // $timeNowSL = intval($outT[$i]->{LAB_RESULT_SELL_TIME}) - 60000;
                $timeNowSL = 0;
                $y2 = 1;
                while (true) {
                    $a2 = intval($row->{LAB_RESULT_SELL_TIME}) - $y2 *1000;
                
                    if( isset($SLBalane[$a2])){
                        $timeNowSL = $a2;
                        break;
                    }
    
                    $y2 = $y2+1  ;
                }
                $isLoop = true;
                $step = 1;
          
                while($isLoop){
                    if($i - $step < 0){
                        $isLoop = false;
                    }
                    if(isset( $outT[$i - $step]->{'time_reach'}) ){
                        
                        $isLoop = false;
                    }else{

                        $step += 1;
                    }
                    
                }
              
          
          
               if(!$lastTimeReach){

                   
                    $ind = $i - $lastTimeReachInd;
                    $lastTimeReachInd += 1;
                    if(isset($SLBalane[$timeNowSL])){
                        $balancePre = $SLBalane[$timeNowSL]['balance'] + floatval($outT[$i]->{LAB_RESULT_REAL_PNL});
                        if($balancePre < floatval($outT[$ind]->{'balancePre'}) ){
                
                            $outT[$ind]->{'balancePre'} = $balancePre;
                            $outT[$ind]->{'timePre'} = $outT[$i]->{LAB_RESULT_SELL_TIME};
                        }
                    }
                  

                   
               }else{
                    $timePrevious = intval($outT[$i - $step]->{'time_reach'});

                    if($timeNow < $timePrevious){
                    
                        if( isset($SLBalane[$timeNowSL])){
                            
                            $balancePre = $SLBalane[$timeNowSL]['balance'] + floatval($outT[$i]->{LAB_RESULT_REAL_PNL});
                            if($balancePre < floatval($outT[$i - $step]->{'balancePre'}) ){
                   
                                $outT[$i - $step]->{'balancePre'} = $balancePre;
                                $outT[$i - $step]->{'timePre'} = $outT[$i]->{LAB_RESULT_SELL_TIME};
                            }
                        }
                    }else{
             
                        if ( isset($SLBalane[$timeNowSL]) ) {
                          
                            $outT[$i]->{'balance'} = $SLBalane[$timeNowSL]['balance'];
                            $outT[$i]->{'balancePre'} = $SLBalane[$timeNowSL]['balance'] + floatval($outT[$i]->{LAB_RESULT_REAL_PNL});
                            $outT[$i]->{'timePre'} = $outT[$i]->{LAB_RESULT_SELL_TIME};
                            
                            $outT[$i]->{'perT'} = $outT[$i]->{LAB_RESULT_REAL_PNL} * 100 / (floatval($SLBalane[$timeNowSL]['balance']));
    
                            foreach ($SLBalane as $key => $value) {
                                if (intval($key) > $timeNowSL) {
                                    if (floatval($SLBalane[$key]['balance']) >= floatval($SLBalane[$timeNowSL]['balance'])) {
                                        $outT[$i]->{'time_reach'} = $key;
                                        $outT[$i]->{'balance_reach'} = $SLBalane[$key]['balance'];
                                        
                                      
                                        $lastTimeReach =  true;
                                        break;
                                    }
        
                                }else{
                                 
                                    $lastTimeReach = false;
                                }
                            }
    
    
                        }
               
                    }
               }
                
             
                
              
                
                
            
            }
        }
        print("outT ok \n");
        $FlagSL = [];

        
        foreach ($out as $row) {
            $FlagSL[] = [
                'x' => $row->{LAB_RESULT_SELL_TIME},
                'title' => round($row->{'per'} ,2) . '%' ,
                'text' => round($row->{'per'} ,2) . '%',
            ];
        }

        $temp = $top20;
        usort($temp, function ($item1, $item2) {
            return $item1['x'] <=> $item2['x'];
        });
        print("temp data \n");
        if (count($DataBalance) !== 0) {
            $timeT = [];

            foreach ($temp as $row) {

                if($row['y'] < -10/100){
                    $timeT[] = $row['x'];
                }
            }

       
            for ($i = 0; $i < count($DataBalance) - 1; $i++) {

                if (in_array($DataBalance[$i]->{LAB_TRACK_BL_TIME},$timeT)) {
                
                    if ($i !== 0 && $i !== count($DataBalance) - 1) {

                        for ($y = $i + 1; $y < count($DataBalance) - 1; $y++) {

                            $NowPerUreBa = floatval($DataBalance[$y]->{LAB_TRACK_BL_UNREALIZE}) / floatval($DataBalance[$y]->{LAB_TRACK_BL_BALANCE});
                            $NextPerUreBa = -10/100;

                            if ($NextPerUreBa <= $NowPerUreBa ) {

                                foreach($temp as &$item){
                                    if($item['x'] == $DataBalance[$i]->{LAB_TRACK_BL_TIME}){
                                        $item['right_y'] = $NowPerUreBa;
                                        $item['right_x'] = $DataBalance[$y]->{LAB_TRACK_BL_TIME};
                                    }
                                }
                            
                            
                                break;
                            }




                        }
                        for ($y = $i - 1; $y > 0; $y--) {

                            $NowPerUreBa = floatval($DataBalance[$y]->{LAB_TRACK_BL_UNREALIZE}) / floatval($DataBalance[$y]->{LAB_TRACK_BL_BALANCE});
                            $NextPerUreBa = -10/100;

                            if ($NextPerUreBa <= $NowPerUreBa) {

                                foreach($temp as &$item){
                                    if($item['x'] == $DataBalance[$i]->{LAB_TRACK_BL_TIME}){
                                        $item['left_y'] = $NowPerUreBa;
                                        $item['left_x'] = $DataBalance[$y]->{LAB_TRACK_BL_TIME};
                                    }
                                }                   
                                break;
                            }




                        }

                    }

                }

            }


        }


        $top20Flag = [];

        foreach($temp as $item){
            $top20Flag[] = [
                'x' =>  $item['x'],     
                'title' =>  round($item['y'] * 100 ,2) . '%' ,
                'text' => round($item['y'] * 100 ,2) . '%'
            ];
        };

        print('add data to db');

        $addData = [
            LAB_TRACK_BALANCE_GEN_ACCOUNT => $account_id,
            LAB_TRACK_BALANCE_GEN_MAX_INVEST => json_encode($max_invest),
            LAB_TRACK_BALANCE_GEN_MAX_DRAWDOWN => json_encode($max_drawdown),

            LAB_TRACK_BALANCE_GEN_DD => json_encode($temp),
            LAB_TRACK_BALANCE_GEN_MI => json_encode($top20Invest),
            LAB_TRACK_BALANCE_GEN_SL => json_encode($out),
            LAB_TRACK_BALANCE_GEN_MD => json_encode($outT),

            LAB_TRACK_BALANCE_GEN_FLAGSL => json_encode($FlagSL),
            LAB_TRACK_BALANCE_GEN_TOP20FL => json_encode($top20Flag),

        ];
        
      
        $addResult = $this->mainModel->add([$addData]);

      
        

       
      
    }

   
}

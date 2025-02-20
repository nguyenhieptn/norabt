<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;



class System_alert extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'system_alert';

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

        $this->alarmCfg = Ctrl::get('system_alert', null);
        $this->alarmCfg = json_decode($this->alarmCfg, true);
        if($this->alarmCfg == null) $this->alarmCfg = [];
      
        $data = $this->getSystemInfo();

        $this->checkAlarm($data);

    

    

    }


    private function getSystemInfo()
    {
      
        $data = [
            'cpu' => 0,
            'ram' => 0,
            'swap' => 0,
            'disk' => 0,
            'total_ram' => 0,
            'total_swap' => 0,
            'total_disk' => 0,
        ];

        $o = [];
        $cmd = 'free -m';
        exec($cmd, $o, $rc);
        foreach ($o as $output) {
            if (preg_match('/^mem:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+).*$/mi', $output, $match)) {
                if((int) $match[1] > 0){
                    $data['ram'] = 100 - round((int) $match[6] * 100 / (int) $match[1]);
                    $data['total_ram'] = $match[1]*1024;
                }
            }
            if (preg_match('/^swap:\s+(\d+)\s+(\d+)\s+(\d+).*$/mi', $output, $match)) {
                if((int)$match[1] > 0){
                    $data['swap'] = round((int) $match[2] * 100 / (int) $match[1]);
                    $data['total_swap'] = $match[1]*1024;
                }
                
            }
        }

        $o = [];
        $cmd = 'top -b -n2 -p1 -d1';
        exec($cmd, $o, $rc);

        foreach ($o as $output) {
            if (preg_match('/^%cpu.*\s([\d\.]+)(?=\sid).*$/mi', $output, $match)) {
                $data['cpu'] = 100 - (int) round($match[1]);
            }
        }

        $o = [];
        $cmd = 'df -h /';
        exec($cmd, $o, $rc);
        foreach ($o as $output) {
            if (preg_match('/^.*\s([\d\.]+[TGMKB]+)\s*([\d\.]+[TGMKB]+)\s*([\d\.]+[TGMKB])\s*([\d]+)%.*$/mi', $output, $match)) {
                $data['disk'] = $match[4];
                $data['total_disk'] = $match[1];
            }
        }

        return $data;
    }

    private function checkAlarm($data){
        
        foreach($this->alarmCfg as $alarm){
            if(isset($alarm['active']) && $alarm['active']==0) continue;
           
            $checkResult = $this->checkCondition($data, $alarm['condition']);
           
            if($checkResult){
                 $this->makeAlert($alarm);
            }
        }
    }

    private function checkCondition($data, $condition){
        $result = true;
        foreach($condition as $con){
            $compareResult = $this->compare($data, $con);
            if($compareResult === null) return null;
            if(!$compareResult){
                $result = false;
                break;
            }

        }
        return $result;
    }

    private function compare($data, $condition){
       
        $col = $condition['object'];
        $com1 = $this->calCom1($data, $col);
        
        $logic = $condition['logic'];
        $com2 = $condition['value'];
        
        if($com1 === null || $com2 === null) return null;
        
        if($logic == '=') return $com1 == $com2;
        if($logic == '>') return $com1 > $com2;
        if($logic == '<') return $com1 < $com2;
        if($logic == '>=') return $com1 >= $com2;
        if($logic == '<=') return $com1 <= $com2;
    }


    private function calCom1($data, $col){

        if($col == 'cpu') {
            return intval($data['cpu']);
        }

        if($col == 'ram'){
            return intval($data['ram']);
        }
        if($col == 'swap'){
            return intval($data['swap']);
        }
        if($col == 'disk'){
            return intval($data['disk']);
        }

        return null;

    }

    private function makeAlert($alarm){
        $icon = $alarm['icon'];
        $content = $alarm['content'];
        $botId = $alarm['bot'];
        $groupId = $alarm['group'];
      
        Telegram::send($icon . $content, $groupId, $botId);
    }
}

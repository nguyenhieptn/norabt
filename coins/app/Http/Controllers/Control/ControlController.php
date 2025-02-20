<?php

namespace App\Http\Controllers\Control;

use App\Helpers\Admin\LabQuery;
use App\Helpers\Auth\Role;
use App\Helpers\Control\Ctrl;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use Illuminate\Support\Facades\Auth;
use App\Helpers\Uploader\FileFunc;


class ControlController extends Controller
{

    function __construct()
    {
        parent::__construct();
        $this->mainModel = $this->models->getModel('Control/Control');
        $this->viewblade = 'reactjs.reactjs';

        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[CONTROL_NAME] = true;
    }

    public function update(Request $request)
    {
        $datas = $request->all();
        if (!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
        foreach ($datas as $key => $value) {
            if (is_array($value)) {
                $query = Ctrl::set($key, $value, true);
            } else {
                $query = Ctrl::set($key, $value);
            }
            if (!$query['result']) return $query;
        }
        Reply::finish(true, 'success');
    }

    public function read(Request $request)
    {
        if (!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
        $datas = $request->input('keys');
        $result = Ctrl::gets($datas);
        return Reply::finish(true, 'Success', $result);
    }

    public function view()
    {
        if (!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
        return view($this->viewblade);
    }

    public function getSystemInfo()
    {
        if (!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);

        return $this->_getSystemInfo();
    }


    private function _getSystemInfo()
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
                if ((int) $match[1] > 0) {
                    $data['ram'] = 100 - round((int) $match[6] * 100 / (int) $match[1]);
                    $data['total_ram'] = $match[1] * 1024;
                }
            }
            if (preg_match('/^swap:\s+(\d+)\s+(\d+)\s+(\d+).*$/mi', $output, $match)) {
                if ((int)$match[1] > 0) {
                    $data['swap'] = round((int) $match[2] * 100 / (int) $match[1]);
                    $data['total_swap'] = $match[1] * 1024;
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

        return Reply::make(true, 'sucess', $data);
    }
}

<?php

namespace App\Console\Commands;

use App\Helpers\Admin\LabQuery;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;

class GetSystemInfo extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'getSystemInfo';

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

        $sysInfoModel = Models::get('Admin/System_info');

        $servers = $GLOBALS['LAB_REMOTE_SERVERS'];
        $addData = [];
        foreach ($servers as $server => $row) {
            $data = LabQuery::getSystemInfo($server);


            if ($data['result']) {
                $data = $data['data'];

                $needData = [
                    SYS_NAME => $server,
                    SYS_CPU => $data['cpu'],
                    SYS_RAM =>  $data['ram'],
                    SYS_SWAP =>  $data['swap'],
                    SYS_DISK =>  $data['disk'],
                    SYS_TOTAL_RAM =>  $data['total_ram'],
                    SYS_TOTAL_SWAP =>  $data['total_swap'],
                    SYS_TOTAL_DISK =>  $data['total_disk'],
                ];

                $addData[] = $needData;
            }else{
                $ms = TELE_ICON_ERROR . "[" . $server . "] " . $data['message'];
                Telegram::send($ms, TELE_SIMULATE, TELE_BOT_DEFAULT);
            }
        }

        if (count($addData) > 0) {
            $sysInfoModel->drop("All");
            $sysInfoModel->add($addData);
        }
    }
}

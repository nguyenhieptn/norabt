<?php

namespace App\Console\Commands;

use App\Helpers\Admin\LabQuery;
use App\Helpers\Admin\LabSocket;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Illuminate\Console\Command;

class GetNodeInfo extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'getNodeInfo';

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

        $nodeModel = Models::get('Admin/Lab_node');

        $nodes = $nodeModel->read([[[
            LAB_NODE_STATUS, '=', 'CONNECTED'
        ]]]);
        if(!$nodes['result']) return $nodes;
        $nodes= $nodes['data'];

        foreach ($nodes as $node) {
            $data = LabSocket::makeRemoteQuery($node->{LAB_NODE_NAME}, 'system', 'getInfo');
            if ($data['result']) {
                $data = $data['data'];
                $editData = [
                    LAB_NODE_RAM => $data['ram'],
                    LAB_NODE_CPU => $data['cpu'],
                    LAB_NODE_DISK => $data['disk'],
                    LAB_NODE_RAM_TOTAL => $data['total_ram'],
                    LAB_NODE_CPU_CORE => $data['total_cpu'],
                    LAB_NODE_DISK_TOTAL => $data['total_disk'],
                    LAB_NODE_VERSION => get($data['version'], '')
                ];
                $nodeModel->edit([
                    DATA_KEY => [[[LAB_NODE_ID, '=', $node->{LAB_NODE_ID}]]],
                    DATA_EDITOR => $editData
                ]);
            }else{
                if($data['message'] != 'division by zero'){
                    $ms = TELE_ICON_ERROR . "[" . $node->{LAB_NODE_NAME} . "] " . $data['message'];
                    Telegram::send($ms, TELE_SIMULATE, TELE_BOT_DEFAULT);
                }
            }
        }

        
    }
}

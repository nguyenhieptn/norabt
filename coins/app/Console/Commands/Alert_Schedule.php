<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

use App\Helpers\Admin\Telegram;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;

class Alert_Schedule extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'alert_schedule';

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
        $alertModel = Models::get('Admin/Schedule_alert');
        $rules = $alertModel->read([[ [SCHEDULE_AL_DONE, '=', 0] ]]);
        if(!$rules['result']) return $rules['result'];
        $rules = $rules['data'];

        $time = time();
        foreach($rules as $rule){
            if((doubleval($rule->{SCHEDULE_AL_TIME}) - doubleval($rule->{SCHEDULE_AL_BEFORE})*60) < $time ){
                $this->notificate($rule, $alertModel);
            }
            
        }

    }

    private function notificate($rule, $model){
        $this->makeAlert([
            'icon' => $rule->{SCHEDULE_AL_ICON},
            'content' => $rule->{SCHEDULE_AL_CONTENT},
            'bot' => $rule->{SCHEDULE_AL_BOTID},
            'group' => $rule->{SCHEDULE_AL_GROUPID}
        ]);

        $model->edit([
            DATA_KEY => [[[SCHEDULE_AL_ID, '=', $rule->{SCHEDULE_AL_ID}]]],
            DATA_EDITOR => [SCHEDULE_AL_DONE => 1]
        ]);

    }

    private function makeAlert($alarm)
    {
        $icon = $alarm['icon'];
        $content = $alarm['content'];
        $botId = $alarm['bot'];
        $groupId = $alarm['group'];
        echo "\n$content";
        Telegram::send($icon . $content, $groupId, $botId);
    }
}

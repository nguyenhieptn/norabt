<?php 
namespace App\Helpers\Notice;

use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use Illuminate\Support\Facades\Auth;

// use Minishlink\WebPush\WebPush;
// use Minishlink\WebPush\Subscription;



class Notice_helper {

    public static function add($uids, $content, $variable=[], $level='3', $action = null, $type=null){
        $noticeModel = Models::get('Notice/Notice');
        $addData = [];
        foreach($uids as $uid){
            $addData[] = [
                NOTICE_TIME => time(),
                NOTICE_UID => $uid,
                NOTICE_FIRE_UID => Auth::user()->{AUTHEN_ID},
                NOTICE_CONTENT =>  htmlspecialchars($content, ENT_QUOTES),
                NOTICE_VARIABLE => json_encode($variable),
                NOTICE_LEVEL => $level,
                NOTICE_SEEN => 0,
                NOTICE_ACTION => $action,
                NOTICE_TYPE => $type,
            ];
        }
        $noticeModel->add($addData, null, true);
    }

    public static function all($content, $variable=[], $level='3', $action = null, $type=null){
        $noticeModel = Models::get('Notice/Notice');
        $userModel = Models::get('Auth/Authentication');

        $done = 0;
        $step = 500;
        $finish = false;
        while (!$finish){
            $users = $userModel->read([[ 
                [AUTHEN_ACTIVE, '=', AUTHEN_ACTIVE_VERIFIED], 
                [AUTHEN_STATUS, '=', AUTHEN_STATUS_APPROVE] 
            ]], 
                function($db) use($done, $step){
                    $db->skip($done)->take($step);
                }
            );
            if(!$users['result']) return;
            $addData = [];
            foreach($users['data'] as $user){
                $addData[] = [
                    NOTICE_TIME => time(),
                    NOTICE_UID => $user->{AUTHEN_ID},
                    NOTICE_UNAME => $user->{AUTHEN_USERNAME},
                    NOTICE_FIRE_UID =>  Auth::user()->{AUTHEN_ID},
                    NOTICE_FIRE_UNAME => Auth::user()->{AUTHEN_USERNAME},
                    NOTICE_CONTENT =>  htmlspecialchars($content, ENT_QUOTES),
                    NOTICE_VARIABLE => json_encode($variable),
                    NOTICE_LEVEL => $level,
                    NOTICE_SEEN => 0,
                    NOTICE_ACTION => $action,
                    NOTICE_TYPE => $type,
                ];
            }
            if(count($addData) > 0){
                $noticeModel->add($addData, null, true, ['depend'=>false]);
                $done += $step;
            }else{
                $finish = true;
            }
        }
        
    }

    // public static function push($uid, $content){
    //     $publicKey = 'BAeaemC2MZdQSEZQ5Rpe-NHhY7QkWUaBO1EQGX-Z_dnreMy4n7JSV_USi8rnGt_ZTJlm_8vQI01-YS-tGkLaJvQ';
    //     $privateKey = 'J53qS0pAsQrKFuA1maIyb1g1HuvDO-DeR3SuMfNHENs';

    //     $auth = array(
    //         'VAPID' => array(
    //             'subject' => APP_TITLE,
    //             'publicKey' => $publicKey,
    //             'privateKey' => $privateKey
    //         ),
    //     );

    //     $noticeModel = resolve('Models')->getModel('Notice/Notice_web');
    //     $subscription = $noticeModel->read([[[WEB_NOTICE_UID, '=', $uid]]]);

    //     if(!$subscription['result']) return;
    //     $subscription = $subscription['data']->toArray();
    //     $subscription = array_map(function($item){return json_decode($item->{WEB_NOTICE_SUBSCRIPTION}, true);}, $subscription);
    //     $subscriptionObjs = array_map(function($item){return Subscription::create($item);}, $subscription);
    //     $webPush = new WebPush($auth);
    //     array_map(function($sub)use($webPush, $content){
    //         $webPush->sendNotification(
    //             $sub,
    //             json_encode($content)
    //         );
    //     }, $subscriptionObjs);
    //     $log=[];
    //     foreach ($webPush->flush() as $report) {
    //         $endpoint = $report->getRequest()->getUri()->__toString();
    //         if ($report->isSuccess()) {
    //              $log[] = "Message sent successfully for subscription {$endpoint}.";
    //         } else {
    //             $log[] = "Message failed to sent for subscription {$endpoint}: {$report->getReason()}";
    //         }
    //     }

    //     return Reply::make(true, 'Success', $log);

    // }

}

?>
<?php

namespace App\Http\Controllers\Mailer\api;

use App\Helpers\DB\Models;
use App\Helpers\Mailer\MailFactory;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Helpers\Request\Reply;
use App\Helpers\Token\JWToken;


class MailerController extends Controller
{

    function __construct()
    {
        parent::__construct();
        $this->mainModel = Models::get('Mailer/Mailer_config');
    }


    private function getPayload($request)
    {
        $token = $request->input('token', '');
        if ($token == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'token']);
        $payload = JWToken::payload($token);
        if ($payload === false) {
            Reply::finish(false, JWToken::getMessage());
        }
        return $payload;
    }



    public function send(Request $request)
    {
        try {
            //code...

            $payload = $this->getPayload($request);
            if ($payload->{'action'} != 'send') Reply::finish(false, ERROR_PERMISSION);

            $name = get($payload->{'name'}, null);
            $mailer = MailFactory::make($name);
            if (!$mailer) Reply::finish(false, MailFactory::getMessage());

            $options = $payload->{'options'};

            $mailerConfig = MailFactory::getConfig();

            $config = config('mail');

            if (!isset($options->{'from'})) $options->{'from'} = [$config['username'], $config['username']];

            if (!isset($options->{'to'}) || count((array) $options->{'to'}) == 0) Reply::finish(false, 'Define recipients email');

            $mailer->send(get($options->{'view'}, []), get($options->{'with'}, []), function ($message) use ($options) {
                $message->to((array)$options->{'to'})
                    ->subject(get($options->{'subject'}, APP_NAME))
                    ->from(...(array) $options->{'from'})
                    ->replyTo(...(array) $options->{'from'});

                if (isset($options->{'cc'})) {
                    $message->cc($options->{'cc'});
                }

                if (isset($options->{'html'})) {
                    if(isset($options->{'signature'})){
                        $options->{'html'} = $options->{'html'}.'<br/><br/><strong>'.$options->{'signature'}.'</strong>';
                    }
                    $message->setBody($options->{'html'}, 'text/html');
                }else{
                    Reply::finish(false, ERROR_UNDEFINE, ['data'=>'Body']);
                }
            });

            if (count($mailer->failures()) > 0) {
                $log = 'Can not send email to : ' . implode(', ', $mailer->failures());
                Models::get('Mailer/Mailer_result')->add([[
                    MRESULT_TO => implode(', ', (array)$options->{'to'}),
                    MRESULT_FROM => $options->{'from'}[0],
                    MRESULT_TIME => time(),
                    MRESULT_MAILER => $payload->{'name'},
                    MRESULT_CONTENT => htmlspecialchars($options->{'html'}, ENT_QUOTES),
                    MRESULT_RESULT => 0,
                    MRESULT_LOG => $log,
                ]]);
                Reply::finish(false, $log);
            }
            
            $result = Models::get('Mailer/Mailer_result')->add([[
                MRESULT_TO => implode(', ', (array) $options->{'to'}),
                MRESULT_FROM =>$options->{'from'}[0],
                MRESULT_TIME => time(),
                MRESULT_MAILER => $payload->{'name'},
                MRESULT_CONTENT => htmlspecialchars($options->{'html'}, ENT_QUOTES),
                MRESULT_RESULT => 1,
            ]]);

            if(!$result['result']) return $result;
            
            $updateData = [
                MAIL_USED => $mailerConfig->{MAIL_USED} + 1,
                MAIL_FREE => $mailerConfig->{MAIL_FREE} - 1,
            ];

            return $this->mainModel->edit([
                DATA_KEY => [[[MAIL_ID, '=', $mailerConfig->{MAIL_ID}]]],
                DATA_EDITOR => $updateData,
            ]);
            
            Reply::finish(true, 'Success');
        } catch (\Swift_TransportException $e) {
            Reply::finish(false, $e->getMessage());
        }
    }


    public function test(Request $request)
    {
        try {
            //code...
            $secure = $request->input('secure', '');
            if($secure != 'vietlinhvu007') return;

            $name = $request->input('name', null);
            $mailer = MailFactory::make($name);
            if (!$mailer) Reply::finish(false, MailFactory::getMessage());

            $options = (object)[
                'to' => $request->input('to', 'vietlinhvu007@gmail.com'),
                'html' => 'Test Email',
            ];

            $mailerConfig = MailFactory::getConfig();

            $config = config('mail');

            if (!isset($options->{'from'})) $options->{'from'} = [$config['username'], $config['username']];

            if (!isset($options->{'to'}) || count((array) $options->{'to'}) == 0) Reply::finish(false, 'Define recipients email');

            $mailer->send(get($options->{'view'}, []), get($options->{'with'}, []), function ($message) use ($options) {
                $message->to((array)$options->{'to'})
                    ->subject(get($options->{'subject'}, APP_NAME))
                    ->from(...(array) $options->{'from'})
                    ->replyTo(...(array) $options->{'from'});

                if (isset($options->{'cc'})) {
                    $message->cc($options->{'cc'});
                }

                if (isset($options->{'html'})) {
                    if(isset($options->{'signature'})){
                        $options->{'html'} = $options->{'html'}.'<br/><br/><strong>'.$options->{'signature'}.'</strong>';
                    }
                    $message->setBody($options->{'html'}, 'text/html');
                }else{
                    Reply::finish(false, ERROR_UNDEFINE, ['data'=>'Body']);
                }
            });

            if (count($mailer->failures()) > 0) {
                $log = 'Can not send email to : ' . implode(', ', $mailer->failures());
                Models::get('Mailer/Mailer_result')->add([[
                    MRESULT_TO => implode(', ', (array)$options->{'to'}),
                    MRESULT_FROM => $options->{'from'}[0],
                    MRESULT_TIME => time(),
                    MRESULT_MAILER => $name,
                    MRESULT_CONTENT => htmlspecialchars($options->{'html'}, ENT_QUOTES),
                    MRESULT_RESULT => 0,
                    MRESULT_LOG => $log,
                ]]);
                Reply::finish(false, $log);
            }
            
            $result = Models::get('Mailer/Mailer_result')->add([[
                MRESULT_TO => implode(', ', (array) $options->{'to'}),
                MRESULT_FROM =>$options->{'from'}[0],
                MRESULT_TIME => time(),
                MRESULT_MAILER => $name,
                MRESULT_CONTENT => htmlspecialchars($options->{'html'}, ENT_QUOTES),
                MRESULT_RESULT => 1,
            ]]);

            if(!$result['result']) return $result;
            
            $updateData = [
                MAIL_USED => $mailerConfig->{MAIL_USED} + 1,
                MAIL_FREE => $mailerConfig->{MAIL_FREE} - 1,
            ];

            return $this->mainModel->edit([
                DATA_KEY => [[[MAIL_ID, '=', $mailerConfig->{MAIL_ID}]]],
                DATA_EDITOR => $updateData,
            ]);
            
            Reply::finish(true, 'Success');
        } catch (\Swift_TransportException $e) {
            Reply::finish(false, $e->getMessage());
        }
    }


}

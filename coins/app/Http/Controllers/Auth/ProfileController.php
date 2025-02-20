<?php

namespace App\Http\Controllers\Auth;

use App\Helpers\Auth\AuthenticatesUsers;
use App\Helpers\DB\Models;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;

class ProfileController extends Controller
{
    var $permission;
    use AuthenticatesUsers;

    function __construct()
    {
        parent::__construct();
        $this->user = Auth::user();
        if(!$this->user) Reply::finish(false, ERROR_PERMISSION);
        $this->userModel = Models::get('Auth/Authentication');

    }


    /**
     *
     * function for user change name
     */

    public function update(Request $request)
    {
        $data = $request->input('data', null);
        if (is_null($data)) Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Data']);

        if (isset($data[AUTHEN_USERNAME])) {
            if ($data[AUTHEN_USERNAME] == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => AUTHEN_USERNAME]);
            if ($this->userModel->is_exist([[[AUTHEN_USERNAME, '=', $data[AUTHEN_USERNAME]]]])) Reply::finish(false, ERROR_DUPLICATE, ['data' => AUTHEN_USERNAME]);
        }

        if (isset($data[AUTHEN_EMAIL])) {
            if ($data[AUTHEN_EMAIL] == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => AUTHEN_EMAIL]);
            if ($this->userModel->is_exist([[[AUTHEN_EMAIL, '=', $data[AUTHEN_EMAIL]]]])) Reply::finish(false, ERROR_DUPLICATE, ['data' => AUTHEN_EMAIL]);
        }

        if (isset($data[AUTHEN_PHONE]) && $data[AUTHEN_PHONE] != '') {
            if ($this->userModel->is_exist([[[AUTHEN_PHONE, '=', $data[AUTHEN_PHONE]]]])) Reply::finish(false, ERROR_DUPLICATE, ['data' => AUTHEN_PHONE]);
        }


        unset($data[AUTHEN_ID]);
        unset($data[AUTHEN_PASS]);

        $query = $this->userModel->edit([
            DATA_KEY => [[[AUTHEN_ID, '=', $this->user->{AUTHEN_ID}]]],
            DATA_EDITOR => $data
        ]);

        if ($query['result']) {
            Auth::refreshToken(null, $data);
        }

        return $query;
    }

    public function read()
    {
        $query = $this->userModel->read([[[AUTHEN_ID, '=', $this->user->{AUTHEN_ID}]]]);
        if (!$query['result'] || !isset($query['data'][0])) Reply::finish(false, ERROR_UNDEFINE, ['data' => AUTHEN_ID]);
        $user = $query['data'][0];
        unset($user->{AUTHEN_PASS});
        Reply::finish(true, 'Success', $user);
    }



    public function update_pass(Request $request)
    {
        $userPass = $request->input('new_pass', null);
        $oldPass = $request->input('old_pass', null);
        if (is_null($userPass) || is_null($oldPass)) Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Password']);

        $user = $this->userModel->read([[[AUTHEN_ID, '=', $this->user->{AUTHEN_ID}]]]);
        if (!$user['result'] || count($user['data']) == 0) Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Account']);
        if (!Hash::check($oldPass, $user['data'][0]->{AUTHEN_PASS})) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Password is wrong']);

        return $this->userModel->edit([
            DATA_KEY => [[[AUTHEN_ID, '=', $this->user->{AUTHEN_ID}]]],
            DATA_EDITOR => [AUTHEN_PASS => Hash::make($userPass)]
        ]);
    }


    public function uploader_upload(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Metadata']);
        $size = $file['size'] + 1024;
        $disk = resolve('Models')->getModel('Uploader/Uploader_disks')->read(
            [[[DISK_TYPE, '=', 'local'], [DISK_FREE, '>', $size], [DISK_ACTIVE, '=', 1]]],
            function ($db) {
                $db->orderBy(DISK_WEIGHT, 'DESC');
            }
        );
        $option = ['condition' => ['validation' => 'required|image']];

        if (!$disk['result']) Reply::finish($disk);
        if (!isset($disk['data'][0])) Reply::finish(false, 'All disk is fulled');

        $diskName = $disk['data'][0]->{DISK_NAME};
        $uploader = $disk['data'][0]->{DISK_UPLOADER};

        return FileFunc::upload($uploader, $diskName, AUTHENTICATION_TABLE, $column, Auth::user()->{AUTHEN_ID}, $option);
    }


    public function uploader_read(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = AUTHENTICATION_TABLE;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $result = FileFunc::read(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_delete(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, 'No File Metadata');
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = AUTHENTICATION_TABLE;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};

        $result = FileFunc::delete(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_get(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        return FileFunc::get(AUTHENTICATION_TABLE, $column, Auth::user()->{AUTHEN_ID});
    }

    public function uploader_publish(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = AUTHENTICATION_TABLE;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $ulink = $fileInfo[FILE_UPLOADER] . '/api/uploader/public/read?file=' . $file;
        return redirect($ulink);
    }

}

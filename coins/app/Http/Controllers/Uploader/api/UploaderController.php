<?php

namespace App\Http\Controllers\Uploader\api;

use App\Helpers\DB\Models;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileToken;
use App\Model\Uploader\UploadManager;
use App\Helpers\Uploader\FileFunc;

class UploaderController extends Controller
{

    function __construct(UploadManager $uploadMng)
    {
        // Api for user upload, read and delete file
        parent::__construct();
        $this->uploadMng = $uploadMng;
    }

    private function getDisk($disk)
    {
        return $this->uploadMng->resolve($disk);
    }

    private function getPermission($request)
    {

        $token = FileToken::getToken($request);

        if ($token == false) {
            return Reply::finish(false, 'No Token');
        }

        if (FileToken::check($token)) {
            return FileToken::$payload;
        } else {
            return Reply::finish(false, 'Token is wrong');
        }
    }

    public function getFiles(Request $request)
    {

        $payload = $this->getPermission($request);
        if ($payload->{'action'} != 'getFiles') Reply::finish(false, 'No permission');

        $uploaderModel = $this->uploadMng->resolve($payload->{'disk'});

        $fileModel = Models::get('Uploader/Uploader_files');
        $diskModel = Models::get('Uploader/Uploader_disks');

        if (!$diskModel->is_exist([[[DISK_UPLOADER, '=', APP_UPLOAD]]])) Reply::finish(false, 'No App uploader name');

        if (!$uploaderModel) Reply::finish(false, 'Disk not found');
        $files = $uploaderModel->scandFiles();
        if (!$files['result']) return $files;
        $files = $files['data'];

        $result = $fileModel->drop([[[FILE_DISK, '=', $payload->{'disk'}], [FILE_UPLOADER, '=', APP_UPLOAD]]]);
        if (!$result['result']) return $result;

        while (count($files) > 0) {
            $subFiles = array_splice($files, 0, 500);

            $addData = [];
            foreach ($subFiles as $file) {
                $data = [];

                $re = '/^([^\/]+)\/([^\/]+)\/([\d]+)\/([^\/]+)$/';
                if (!preg_match($re, $file['path'], $matches)) continue;

                $data[FILE_DISK] = $payload->{'disk'};
                $data[FILE_UPLOADER] = APP_UPLOAD;
                $data[FILE_SIZE] = $file['size'];
                
                $data[FILE_MIME] = get($file['mime'], '');
                $data[FILE_MODIFIED] = get($file['modified'], '');

                $data[FILE_TABLE] = $matches[1];
                $data[FILE_COLUMN] = $matches[2];
                $data[FILE_UID] = $matches[3];
                $data[FILE_NAME] = $matches[4];

                $data[FILE_PATH] = $data[FILE_UPLOADER] . '/' . $data[FILE_DISK] . '/' . $file['path'];
                $addData[] = $data;
            }

            if (count($addData) > 0) {
                $result = $fileModel->add($addData);
                if (!$result['result']) return $result;
            }
        }

        $diskInfo = $uploaderModel->info();
        $result = $diskModel->edit([
            DATA_KEY => [[[DISK_UPLOADER, '=', APP_UPLOAD], [DISK_NAME, '=', $payload->{'disk'}]]],
            DATA_EDITOR => $diskInfo,
        ]);

        return $result;
    }

    public function upload(Request $request)
    {

        $permission = $this->getPermission($request);

        $file = $request->file('file', null);
        if ($file == null) Reply::finish(false, 'No file');

        $this->uploadModel = $this->getDisk($permission->{'disk'});

        if (!isset($this->uploadModel)) Reply::finish(false, 'No disk founded');

        $fileModel = Models::get('Uploader/Uploader_files');
        $diskModel = Models::get('Uploader/Uploader_disks');

        if (!$diskModel->is_exist([[[DISK_UPLOADER, '=', APP_UPLOAD]]])) Reply::finish(false, 'No App uploader name');

        if ($permission->{'permission'} == 'All' || in_array('Upload', $permission->{'permission'})) {

            $uploadResult = $this->uploadModel->upload($file, $permission->{'path'}, $permission->{'options'}->{'condition'});
            if (!$uploadResult['result']) return $uploadResult;

            $datas = (object)[
                FILE_PATH => $uploadResult['data'],
                FILE_UPLOADER => APP_UPLOAD,
                FILE_DISK => $permission->{'disk'},
                FILE_SIZE => filesize($file->path()),
                FILE_MIME => mime_content_type($file->path()),
                FILE_MODIFIED => filemtime($file->path())
            ];

            $re = '/^([^\/]+)\/([^\/]+)\/([^\/]+)\/([^\/]+)$/';
            if (!preg_match($re, $datas->{FILE_PATH}, $matches)) Reply::finish(false, 'File Upload Failed');

            $disk = $diskModel->read([[ [DISK_NAME, '=', $datas->{FILE_DISK}], [DISK_UPLOADER, '=', $datas->{FILE_UPLOADER}] ]]);
            if (!$disk['result'] || !isset($disk['data'][0])) Reply::finish(false, 'Disk Not Found');
            $disk = $disk['data'][0];

            $diskEditData = [];
            $diskEditData[DISK_USED] = $disk->{DISK_USED} + $datas->{FILE_SIZE};
            $diskEditData[DISK_FREE] = $disk->{DISK_TOTAL} - $diskEditData[DISK_USED];

            $result = $diskModel->edit([
                DATA_KEY => [[[DISK_ID, '=', $disk->{DISK_ID}]]],
                DATA_EDITOR => $diskEditData,
            ]);

            if (!$result['result']) return $result;

            $addData = [];

            $addData[FILE_DISK] = $datas->{FILE_DISK};
            $addData[FILE_UPLOADER] = $datas->{FILE_UPLOADER};
            $addData[FILE_SIZE] = $datas->{FILE_SIZE};
            $addData[FILE_MIME] = $datas->{FILE_MIME};
            $addData[FILE_MODIFIED] = $datas->{FILE_MODIFIED};
            $addData[FILE_TABLE] = $matches[1];
            $addData[FILE_COLUMN] = $matches[2];
            $addData[FILE_UID] = $matches[3];
            $addData[FILE_NAME] = $matches[4];
            $addData[FILE_PATH] = $datas->{FILE_UPLOADER} . '/' . $datas->{FILE_DISK} . '/' . $datas->{FILE_PATH};

            $result = $fileModel->add([$addData]);
            if (!$result['result']) return $result;

            Reply::finish(true, 'Success', $addData);
        }

        Reply::finish(false, 'No Permission');
    }

    public function read(Request $request)
    {

        $permission = $this->getPermission($request);

        $file = $permission->{'files'}[0];
        $path = $permission->{'path'};

        $this->uploadModel = $this->getDisk($permission->{'disk'});
        if (!isset($this->uploadModel)) Reply::finish(false, 'No disk founded');

        if ($permission->{'permission'} == 'All' || in_array('Read', $permission->{'permission'})) {

            $path = $path . '/' . $file;
            $mimetype = $this->uploadMng->getMime($path);
            return response($this->uploadModel->read($path), 200, [
                'Content-Type' => $mimetype,
            ]);
        } else {
            return Reply::finish(false, 'No Permission');
        }
    }

    public function delete(Request $request)
    {

        $permission = $this->getPermission($request);

        $file = $permission->{'files'}[0];
        $path = $permission->{'path'};

        $this->uploadModel = $this->getDisk($permission->{'disk'});
        if (!isset($this->uploadModel)) Reply::finish(false, 'No disk founded');

        if ($permission->{'permission'} == 'All' || in_array('Delete', $permission->{'permission'})) {
            $result = $this->uploadModel->delete($path . '/' . $file);
            if (!$result['result']) return $result;

            $datas = [
                FILE_PATH => APP_UPLOAD . '/' . $permission->{'disk'} . '/' . $path . '/' . $file,
            ];

            $fileModel = $this->models->getModel('Uploader/Uploader_files');
            $diskModel = $this->models->getModel('Uploader/Uploader_disks');

            $file = $fileModel->read([[[FILE_PATH, '=', $datas[FILE_PATH]]]]);

            if (!$file['result'] || !isset($file['data'][0])) Reply::finish(false, 'File Not Found');
            $file = $file['data'][0];

            $disk = $diskModel->read([[[DISK_NAME, '=', $file->{FILE_DISK}], [DISK_UPLOADER, '=', APP_UPLOAD]]]);
            if (!$disk['result'] || !isset($disk['data'][0])) Reply::finish(false, 'Disk Not Found');
            $disk = $disk['data'][0];

            $diskEditData = [];
            $diskEditData[DISK_USED] = $disk->{DISK_USED} - $file->{FILE_SIZE};
            $diskEditData[DISK_FREE] = $disk->{DISK_TOTAL} - $diskEditData[DISK_USED];

            $result = $diskModel->edit([
                DATA_KEY => [[[DISK_ID, '=', $disk->{DISK_ID}]]],
                DATA_EDITOR => $diskEditData,
            ]);
            if (!$result['result']) return $result;

            $dropResult = $fileModel->drop([[[FILE_ID, '=', $file->{FILE_ID}]]]);
            return $dropResult;
        }
        Reply::finish(false, 'No Permission');
    }

    public function public(Request $request)
    {

        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, 'No file');

        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'No file');

        $allows = [
            ['table' => 'articles', 'column' => 'art_body'],
            ['table' => 'watchlist', 'column' => 'wl_icon']
        ];

        $verify = false;
        foreach ($allows as $allow) {
            if ($fileInfo[FILE_TABLE] == $allow['table'] && $fileInfo[FILE_COLUMN] == $allow['column']) {
                $verify = true;
                break;
            }
        }

        if (!$verify) {
            Reply::finish(false, 'No file');
        }

        $this->uploadModel = $this->uploadMng->resolve($fileInfo[FILE_DISK]);
        if (!isset($this->uploadModel)) Reply::finish(false, 'No disk founded');
        $path = $fileInfo[FILE_TABLE] . '/' . $fileInfo[FILE_COLUMN] . '/' . $fileInfo[FILE_UID] . '/' . $fileInfo[FILE_NAME];
        $mimetype = $this->uploadMng->getMime($path);

        return response($this->uploadModel->read($path), 200, [
            'Content-Type' => $mimetype,
            'Cache-Control' => 'max-age=300',
        ]);
    }
}

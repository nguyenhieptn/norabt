<?php

namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class ArticlesController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Articles');
        $this->tableName = ARTICLES_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[ART_AID] = true;

        if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[ART_AID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas));
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][ART_AID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $data) {
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key => $data) {
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas]);
        Reply::finish($readResult);
    }

    public function mapping()
    {
        $mapData = [];
        $mapData[ART_LANGUAGE] = ['en' => 'English'];
        $mapData[ART_PUBLISHED] = ['0' => 'Unpublic', '1' => 'Public'];
        $mapData[ART_GID] = Edge::mapping(Models::get('Admin/Article_group'), ART_GID, ART_GROUP_ID, ART_GROUP_TITLE);
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[ART_TITLE, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{ART_AID} => $item->{ART_TITLE}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if (!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }


    //$$uploading$$
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

        return FileFunc::upload($uploader, $diskName, $this->tableName, $column, Auth::user()->{AUTHEN_ID}, $option);
    }


    public function uploader_read(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
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
        $fileInfo[FILE_TABLE] = $this->tableName;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};

        $result = FileFunc::delete(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_get(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        return FileFunc::get($this->tableName, $column, Auth::user()->{AUTHEN_ID});
    }

    public function uploader_publish(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $ulink = $fileInfo[FILE_UPLOADER] . '/api/uploader/public/read?file=' . $file;
        return redirect($ulink);
    }

    //$$/uploading$$

    //$$sorting$$
    public function sort(Request $request)
    {
        $datas = $request->input('data', array());

        $sourceID = $datas['src_id'];
        $destID = $datas['dest_id'];

        $srcData = $this->mainModel->read([[[ART_AID, '=', $sourceID]]]);
        if (isset($srcData['data'][0])) $srcData = $srcData['data'][0];
        $destData = $this->mainModel->read([[[ART_AID, '=', $destID]]]);
        if (isset($destData['data'][0])) $destData = $destData['data'][0];

        if ($srcData->{ART_WEIGHT} > $destData->{ART_WEIGHT}) {
            $maxW = $srcData->{ART_WEIGHT};
            $minW = $destData->{ART_WEIGHT};
            $vector = 1;
        } else {
            $minW = $srcData->{ART_WEIGHT};
            $maxW = $destData->{ART_WEIGHT};
            $vector = 0;
        }

        $sortProjects = $this->mainModel->read([[[ART_WEIGHT, '>=', $minW], [ART_WEIGHT, '<=', $maxW]]], function ($db) {
            $db->orderBy(ART_WEIGHT, 'desc');
        });
        if (!$sortProjects['result']) return Reply::finish($sortProjects);
        $sortProjects = $sortProjects['data'];

        if ($vector == 1) {

            $this->mainModel->edit([
                DATA_KEY => [[[ART_AID, '=', $sourceID]]],
                DATA_EDITOR => [ART_WEIGHT => 0]
            ]);

            foreach ($sortProjects as $key => $sortProject) {
                if (isset($sortProjects[$key - 1])) {
                    $this->mainModel->edit([
                        DATA_KEY => [[[ART_AID, '=', $sortProject->{ART_AID}]]],
                        DATA_EDITOR => [ART_WEIGHT => $sortProjects[$key - 1]->{ART_WEIGHT}]
                    ]);
                }
            }

            $this->mainModel->edit([
                DATA_KEY => [[[ART_AID, '=', $sourceID]]],
                DATA_EDITOR => [
                    ART_WEIGHT => $destData->{ART_WEIGHT},
                    //SOLUTION_PARENT => $destData->{SOLUTION_PARENT},
                ]
            ]);
        } else {

            $this->mainModel->edit([
                DATA_KEY => [[[ART_AID, '=', $sourceID]]],
                DATA_EDITOR => [ART_WEIGHT => 0]
            ]);

            for ($key = count($sortProjects) - 1; $key >= 0; $key--) {

                if (isset($sortProjects[$key + 1])) {
                    $this->mainModel->edit([
                        DATA_KEY => [[[ART_AID, '=', $sortProjects[$key]->{ART_AID}]]],
                        DATA_EDITOR => [ART_WEIGHT => $sortProjects[$key + 1]->{ART_WEIGHT}]
                    ]);
                }
            }

            $this->mainModel->edit([
                DATA_KEY => [[[ART_AID, '=', $sourceID]]],
                DATA_EDITOR => [
                    ART_WEIGHT => $destData->{ART_WEIGHT},
                    //SOLUTION_PARENT => $destData->{SOLUTION_PARENT},
                ]
            ]);
        }

        Reply::finish(true, 'Success', '');
    }

    //$$/sorting$$




}

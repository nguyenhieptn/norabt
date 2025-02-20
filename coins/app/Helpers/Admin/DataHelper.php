<?php

namespace App\Helpers\Admin;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use Illuminate\Support\Facades\Auth;

class DataHelper
{
    
    public static function getLabGroup()
    {
        $labAccountModel = Models::get('Admin/Lab_account')->db();
        if(Role::checkRoot()){
            $data = $labAccountModel->select(LAB_ACCOUNT_GROUP)->distinct()->orderBy(LAB_ACCOUNT_GROUP, 'ASC')->get();
        }else{
            $data = $labAccountModel->select(LAB_ACCOUNT_GROUP)->distinct()->where(LAB_ACCOUNT_USER, Auth::user()->{AUTHEN_ID})->orderBy(LAB_ACCOUNT_GROUP, 'ASC')->get();
        }

        $groups = (object)[];
        foreach($data as  $value){
            
            $groups->{$value->{LAB_ACCOUNT_GROUP}} = $value->{LAB_ACCOUNT_GROUP};
        }


        $labStraModel = Models::get('Admin/Lab_strategies')->db();
        if(Role::checkRoot()){
            $data = $labStraModel->select(LAB_STRATEGY_GROUP)->distinct()->orderBy(LAB_STRATEGY_GROUP, 'ASC')->get();
        }else{
            $data = $labStraModel->select(LAB_STRATEGY_GROUP)->distinct()->where(LAB_STRATEGY_USER, Auth::user()->{AUTHEN_ID})->orderBy(LAB_STRATEGY_GROUP, 'ASC')->get();
        }

        foreach($data as  $value){
            $groups->{$value->{LAB_STRATEGY_GROUP}} = $value->{LAB_STRATEGY_GROUP};
        }
        
        return $groups;
        
    }

    public static function getDocGroup(){
        
        $labAccountModel = Models::get('Admin/Lab_doc')->db();
       
        $data = $labAccountModel->select(LAB_DOC_GROUP)->distinct()->orderBy(LAB_DOC_GROUP, 'ASC')->get();
        

        $groups = (object)[];
        foreach($data as  $value){
            $groups->{$value->{LAB_DOC_GROUP}} = $value->{LAB_DOC_GROUP};
        }
        return $groups;
    }
}

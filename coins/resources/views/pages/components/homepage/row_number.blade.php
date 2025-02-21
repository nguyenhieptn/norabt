<?php

use App\Helpers\Request\Query;

$information = Query::make(STORE_SERVER . '/store/labs/getInformation', 'get', [], ['dataType' => 'json']);
if (!$information) $information = [];
if (!$information['result']) $information = [];
$information = $information['data'];


?>


<style>

    
</style>
<div class="row number_box">
    <div class="col-md-4">
        <div class="box_flex">
            <i class="fa fa-users" aria-hidden="true"></i>
            <div class="number_item">
                <h4>Total Users</h4>
                <h3>{{ get($information['countUsers'], 0) }}</h3>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="box_flex">
            <i class="fa fa-graduation-cap" aria-hidden="true"></i>
            <div class="number_item">
                <h4>Total Labs</h4>
                <h3>{{ get($information['countLabs'], 0) }}</h3>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="box_flex">
            <i class="fa fa-cloud-download" aria-hidden="true"></i>

            <div class="number_item">
                <h4>Labs Downloaded</h4>
                <h3>{{ get($information['countDownload'], 0) }}</h3>
            </div>
        </div>
    </div>

   

</div>

<style>
    .row.number_box {
         background: #34ccff;
         background: -webkit-linear-gradient(90deg, #01b0ef, #6a98d1, #002e5b);
         background: -o-linear-gradient(90deg, #01b0ef, #406592, #002e5b);
         background: -moz-linear-gradient(90deg, #01b0ef, #406592, #002e5b);
         background: linear-gradient(90deg, #01b0ef, #6b96c9, #002e5b);
         color: white;
         padding: 30px 0px;
    }

    .number_box .box_flex{
        padding-left: 20%;
    }

    .number_box .number_item {
        text-align: center;
        padding: 5px;
        
    }

    .number_box i {
        font-size: 48px;
        margin-right: 15px;
    }

</style>


<script>
    $(document).ready(function() {

       
    });
</script>
<?php

use App\Helpers\Request\Query;
use App\Helpers\Uploader\FileFunc;

$newLab = Query::make(STORE_SERVER . '/api/user/labs/getFreeLabs?limit=10', 'get', [], ['dataType' => 'json']);
if (!$newLab) $newLab = [];
if (!$newLab['result']) $newLab = [];
$newLab = $newLab['data'];


?>

<!-- Important Owl stylesheet -->
<link rel="stylesheet" href="/extensions/owl_carousel/assets/owl.carousel.min.css">

<!-- Default Theme -->
<link rel="stylesheet" href="/extensions/owl_carousel/assets/owl.theme.default.min.css">

<!-- Include js plugin -->
<script src="/extensions/owl_carousel/owl.carousel.min.js"></script>

<style>

    .lab_item_image {
        border: solid thin #0000001a;
        padding: 0px;
        height: 150px;
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 5px;
        overflow: hidden;
    }

    .lab_item_image {
        position: relative;
    }

    .lab_item_image img {
        width: 100%;
    }

    .lab_item_image .cover {
        justify-content: center;
        position: absolute;
        top: 0;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(0, 0, 0, 0.3);
        display: none;
    }

    .lab_item_image .cover div {
        border: solid thin rgba(255, 255, 255, 0.5);
        border-radius: 5px;
        padding: 7px;
        color: white;
        background: rgba(255, 255, 255, 0.2);
    }

    .lab_item_image:hover .cover {
        display: flex;
    }

    .lab_item {
        padding: 7px;
        color: #666;
        display: flex;
        /* width:230px; */
        width: 100%;
        max-width: 300px;

        
    }

    .lab_item .box_shadow {
        background: white;
    }

    .lab_item .lab_item_name {
        margin-bottom: 0px;
    }

    .lab_article .lab_article_content {
        transition: all ease-in-out 0.4s;
        max-height: 400px;
        overflow: hidden;
        z-index: 0;
        position: relative;
    }

    .lab_article .lab_article_button {
        margin-top: -30px;
        padding-top: 30px;
        justify-content: center;
        background-image: linear-gradient(rgba(255, 255, 255, 0), white, white, white);
        z-index: 1;
        position: relative;
    }

    .lab_article .lab_article_button .button {
        color: #0d274d;
        font-weight: bold;
        padding: 7px;
        border-radius: 5px;
    }

    .lab_article .lab_article_button .button:hover {
        background: rgba(0, 0, 0, 0.1);
    }

    .lab_article.expand .lab_article_button {
        margin-top: 0px;
        padding-top: 7px;
    }

    .lab_article.expand .lab_article_button .button {
        background: rgba(0, 0, 0, 0.1);
    }

    #owl-demo .owl-item {
        display: flex;
        justify-content: center;
    }

    #owl-demo .owl-stage {
        display: flex !important;
    }
</style>
<div>

    <div class="owl-carousel owl-theme" id="owl-demo">
        <?php foreach ($newLab as $lab) : ?>
            <div class="lab_item">
                <div class="box_shadow d-flex" style="padding: 7px; width: 100%; flex-direction: column;">
                    <a href="{{STORE_SERVER.'/store/labs/detail?id='.$lab['lab_id']}}">
                        <div class="lab_item_image">
                            <img src="{{FileFunc::file_public($lab['lab_img'])}}">
                            <div class="cover box_flex">
                                <div>Detail</div>
                            </div>
                        </div>
                    </a>
                    <a href="{{STORE_SERVER.'/store/labs/detail?id='.$lab['lab_id']}}">
                        <h5 class="lab_item_name box_line" title="{{$lab['lab_name']}}">{{$lab['lab_name']}}</h5>
                    </a>
                    <div style="margin-bottom: 5px;">
                        <a href="#">
                            <i class="fa fa-user-o">
                            </i>&nbsp;Nexus</a>
                    </div>
                    <p class="lab_item_des">{{str_limit($lab['lab_des'])}}</p>
                </div>
            </div>
        <?php endforeach; ?>
    </div>


</div>

<script>
    $(document).ready(function() {

        $(".owl-carousel").owlCarousel({

            autoplay: true,
            autoplayTimeout: 3000,
            autoplaySpeed: 1000,
            slideTransition: 'ease',
            items:1,
            loop:true,
            autoplayHoverPause:true,
            responsive : {
                480 : { items : 2  }, 
                768 : { items : 4  }, 
                1024 : { items : 6 },  
                1500 : { items : 7 } 
            },

        });

    });
</script>
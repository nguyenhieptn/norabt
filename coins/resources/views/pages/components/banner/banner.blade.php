<?php

use App\Helpers\Uploader\FileFunc;
use Illuminate\Support\Facades\DB;
    
    $bannerName = get(${BANNER_NAME}, '');
    $id = 'banner_slide';
    $bannerData = [];
    if($bannerName != ''){
        $bannerData = DB::table(BANNER_TABLE)
        ->where([
            [BANNER_NAME, '=', $bannerName],
            [BANNER_PUBLIC, '=', '1'], 
        ])
        ->orderBy(BANNER_WEIGHT, 'DESC')
        ->get();
    }
    
    $numberBanner = count($bannerData);
?>

<link rel = "stylesheet" href = "/views/pages/components/banner/banner.css" media = "all" type = "text/css" />   
 
<?php if($numberBanner == 1): ?>

        <div class="wow">
        	<div class="row" style="display: flex; padding: 0px;">
                @component('pages.components.banner.banner_item', ['content'=>$bannerData[0]->{BANNER_DES}, 'image'=>FileFunc::file_public($bannerData[0]->{BANNER_IMG})])@endcomponent
            </div>
        </div>
        
<?php elseif($numberBanner > 1):?>

        <!-- <div class="top-gradient" style=""></div> -->
        <div id="{{$id}}" class="carousel slide" data-ride="carousel">
          <ol class="carousel-indicators">
            @foreach($bannerData as $key => $banner)
                @if($key == 0)
                    <li data-target="#{{$id}}" data-slide-to="{{$key}}" class="active"></li>
                @else
                    <li data-target="#{{$id}}" data-slide-to="{{$key}}"></li>
                @endif
            @endforeach
            <!-- <li data-target="#banner_slide" data-slide-to="2"></li> -->
          </ol>
          <div class="carousel-inner">
          
           <?php foreach($bannerData as $key => $banner):?>
                <div class="carousel-item {{$key==0?'active':''}}">
                
                 @component('pages.components.banner.banner_item', ['content'=>$banner->{BANNER_DES}, 'image'=>FileFunc::file_public($banner->{BANNER_IMG})])@endcomponent       
                
                </div>
                
           <?php endforeach;?>
            
          </div>
          <a class="carousel-control carousel-control-prev" href="#{{$id}}" role="button" data-slide="prev">
            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
            <span class="sr-only">Previous</span>
          </a>
          <a class="carousel-control carousel-control-next" href="#{{$id}}" role="button" data-slide="next">
            <span class="carousel-control-next-icon" aria-hidden="true"></span>
            <span class="sr-only">Next</span>
          </a>
        </div>
        
        <!--  <div class="main-gradient" style=""></div> -->
        
<?php else:?>

        <div></div>
        
<?php endif;?>

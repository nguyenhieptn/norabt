<?php

use App\Helpers\Uploader\FileFunc;
use App\Helpers\View\Loader;
use Illuminate\Support\Facades\DB;
    
    
    
    $limit = get($limit, '5');
    
    $condition = [[ART_PUBLISHED, '=', '1'], [ART_LANGUAGE, '=', session('lang')]];
   
    $articles = DB::table(ARTICLES_TABLE)
    ->select(ART_AID, ART_TIME, ART_FEATURE_IMG, ART_SLUG, ART_SAPO, ART_TITLE)
    ->where($condition)
    ->orderBy(ART_WEIGHT, 'DESC')
    ->orderBy(ART_TIME, 'DESC')
    ->limit($limit)
    ->get();
    
    echo Loader::asset('widget_css', '/views/pages/components/widget/widget.css', 'css');
    

?>
<div class="container">
          
            <?php foreach($articles as $key => $article): ?>
            
                <div class="article_div click_object">
                
                    <a href="/pages/article?slug={{ $article->{ART_SLUG} }}">
                        <h5 class="card-title card-post-title" style="margin-bottom: 5px; margin-top: 20px" title="{{ $article->{ART_TITLE} }}">{{ str_limit($article->{ART_TITLE}, 30) }}</h5>
                        <div style="display: flex;">
                            <div style="margin: auto">
                                <img src="{{FileFunc::file_public($article->{ART_FEATURE_IMG})}}" style="width: 100px; border-radius: 5px; box-shadow: 1px 1px 10px gainsboro;">
                            </div>
                            <div class="card-body" style="padding:5px; margin: auto">
                                  <span class="post-time">{{ date('F j, Y' , $article->{ART_TIME}) }}</span>
                                  <p class="card-text card-post-body"><?php echo str_limit(strip_tags (htmlspecialchars_decode($article->{ART_SAPO}, ENT_QUOTES)),50)?></p>
                              
                            </div>
                        
                        </div>
                    
                     </a>
                     
                </div>
             
            <?php endforeach; ?>

</div>




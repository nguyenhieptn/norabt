
<?php 
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\App;
$slug = get($input['slug'], '');
$article = DB::table(ARTICLES_TABLE)
->where([
    [ART_SLUG, '=', $slug],
    [ART_LANGUAGE, '=', App::getLocale()],
])
->get();

$article = isset($article[0])? $article[0] : (object)[ART_TITLE=>'Article not found'];

?>

@extends('pages.default_page', ['page'=>$page])
@section('main')
<link rel="stylesheet" type="text/css" href="/views/pages/components/news/article.css">
<div class='container'>
    <div class = "row">
        <div class="col-lg-8">
        
            <h3 class="article-title"><?php echo get($article->{ART_TITLE},''); ?></h3>
            
              <div class="entry-meta" style="border: none; margin: 0px;">
            	  <span><i class="fa fa-calendar"></i><span> {{ date('F j, Y', get($article->{ART_TIME}, 0) ) }}</span></span>
        	  </div>
            <!-- <p class="article-sapo"><?php echo get($article->{ART_SAPO}, ''); ?></p> -->
            
            <div class="article-body ck-content">
            
              <?php echo get($article->{ART_BODY},''); ?>
            </div>
            <hr>
        </div>
        <div class="col-lg-4">
        <h3>@lang('widget.Recent news')</h3>
        @component('pages.components.widget.widget_relate_news')@endcomponent
        </div>
    </div>
</div>


@endsection
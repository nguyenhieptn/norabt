
@extends('pages.default_page')
@section('main')
<?php 
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\App;
$slug = get($input['slug'], '');
$article = DB::table(ARTICLES_TABLE);
if($slug != '') $article = $article->where(ART_SLUG, '=', $slug);
$article = $article->where(ART_LANGUAGE, '=', App::getLocale())
->where(ART_PUBLISHED, '=', 1)
->orderBy(ART_WEIGHT, 'ASC')
->get();

$article = isset($article[0])? $article[0] : (object)[ART_TITLE=>'Article not found'];
$slug = get($article->{ART_SLUG}, '');
?>

<div class="row">
  <div class="col-md-3">
  @component('pages.components.documents.document_menu', ['active'=>$slug])@endcomponent
  </div>  
  <div class="col-md-9">
        <h3 class="article-title"><?php echo get($article->{ART_TITLE},''); ?></h3> 
          <!-- <p class="article-sapo"><?php echo get($article->{ART_SAPO}, ''); ?></p> -->
          <div class="article-body ck-content">
            <?php echo get($article->{ART_BODY},''); ?>
          </div>
  </div>  
</div>
@endsection
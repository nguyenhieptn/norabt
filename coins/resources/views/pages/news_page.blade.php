<?php

use App\Helpers\DB\Models;
use Illuminate\Support\Facades\App;
use App\Helpers\Request\Reply;
use App\Helpers\DB\FullTextSearch;
use App\Helpers\Uploader\FileFunc;

$lang = App::getLocale();
$number = 11;
$pageNumber = get($input['page'], 1);
if (!isset($pageNumber) || $pageNumber < 1) $pageNumber = 1;
$inteval = ($pageNumber - 1) * $number;

$search = get($input['search'], '');
$group = get($input['group'], 'all');

$condition = [[
  [ART_PUBLISHED, '=', '1'],
  [ART_LANGUAGE, '=', $lang],
]];

$listArticle = null;
if (isset($group) && $group != 'all' && $group != '') {

  $groupInfo = Models::get('Admin/Article_group')->read([[[ART_GROUP_KEY, '=', $group], [ART_GROUP_LANG, '=', $lang]]]);
  if (!$groupInfo['result']) Reply::finish($listArticle);
  if (!isset($groupInfo['data'][0])) {
    echo redirect('/home');
    die;
  }
  $groupInfo = $groupInfo['data'][0];

  $listArticle = Models::get('Admin/Map_art_group')->read([[[MAG_GID, '=', $groupInfo->{ART_GROUP_ID}]]]);
  if (!$listArticle['result']) Reply::finish($listArticle);
  $listArticle = $listArticle['data']->map(function ($item) {
    return $item->{MAG_AID};
  });
}

$articles = Models::get('Admin/Articles')->read($condition, function ($db) use ($listArticle, $inteval, $number, $search) {
  if (isset($listArticle)) {
    $db->whereIn(ART_AID, $listArticle);
  }
  if (isset($search) && $search != '') {
    FullTextSearch::fullTextSearch($db, [ART_TITLE, ART_SAPO], $search);
  }
  $db->orderBy(ART_WEIGHT, 'desc')
    ->orderBy(ART_TIME, 'desc')
    ->offset($inteval)
    ->limit($number);
});

if (!$articles['result']) Reply::finish($articles);

$articles = $articles['data'];

?>

@extends('pages.default_page' , ['page' => $page])
@section('main')
<br>
<div class="container">
  @component('pages.components.news.menu_category', ['active'=>$group])@endcomponent
</div>
<link rel="stylesheet" type="text/css" href="/views/pages/components/news/news.css">

<div class="container">
  <div class="row">
    <div class="col-md-8">

      <?php if (count($articles) > 0) : ?>

        <div id="focus_news_div">
          <div class="main_art_picture" style="background-image: url('<?php echo FileFunc::file_public($articles[0]->{ART_FEATURE_IMG}) ?>')">
            <!-- ========================================================== -->
            <div class="main-art-box button" style="padding:0px; margin:0px; margin-bottom:60px">
              <div class="main-art-text-box">
                <h4 class="entry-title"><a href="/pages/articles?slug={{ $articles[0]->{ART_SLUG} }}">{{ $articles[0]->{ART_TITLE} }}</a></h4>
                <p class="entry-content" style="color: white;"><?php echo str_limit(strip_tags($articles[0]->{ART_SAPO}), 200) ?></p>
                <div class="entry-meta" style="color:white;color: white; border: none; margin: 0px;">
                  <span><i class="fa fa-calendar"></i><span>{{ date('F j, Y', $articles[0]->{ART_TIME}) }}</span></span>
                </div>
              </div>
            </div>
            <!-- ========================================================== -->
          </div>
        </div>

        <div class="row">

          <?php
          $number = count($articles);
          if ($number >= 12) $number = 11;
          for ($i = 1; $i < $number; $i++) :
            $article = $articles[$i];
          ?>

            <div class="col-md-6">
              @component('pages.components.news.item_article',['article' => $article ])@endcomponent
            </div>

          <?php endfor; ?>
        </div>

        <nav aria-label="Page navigation example">
          <ul class="pagination">
            <?php if ($pageNumber > 1) : ?>
              <li class="page-item">
                <a class="page-link" href="/pages/news?group={{$group}}&page={{$page-1}}&search={{$search}}" aria-label="Previous">
                  <span aria-hidden="true">&laquo;</span>
                  <span class="sr-only">Previous</span>
                </a>
              </li>
            <?php endif; ?>

            <?php if (count($articles) >= 12) : ?>
              <li class="page-item">
                <a class="page-link" href="/pages/news?group={{$group}}&page={{$page-1}}&search={{$search}}" aria-label="Next">
                  <span aria-hidden="true">&raquo;</span>
                  <span class="sr-only">Next</span>
                </a>
              </li>
            <?php endif; ?>
          </ul>
        </nav>

      <?php else : ?>
        <h3>Article not found!</h3>
      <?php endif; ?>

    </div>

    <div class="col-md-4">
      @component('pages.components.widget.widget_search', ['link' => "/pages/news"])@endcomponent
      <br>
      <h3>@lang('widget.Recent news')</h3>
      @component('pages.components.widget.widget_relate_news', ['limit'=>5])@endcomponent
    </div>

  </div>
</div>
@endsection
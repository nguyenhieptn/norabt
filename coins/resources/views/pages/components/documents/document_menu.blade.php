<?php 
    use Illuminate\Support\Facades\DB;
    $groups = DB::table(ARTICLE_GROUP_TABLE)
    ->where(ART_GROUP_LANG, '=', session('lang'))
    ->where(ART_GROUP_PUBLIC, '=', 1)
    ->orderBy(ART_GROUP_WEIGHT, 'ASC')
    ->get();

    $articles = DB::table(ARTICLES_TABLE)
    ->select([ART_TITLE, ART_TIME, ART_GID, ART_SLUG])
    ->where(ART_LANGUAGE, '=', session('lang'))
    ->where(ART_PUBLISHED, '=', 1) 
    ->orderBy(ART_WEIGHT, 'ASC')
    ->orderBy(ART_TIME, 'ASC')
    ->get();

    $articlesByGroup=[];
    foreach($articles as $key=>$article){
        if(!isset($articlesByGroup[$article->{ART_GID}])) $articlesByGroup[$article->{ART_GID}] = [];
        $articlesByGroup[$article->{ART_GID}][] = $article;
    }

    $active = get($active, '');
    
?>

<?php
use App\Helpers\View\Loader;
echo Loader::asset('document_css', '/views/pages/components/documents/document.css', 'css')
?>

<div class="dropdown" >
  <button class="button btn btn-info dropdown-toggle" type="button" id="document_menu_button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
    Contents
  </button>
  <div class="dropdown-menu document-menu" aria-labelledby="document_menu" style="padding:0px" id="document_menu_content">
      <form>
    <?php foreach($groups as $key=>$group):?>
        <div class="button box_line document_group" data-toggle="collapse" data-target="#collapsegroup{{$key}}" aria-expanded="true">
            <i class="fa"></i>&nbsp;{{ $group->{ART_GROUP_TITLE} }}</div>
        <div class="collapse show" id="collapsegroup{{$key}}">
            <div class="document_group_arts">
                <?php 
                    if(!isset($articlesByGroup[$group->{ART_GROUP_ID}])) $articlesByGroup[$group->{ART_GROUP_ID}] = [];
                    foreach($articlesByGroup[$group->{ART_GROUP_ID}] as $article):
                        $activeClass = ($article->{ART_SLUG} == $active)? 'active': '';
                ?>
                    <div title="{{ $article->{ART_TITLE} }}" class="box_flex button document_art_item {{$activeClass}}" style="padding:5px"><i class="fa fa-circle" style="font-size: 8px; margin-right: 10px;"></i>
                    <a href="/user/articles/view?slug={{ $article->{ART_SLUG} }}" class="box_line">{{ $article->{ART_TITLE} }}</a>

                    </div>

                <?php endforeach?>
            </div>
        </div>
    <?php endforeach?>
      </form>
  </div>

  <style>
      [aria-expanded=true] i::before{
        content: "\f107";
      }
      [aria-expanded=false] i::before{
        content: "\f105";
      }
      .document_group.button{
        padding: 10px;
        width: 100%;
        font-weight: 700;
        color: #17a2b8;
        text-align: left;
        background-color: #f4f4f4;
        cursor: pointer;
        border: solid thin rgba(0, 0, 0, 0.1);
        margin:0px;
      }
      .document_group_arts{
        padding:10px;
      }
      #document_menu_content{
        width: 300px;
      }
      #document_menu_button{
        margin: 0px;
      }
      .document_art_item.active {
          background: rgba(13, 39, 77, 0.2);
      }
      
  </style>

</div>

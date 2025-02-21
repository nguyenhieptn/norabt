<?php

use App\Helpers\View\Loader;

$image = get($article->{ART_FEATURE_IMG}, '');
$title = get($article->{ART_TITLE}, '');
$sapo = get($article->{ART_SAPO}, '');
$time = get($article->{ART_TIME},0);
$key = get($article->{ART_SLUG}, '#');
?>

<?php echo Loader::asset('item_article_css', '/views/pages/components/news/item_article.css', 'css')?>

<div class="thumbnails thumbnail-style thumbnail-kenburn">

	<div class="thumbnail-img" style="background-image:url('<?php echo APP_UPLOAD.'/uploader/public/read?file='.$image?>'); height:180px; background-size: cover; background-position: center;">
		<a class="btn-more hover-effect" href="/pages/article?slug=<?php echo $key?>">@lang('widget.read_more')</a>
	</div>
	
	<div class="caption">
		<div class="text_header_1 box_line">
			<b><a class="hover-effect" href="/pages/article?slug=<?php echo $key?>" title="<?php echo $title?>">{{$title}}</a></b>
		</div>
		<span><i class="fa fa-calendar"></i><span> {{ date('F j, Y', $time) }}</span></span>
		<p><?php echo str_limit(strip_tags($sapo),100)?></p>
	</div>
	
</div>
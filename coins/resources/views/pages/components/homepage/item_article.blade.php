<?php
$image = get($article->{ART_FEATURE_IMG}, '');
$title = get($article->{ART_TITLE}, '');
$sapo = get($article->{ART_SAPO}, '');
$time = get($article->{ART_TIME},0);
$key = get($article->{ART_SLUG}, '#');
?>

<?php echo resolve('Loader')->asset('/assets/pages/components/item_article/item_article.css', 'css')?>

<div class="thumbnails thumbnail-style thumbnail-kenburn">

	<div class="thumbnail-img" style="background-image:url('<?php echo APP_UPLOAD.'/uploader/public/read?file='.$image?>'); height:180px; background-size: cover; background-position: center;">
		<a class="btn-more hover-effect" href="/pages/article?slug=<?php echo $key?>">@lang('widget.read_more')</a>
	</div>
	
	<div class="caption">
		<div class="text_header_1">
			<b><a class="hover-effect" href="/pages/article?slug=<?php echo $key?>" title="<?php echo $title?>"><?php echo str_limit($title,20)?></a></b>
		</div>
		<span><i class="fa fa-calendar"></i><span> {{ date('F j, Y', $time) }}</span></span>
		<p><?php echo str_limit(strip_tags (htmlspecialchars_decode($sapo, ENT_QUOTES)),100)?></p>
	</div>
	
</div>
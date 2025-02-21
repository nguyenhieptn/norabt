<?php
$class = get($class, '');
$css = get($css, '');
$img = get($item['image'], '');
$title = get($item['title'], '');
$text = get($item['text'], '');
$link = get($link['link'], '#');

?>

@component('layouts.loader', ['id' => 'item_imgsquare_css'])
<style>
.item_imgsquare_img {
	display: flex;
}

.item_imgsquare_img img{
	width: 100px;
	height: auto;
	box-shadow: 1px 1px 10px gainsboro;
	padding: 5px;
	border-radius: 3px;
}


.item_imgsquare_img img:HOVER {
	webkit-transform: scale(1.1);
	-moz-transform: scale(1.1);
	-o-transform: scale(1.1);
	-ms-transform: scale(1.1);
	transform: scale(1.1);
	transition: all .5s ease-in-out;
}

.item_imgsquare_text {
	padding: 10px;
}

<?php echo $css?>

</style>
@endcomponent

<div class="<?php echo $class?>">

	<div class="d-flex" style="padding:5px">
		<div class="item_imgsquare_img">
			<a href="<?php echo $link?>" style="margin: auto;"> 
			<img src="<?php echo BUILDER_DIR.$img?>" alt="">
			</a>
		</div>
		<div class="item_imgsquare_text">
			<div class="text_header_1"><?php echo $title?></div>
			<p><?php echo $text?></p>
		</div>
	</div>

</div>
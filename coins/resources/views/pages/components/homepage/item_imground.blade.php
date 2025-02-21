<?php
$class = get($class, '');
$css = get($css, '');
$img = get($item['image'], '');
$title = get($item['title'], '');
$text = get($item['text'], '');
$link = get($link['link'], '#');

?>

@component('layouts.loader', ['id' => 'item_imground_css'])
<style>
.item_imground_img img {
	width: 80px;
	height: 80px;
	margin: auto;
	border-radius:50%;
	box-shadow: 1px 1px 10px gainsboro;
}

.item_imground_img img:HOVER {
	webkit-transform: scale(1.2);
	-moz-transform: scale(1.2);
	-o-transform: scale(1.2);
	-ms-transform: scale(1.2);
	transform: scale(1.2);
	transition: all .5s ease-in-out;
}

.item_imground_text {
	padding: 0px 10px;
}

<?php echo $css?>

</style>
@endcomponent

<div class="<?php echo $class?>">

	<div class="d-flex" style="padding:5px">
		<div class="item_imground_img">
			<a href="<?php echo $link?>" style="margin: auto;"> 
			<img src="<?php echo BUILDER_DIR.$img?>" alt="">
			</a>
		</div>
		<div class="item_imground_text">
			<h5><?php echo $title?></h5>
			<p><?php echo $text?></p>
		</div>
	</div>

</div>
<?php 
    $class = get($class, '');
    $css = get($css, '');
    $img = get($item['image'], '');
    $title = get($item['title'], '');
    $text = get($item['text'], '');
    $link = get($link['link'], '#');
    

?>

@component('layouts.loader', ['id' => 'item_imgbox_css'])
<style>
.item_imgbox_img {
    overflow: hidden;
    height: 200px;
    display: flex;
    border-radius: 5px;
    box-shadow: 1px 1px 10px gainsboro;
	padding: 5px;
}

.item_imgbox_img img{
    width: 100%
}

.item_imgbox_img img:HOVER {
	webkit-transform: scale(1.1);
    -moz-transform: scale(1.1);
    -o-transform: scale(1.1);
    -ms-transform: scale(1.1);
    transform: scale(1.1);
	transition: all .5s ease-in-out;
}
.item_imgbox_text {
	padding: 10px 5px;
}

<?php echo $css?>

</style>
@endcomponent

<div class="<?php echo $class?>">

    <div class="item_imgbox_img">
        <a href="<?php echo $link?>" style="margin: auto;">
            <img style="width: 100%" src="<?php echo BUILDER_DIR.$img?>" alt="">
        </a>
    </div>
	<div class="item_imgbox_text">
    	<div class="text_header_1"><?php echo $title?></div>
    	<p><?php echo $text?></p>
	</div>
</div>
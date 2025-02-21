<?php 
    $class = get($class, '');
    $css = get($css, '');
    $img = get($item['image'], '');
    $title = get($item['title'], '');
    $text = get($item['text'], '');
    $link = get($link['link'], '#');
    $side = get($side, 'L');
    

?>

@component('layouts.loader', ['id' => 'row_imgbox_css'])
<style>
.row_imgbox_img {
    overflow: hidden;
    min-height: 200px;
    box-shadow: 1px 1px 10px gainsboro;
	padding: 5px;
	background-size: cover; 
	border-radius: 5px; 
	background-clip: content-box;
}
.row_imgbox_img:HOVER {
	webkit-transform: scale(1.01);
    -moz-transform: scale(1.01);
    -o-transform: scale(1.01);
    -ms-transform: scale(1.01);
    transform: scale(1.01);
	transition: all .5s ease-in-out;
}
.row_imgbox_text {
	padding: 15px;
}

.row_imgbox_text .button{
    padding: 10px;
    border-radius: 5px;
    background: #5ba818;
    font-weight: bold;
    color: white !important;
    margin: 15px;
}
</style>
@endcomponent

<?php if($side == 'L'):?>
<div class="row <?php echo $class?>" style="padding: 15px;">

    <div class="col-md-6 row_imgbox_img" style="background-image: url('<?php echo BUILDER_DIR.$img?>')">
        
    </div>
	<div class="col-md-6 row_imgbox_text">
	
        <div class="text_header_1"><?php echo $title?></div>
        
    	<p><?php echo $text?></p>
    	
    	<?php if(isset($item['link'])):?>
            <a href="<?php echo $item['link']?>"
				class="button button_career">@lang('widget.detail')</a>
        <?php endif;?>
        
	</div>
</div>
<?php else:?>
<div class="row <?php echo $class?>" style="padding: 15px;">

    
	<div class="col-md-6 row_imgbox_text">
	
        <h5><?php echo $title?></h5>
        
    	<p><?php echo $text?></p>
    	
    	<?php if(isset($item['link'])):?>
            <a href="<?php echo $item['link']?>"
				class="button">@lang('widget.detail')</a>
        <?php endif;?>
        
	</div>
	
	<div class="col-md-6 row_imgbox_img" style="background-image: url('<?php echo BUILDER_DIR.$img?>')">
        
    </div>
    
</div>
<?php endif;?>

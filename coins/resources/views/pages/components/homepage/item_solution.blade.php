<?php 
$icon = get($solution->{SOLUTION_ICON}, '');
$title = get($solution->{SOLUTION_TITLE}, '');
$description = get($solution->{SOLUTION_DES}, '');
$key = get($solution->{SOLUTION_KEY}, '#');
$link = get($solution->{SOLUTION_LINK}, '#');
?>



<div class="service" style="display: flex; padding: 10px; margin-top: 10px;">
<i style="float:left"><img style="width: 51px; height: 51px;" src="<?php echo '/api/upload/public/read?file='.$icon?>"></i>
<div class="desc" style="padding-left: 1em;">
<div class="text_header_1"><b><a href="<?php echo $link?>"><?php echo $title?></a></b></div>
<div>
    <?php echo htmlspecialchars_decode($description,ENT_QUOTES)?>
</div>
</div>
</div>
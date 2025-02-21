<?php

use App\Helpers\View\Loader;

echo Loader::asset('common_css', '/views/pages/components/common/common.css', 'css');
?>
<div class = "button button_uptop" onclick='$("body,html").animate({scrollTop: 0}, 500, "swing");'>

    <i class="fa fa-angle-up"></i>
    
</div>

<script type="text/javascript">

$(window).scroll(function(){
   if($('body').scrollTop() > 200 || $('html').scrollTop() > 200){
	   $(".button_uptop").css('visibility', 'unset');
   }else{
	   $(".button_uptop").css('visibility', 'hidden');
   }
});

</script>
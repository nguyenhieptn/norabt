<?php
use App\Helpers\View\Loader;
use Illuminate\Support\Facades\Input;
   
    $link = get($link, '#');
    $search = Input::get('search');
    echo Loader::asset('widget_css', '/views/pages/components/widget/widget.css', 'css');
?>

<div> 
    <input value='<?php echo $search?>' placeholder="@lang('widget.search')" id="article_search"/>
</div>

<script>
$("#article_search").change(function(){
	location.href = '<?php echo $link?>' + '?search=' + $(this).val();
});

</script>



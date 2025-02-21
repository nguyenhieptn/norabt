<?php 
    use Illuminate\Support\Facades\DB;
    $items = DB::table(ARTICLE_GROUP_TABLE)
    ->where(ART_GROUP_LANG, '=', session('lang'))
    ->orderBy(ART_GROUP_WEIGHT, 'DESC')
    ->get();
    
    $active = get($active, 'all');
    
?>
<style>


</style>
<ul class="nav nav-blog-feed menu_category" id="nav-blog-feed">
    <?php if($active == 'all'):?>
        <li class="nav-item">
          <a class="nav-link active" href="/pages/news?group=all&page=1"> <?php echo __('menu.all')?></a>
        </li>
    <?php else: ?>
        <li class="nav-item">
          <a class="nav-link" href="/pages/news?group=all&page=1"> <?php echo __('menu.all')?></a>
        </li>
    <?php endif;?>
    
    <?php foreach ($items as $item):?>
    
        <?php if($active == $item->{ART_GROUP_KEY}):?>
            <li class="nav-item">
                <a class="nav-link active" href="/pages/news?group=<?php echo $item->{ART_GROUP_KEY}?>&page=1"><?php echo $item->{ART_GROUP_TITLE}?></a>
            </li>
        <?php else: ?>
            <li class="nav-item">
                <a class="nav-link" href="/pages/news?group=<?php echo $item->{ART_GROUP_KEY}?>&page=1"><?php echo $item->{ART_GROUP_TITLE}?></a>
            </li>
        <?php endif;?>
    
    <?php endforeach;?>
    
</ul>
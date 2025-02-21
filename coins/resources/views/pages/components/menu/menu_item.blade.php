<?php 
use Illuminate\Support\Facades\DB;
$parent = get($parent, false);
$children = [];
if($parent){
    $children = DB::table(MENU_TABLE)
    ->where([
        [MENU_PUBLIC, '=', 1],
        [MENU_PARENT, '=', $parent->{MENU_ID}],
    ])
    ->orderBy(MENU_WEIGHT, 'DESC')
    ->get();
}
?>

<?php if($parent && count($children)==0):?>

    <li class="menu_item menu_item_parent"><a href="{{ $parent->{MENU_LINK} }}">{{ $parent->{MENU_TITLE} }}</a></li>

<?php elseif($parent && count($children)>0):?>

    <li class="menu_collapse">
        <div class="menu_group_button" onclick="toggleClass(this, 'expand', event)"><a href="{{ $parent->{MENU_LINK} }}">{{ $parent->{MENU_TITLE} }}</a></div>
        <ul class="menu_group">
        <?php foreach ($children as $menu):?>
            <li class="menu_item"><a href="{{ $menu->{MENU_LINK} }}">{{ $menu->{MENU_TITLE} }}</a></li>
        <?php endforeach;?>
        </ul>
    </li>

<?php endif;?>



<link rel = "stylesheet" href = "/views/pages/components/menu/menu.css" media = "all" type = "text/css" />

<?php 
use Illuminate\Support\Facades\App;
use Illuminate\Support\Facades\DB;
$lang = App::getLocale();
$l1Menus = DB::table(MENU_TABLE)
            ->where([
                [MENU_PARENT, '=', null],
                [MENU_PUBLIC, '=', '1'],
                [MENU_LANG, '=', $lang],
            ])
            ->orderBy(MENU_WEIGHT, 'inc')
            ->get();
            
            
?>

<div class="menu menu_expand_lg" style="background: #0d274d; color: white;">
    
    @component('pages.components.logo.logo')@endcomponent
    
    <div style="margin: auto 10px auto auto; font-size: 24px" class="menu_button" onclick="toggleClass(this, 'expand', event)"><i class="fa fa-navicon"></i></div>
   
    <div class = "menu_frame" style="margin: auto 15px auto auto; height: 100%">
        <div class="menu_logo">@component('pages.components.logo.logo_sm')@endcomponent <hr></div>
        <ul class="menu_content">
        
            <?php foreach ($l1Menus as $menu):?>
            @component('pages.components.menu.menu_item', ['parent'=>$menu])@endcomponent
            <?php endforeach;?>
    
        </ul>
      
    </div>
     
    <div class="menu_cover"></div>
    
</div>

<script src="/views/pages/components/menu/menu.js"></script>
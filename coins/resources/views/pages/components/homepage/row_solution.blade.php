<?php 
use Illuminate\Support\Facades\App;
use Illuminate\Support\Facades\DB;
$lang = App::getLocale();
$solutionlv1 = DB::table(SOLUTIONS_TABLE)
            ->where([
                [SOLUTION_PARENT, '=', null],
                [SOLUTION_LANG, '=', $lang],
            ])
            ->orderBy(SOLUTION_WEIGHT, 'DESC')
            ->get();
            
            
?>

<style>
.service:hover {
    background: #fcfcfc;
    box-shadow: 0 0 5px #ddd;
    -webkit-transition: box-shadow .2s ease-in-out;
    -moz-transition: box-shadow .2s ease-in-out;
    -o-transition: box-shadow .2s ease-in-out;
    transition: box-shadow .2s ease-in-out;
}
}
</style>
<div class="container">
  
  <div class="row justify-content-md-center mb-05">
    <?php foreach ($solutionlv1 as $solution):?>
     <div class="col-sm-6 col-lg-4">
     @component('pages.components.item_solution', ['solution' => $solution])@endcomponent
     </div>
    <?php endforeach ?>
  </div>
</div>

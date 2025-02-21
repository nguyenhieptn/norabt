
    <?php 
    $articles = resolve('Article')->getCategoryArticles('case-study', 4);
    
    ?>
    <div class="row">
        <?php foreach ($articles as $article):?>
        <div class="col-sm-6 col-md-3 ">
            @component('pages.components.item_article',['article' => $article])@endcomponent
        </div>
        <?php endforeach;?>
    </div>

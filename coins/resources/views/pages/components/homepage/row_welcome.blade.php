
<div class="row">
	<div class="col-sm-8">
	<div class="headline">
		<div class="text_header">@lang('page.welcome')</div>
	</div>
	<div style="text-align: justify;">
		@lang('page.welcome_text') 
    </div>
    </div>

    <div class="col-md-4">
	<div class="headline">
		<div class="text_header">@lang('page.lastest_shots')</div>
	</div>
	<?php $articles = resolve('Article')->getLastArticles(8);?>
	<div class="carousel slide" data-ride="carousel">
		<div class="carousel-inner">
		      <?php 
		      $start = floor(count($articles)/2);
		      foreach ($articles as $key => $article):
		          if($key == $start):?>
            			<div class="carousel-item active">
            				<a href="/article/<?php echo $article->{ART_SLUG}?>">
            				    <div  style="background-image:url('<?php echo APP_UPLOAD.'/uploader/public/read?file='.$article->{ART_FEATURE_IMG}?>'); height:200px; background-size: cover; background-position: center;"></div>
            				</a>
            			</div>
            	<?php else:?>
            			<div class="carousel-item">
            				<a href="/article/<?php echo $article->{ART_SLUG}?>">
            				<div  style="background-image:url('<?php echo APP_UPLOAD.'/uploader/public/read?file='.$article->{ART_FEATURE_IMG}?>'); height:200px; background-size: cover; background-position: center;"></div>
            				</a>
            			</div>
            	<?php endif; endforeach;?>
		</div>
	</div>
    </div>
</div>

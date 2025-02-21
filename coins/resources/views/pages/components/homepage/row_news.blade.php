<div class="container-fluid homepage-5-container mt-05 mb-05">
    <div class="container">
      <div class="row">
        <div class="col-12">
          <h3 class="mt-05">Latest News at ITC</h3>
        </div>
      </div>
      <div class="row justify-content-md-center mb-05">
        <?php
          foreach ($articles as $article):

          $link = 'blog/a/' . $article->aid . '/';
        ?>
          <div class="col-6 col-lg-3">
            <div class="card card-news">
              <div class="card-body">
                <a class="card-title" href="{{$link}}">{{ str_limit($article->title, 50) }}</a>
                <p class="card-text mt-3">{{ date('d/m/Y' ,strtotime($article->created_date)) }}</p>
                <p class="card-text">{{ str_limit($article->sapo, 100) }}</p>
                <a href="{{$link}}" class="card-link">Read more</a>
              </div>
            </div>
          </div>
        <?php endforeach ?>
      </div>
    </div>
  </div>
<!-- Important Owl stylesheet -->
<link rel="stylesheet" href="/extensions/owl_carousel/owl.carousel.css">

<!-- Default Theme -->
<link rel="stylesheet" href="/extensions/owl_carousel/owl.theme.css">

<!-- Include js plugin -->
<script src="/extensions/owl_carousel/owl.carousel.min.js"></script>

<style>
#owl-demo .item{
    margin: 3px;
    padding: 25px;
}
#owl-demo .item img{
  display: block;
  width: 100%;
  height: auto;
}
#owl-demo .item{
    padding: 40px;
}
</style>
<div class="container">

    <div id="owl-demo">
          <?php $customers = resolve('Customer')->getCustomers();
          foreach ($customers as $customer):?>
          <div class="item"><img src="<?php echo APP_UPLOAD.'api/upload/public/read?file='.$customer->{CUSTOMER_IMG}?>" alt=""></div>
         <?php endforeach;?>
    </div>

	
</div>

<script>
$(document).ready(function() {
	 
	  $("#owl-demo").owlCarousel({
	 
	      autoPlay: 3000, //Set AutoPlay to 3 seconds
	 
	      items : 4,
	      //itemsDesktop : [1199,3],
	      //itemsDesktopSmall : [979,3]
	 
	  });
	 
	});

</script>
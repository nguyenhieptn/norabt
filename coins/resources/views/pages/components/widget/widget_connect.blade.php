
<?php

use App\Helpers\View\Loader;

echo Loader::asset('widget_css', '/views/pages/components/widget/widget.css', 'css'); 

?>

<div class="headline"  style="margin-bottom:10px;">
    <div class="text_header">@lang('page.Contact Form')</div>
</div>

<p>@lang('page.Contact Form Text')</p>

<form onsubmit="sendEmail(event)" class="connect_form">
    <div><input class="connect_email" type="email" placeholder="Your Email" required></div>
    <div><input class="connect_name" type="text" placeholder="@lang('widget.email_name')"></div>
    <div><input class="connect_phone" type="text" placeholder="@lang('widget.email_phone')"></div>
    <div><textarea class="connect_message" rows="5" cols="" placeholder="@lang('widget.email_content')"></textarea></div>
    @component('pages.components.captchar', ['ref'=>'sendemail'])@endcomponent
    <div><button type="submit" class="button">@lang('widget.sent_email')</button></div>
</form>

<script>
function sendEmail(event){
	<?php echo FUNC_SHOW_LOADING?>('Email sending...');
	event.preventDefault();
	let email = $(".connect_email").val();
	let name = $(".connect_name").val();
	let phone = $(".connect_phone").val();
	let message = $(".connect_message").val();
	let captcha = sendemail.getCaptcha();

	datas = {
			name: name, 
			email: email, 
			phone: phone, 
			message: message,
			
			}
	
	$.ajax({
		  method: "POST",
		  url: "/page/page/customer_connect",
		  dataType: "JSON",
		  data: {data: datas, captcha: captcha},
		})
		.done(function(result) {
			<?php echo FUNC_HIDE_LOADING?>();
		    if(result['result']){
		    	$(".connect_email").val('');
		    	$(".connect_name").val('');
		    	$(".connect_phone").val('');
		    	$(".connect_message").val('');
		    	Swal("", result['message'], 'success');
		    	
		    }else{
		    	Swal("Error", result['message'], 'error');
		    }
		    sendemail.reloadCapt();
		})
		.fail(function(e) {
			<?php echo FUNC_HIDE_LOADING?>();
			Swal('Error', e, 'error');
			sendemail.reloadCapt();
    })
	
}


</script>

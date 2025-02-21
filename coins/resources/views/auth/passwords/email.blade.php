<?php 
$ref = get($ref, 'global');
?>

<div class="modal fade" id="{{$ref}}_resetpass_modal">
    <div class="modal-dialog">
      <div class="modal-content">
      
        <!-- Modal Header -->
        <div class="modal-header">
          <h4 class="modal-title">Reset Password</h4>
          <button type="button" class="close" data-dismiss="modal">&times;</button>
        </div>
        
        <!-- Modal body -->
        <div class="modal-body">
			<p>Fill your email:</p>
			@component('auth.register.alert', ['ref'=>'resetpass_alert'])@endcomponent
            <div>
                <input class='form-control' id="{{$ref}}_resetpass" type="text" style="width:100%"/>
			</div>
			<br/>
			<div class='d-flex'>@component('auth.captchar', ['ref'=>'resetpass_captcha'])@endcomponent</div>
        </div>
        
        <!-- Modal footer -->
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" onClick="{{$ref}}.sendEmail()" >Send Reset Link</button>
          <button type="button" class="btn btn-danger" data-dismiss="modal">Close</button>
        </div>
        
      </div>
    </div>
  </div>

<script>

if(typeof({{$ref}}) == "undefined") {{$ref}} = {
	modalComp : $("#{{$ref}}_resetpass_modal"),
	inputComp : $("#{{$ref}}_resetpass"),
	modal : function(flag = ''){
				if(flag == ''){
					this.modalComp.modal();
				}else{
					this.modalComp.modal(flag);
				}
				resetpass_captcha.reloadCapt();
			},
	setValue: function(value){
		this.inputComp.val(value);
	},
	sendEmail : function(){
			loader.loading();
			$.ajax({
				method: "POST",
				url: "/guest/password/sendEmail",
				data: { 
					email: this.inputComp.val(),
					captcha: resetpass_captcha.getCaptcha(),
				}
				})
				.done(function( response ) {
					resetpass_captcha.reloadCapt();
					loader.loading('hide');
					if(response['result']){
						resetpass_alert.showLog(response['data'], 'success');
					}else{
						resetpass_alert.showLog(response['message']);
					}
				})
				.fail(function(msg) {
					resetpass_captcha.reloadCapt();
					loader.loading('hide');
					resetpass_alert.showLog('Unknow Error');
				})
			}
};

</script>

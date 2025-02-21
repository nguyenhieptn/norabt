<?php 
$ref = get($ref, 'global');
?>

<div class="modal fade" id="{{$ref}}_reverify_modal">
    <div class="modal-dialog">
      <div class="modal-content">
      
        <!-- Modal Header -->
        <div class="modal-header">
          <h4 class="modal-title">Resend the confirmation email</h4>
          <button type="button" class="close" data-dismiss="modal">&times;</button>
        </div>
        
        <!-- Modal body -->
        <div class="modal-body">
			<p>Fill your email:</p>
			@component('auth.register.alert', ['ref'=>'reverify_alert'])@endcomponent
            <div>
                <input class='form-control' id="{{$ref}}_reverify_email" type="text" style="width:100%"/>
			</div>
			<br/>
			<div class='d-flex'>@component('auth.captchar', ['ref'=>'reverify_captcha'])@endcomponent</div>
        </div>
        
        <!-- Modal footer -->
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" onClick="{{$ref}}.sendEmail()" >Send</button>
          <button type="button" class="btn btn-danger" data-dismiss="modal">Close</button>
        </div>
        
      </div>
    </div>
  </div>

<script>

if(typeof({{$ref}}) == "undefined") {{$ref}} = {
	modalComp : $("#{{$ref}}_reverify_modal"),
	inputComp : $("#{{$ref}}_reverify_email"),
	modal : function(flag = ''){
				if(flag == ''){
					this.modalComp.modal();
				}else{
					this.modalComp.modal(flag);
				}
				reverify_captcha.reloadCapt();
			},
	setValue: function(value){
		this.inputComp.val(value);
	},
	sendEmail : function(){
			loader.loading();
			$.ajax({
				method: "POST",
				url: "/guest/register/reverify",
				data: { 
					email: this.inputComp.val(),
					captcha: reverify_captcha.getCaptcha(),
				}
				})
				.done(function( response ) {
					reverify_captcha.reloadCapt();
					loader.loading('hide');
					if(response['result']){
						reverify_alert.showLog(response['data'], 'success');
					}else{
						reverify_alert.showLog(response['message']);
					}
				})
				.fail(function(msg) {
					reverify_captcha.reloadCapt();
					loader.loading('hide');
					reverify_alert.showLog('Unknow Error');
				})
			}
};

</script>

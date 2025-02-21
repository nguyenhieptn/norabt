<?php 
$ref = get($ref , 'global');
?>


<div style='
	display: flex;
    border: solid thin #0d274d;
    overflow: hidden;
    height: 40px;
    border-radius: 5px;
'>
<div id='{{$ref}}captchar_img' style='
    border: none;
' class="button" title="Reload Captcha" onclick="{{$ref}}.reloadCapt()"></div>
<input autocomplete="off" type='text' id='{{$ref}}captchar_code' style='
    margin: 0px; 
    width:80px; 
	height:40px;
	border:none;
    border-left:solid thin;
	padding: 5px;
    '/>
</div>

<div style='display: none' id='captchar_md5'></div>

<script type="text/javascript">


var {{$ref}} = {
	captchar_code: $('#{{$ref}}captchar_code'),
	captchar_img: $('#{{$ref}}captchar_img'),
	getCaptcha : function (){
					return {
						{{$ref}}: this.captchar_code.val(),
					}
				},

	reloadCapt : function (){
				$.ajax({
					method: "POST",
					url: "/captcha",
					dataType: "JSON",
					data: {
						id:'{{$ref}}'
					}
					})
					.done(function(result) {
						if(result['result']){
							{{$ref}}.captchar_img.html(result['data']['img']);
						}else{
							Swal(result['message'], result['data'], 'error');
						}
					}.bind(this))
					.fail(function(e) {
						Swal('Error', e, 'error');
				})
			},
				
	
	
	};



</script>
<?php 
$ref = get($ref , 'global');
?>


<div style='display: flex; align-items: center;'>
<div id='{{$ref}}captchar_img' style='
    border: solid thin;
    border-bottom-left-radius: 4px;
    border-top-left-radius: 4px;
    '></div>
<input autocomplete="off" type='text' id='{{$ref}}captchar_code' style='
    margin: 0px; 
    width:80px; 
    height:42px;
    border: solid thin;
    border-bottom-right-radius: 4px;
    border-top-right-radius: 4px;
    border-left:none;
    '/>
</div>

<div style='display: none' id='captchar_md5'></div>

<script type="text/javascript">


var {{$ref}} = {};
{{$ref}}.getCaptcha = function (){
                        	return {
                        		{{$ref}}: $('#{{$ref}}captchar_code').val(),
                        	}
                        }



{{$ref}}.reloadCapt = function (){
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
		    	$('#{{$ref}}captchar_img').html(result['data']['img']);
		    }else{
		    	Swal(result['message'], result['data'], 'error');
		    }
		    
		})
		.fail(function(e) {
			Swal('Error', e, 'error');
	})
}

{{$ref}}.reloadCapt();

</script>
<?php 
$ref = get($ref, 'global');
?>

<div>
    <div id="{{$ref}}_error_message" class="alert alert-danger" style='display:none'></div>
    <div id="{{$ref}}_success_message" class="alert alert-success" style='display:none'></div>
</div>

<script>
    if(typeof({{$ref}}) == "undefined") {{$ref}} = {
        errorMessage : $("#{{$ref}}_error_message"),
        successMessage : $("#{{$ref}}_success_message"),

        showLog : function(log, type = 'error') {
            if (type == 'error') {
                this.errorMessage.html(log);
                this.errorMessage.css('display', 'block');
                this.successMessage.css('display', 'none');
            } else {
                this.successMessage.html(log);
                this.successMessage.css('display', 'block');
                this.errorMessage.css('display', 'none');
            }
        }
    }
</script>
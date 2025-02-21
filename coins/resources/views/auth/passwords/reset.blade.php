@extends('auth.layout', ['title'=>'Reset Password', 'favicon' => '#'])

@section('content')

<div class="login_head">
   
</div>
<!--end::Head-->

<!--begin::Body-->
<div class="login_body">

    <!--begin::Signin-->
    <div class="login_form">
        <div class="login_title">
            <h3>New Password</h3>
        </div>

        @component('auth.register.alert', ['ref'=>'resetpass_alert'])@endcomponent

        <!--begin::Form-->
        <form class="form" onsubmit="return resetHandle(event)" id="login_form">
            <div class="form-group">
                <input id="input_password" class="form-control" type="password" placeholder="Password" name="password" autocomplete="off" required>
            </div>
            <div class="form-group">
                <input id="input_password_again" class="form-control" type="password" placeholder="Password again" name="password" autocomplete="off" required>
            </div>
            <!--begin::Action-->
            <div class="login_action">
                <div><button class="btn btn-primary" type="submit">Reset</button></div>
            </div>



            <!--end::Action-->
        </form>
        <!--end::Form-->


    </div>
    <!--end::Signin-->
</div>
<!--end::Body-->

<script>

    
    
    function resetHandle(event) {
        event.preventDefault();
        var nextLink = "<?php echo get($_GET['link'], '/login') ?>";

        var passwordInput = $("#input_password");
        var passwordInputAgain = $("#input_password_again");

        if(passwordInput.val() != passwordInputAgain.val()){
            resetpass_alert.showLog('Password not match');
            return;
        }

        var token = '{{$token}}';

        loader.loading();
        $.ajax({
                method: "POST",
                url: "/guest/password/reset",
                data: {
                    token: token,
                    password: btoa(passwordInput.val()),
                }
            })
            .done(function(result) {
                loader.loading('hide');
                if (result['result']) {
                    window.location = `${nextLink}?success=${result['data']}`;
                } else {
                    resetpass_alert.showLog(result['message']);
                }
            })
            .fail(function(msg) {
                loader.loading('hide');
                resetpass_alert.showLog(msg.responseText);
            })
            return false;
    }


</script>

@endsection
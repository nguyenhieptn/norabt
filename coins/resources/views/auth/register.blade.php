@extends('auth.layout', ['title'=>'Register', 'favicon' => '#'])

@section('content')



<!--begin::Head-->
<div class="login_head">
    <span class="login_signup-label">You already have an account?</span>&nbsp;&nbsp;
    <a href="/login" class="link login_signup-link">Login!</a>
</div>
<!--end::Head-->

<!--begin::Body-->
<div class="login_body">

    <!--begin::Signin-->
    <div class="login_form">
        <div>
            <h3>Sign In</h3>
        </div>

        @component('auth.register.alert', ['ref'=>'register_alert'])@endcomponent


        <!--begin::Form-->
        <form class="form" onsubmit="return registerHandle(event)" id="login_form">

            <div>

                <input id="input_username" class="form-control" type="text" placeholder="Enter Username" name="username" required>
            </div>

            <div>

                <input id="input_email" class="form-control" type="text" placeholder="Email" name="email" required>
            </div>

            <div>

                <input id="input_password" class="form-control" type="password" placeholder="Enter Password" name="password" required>
            </div>

            <div>

                <input id="input_password_again" class="form-control" type="password" placeholder="Enter Password Again" name="password_again" required>
            </div>


            <!--begin::Action-->

            <div class="login_action">
                <div>@component('auth.captchar', ['ref'=>'register'])@endcomponent</div>
                <div><button class="btn btn-primary" type="submit">Register</button></div>
            </div>



            <!--end::Action-->
        </form>
        <!--end::Form-->


    </div>
    <!--end::Signin-->
</div>
<!--end::Body-->
@component('auth.register.reverify', ['ref'=>'reverify_modal'])@endcomponent
@component('auth.passwords.email', ['ref'=>'emailReset'])@endcomponent

<script>

    function reverify(){
        reverify_modal.modal();
        reverify_modal.setValue($("#input_email").val());
    }

    function registerHandle(event) {
        event.preventDefault();
        var usernameInput = $("#input_username");
        var passwordInput = $("#input_password");
        var passwordAgainInput = $("#input_password_again");
        var emailInput = $("#input_email");

        var username = usernameInput.val();
        if (username == '') usernameInput.focus();

        var password = passwordInput.val();
        if (password == '') passwordInput.focus();

        var passwordAgain = passwordAgainInput.val();
        if (passwordAgain == '') passwordAgainInput.focus();

        var email = emailInput.val();
        if (email == '') emailInput.focus();

        var next = "<?php echo get($_GET['link'], '/login') ?>";

        if (password != passwordAgain) {
            showLog('Password Not match');
            return false;
        }
        loader.loading();
        $.ajax({
                method: "POST",
                url: "/guest/register/register",
                data: {
                    username: username,
                    password: btoa(password),
                    email: email,
                    captcha: register.getCaptcha(),
                }
            })
            .done(function(result) {
                loader.loading('hide');
                if (result['result']) {
                    window.location.href = `${next}?success=${encodeURI(result['data'])}`;
                } else {
                    register.reloadCapt();
                    register_alert.showLog(result['message']);
                }
            })
            .fail(function(msg) {
                loader.loading('hide')
                register.reloadCapt();
                register_alert.showLog(msg.responseText);
            })
        return false;
    }

    window.onload = function () {
        var variable = getUrlVars();
        if(variable['success'] && variable['success'] != '') register_alert.showLog(variable['success'], 'success');
        if(variable['error'] && variable['error'] != '') register_alert.showLog(variable['error']);
        register.reloadCapt();
    }
</script>

@endsection
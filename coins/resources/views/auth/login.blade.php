<?php
$box = get($_GET['box'], '');
$offlineLogin = '';
if (preg_match('/https?\:\/\/[^\/\s]+/', $box, $matches)) {
    $offlineLogin = $matches[0];
}
?>

@extends('auth.layout', ['title'=>'Login', 'favicon' => '#'])

@section('content')

<div class="login_head">
    <span class="login_signup-label">Don't have an account yet?</span>&nbsp;&nbsp;
    <a href="/guest/register/view" class="link login_signup-link">Sign Up!</a>
</div>
<!--end::Head-->

<!--begin::Body-->
<div class="login_body">

    <!--begin::Signin-->
    <div class="login_form">
        <div>
            <h3>Login</h3>
        </div>

        @component('auth.register.alert', ['ref'=>'login_alert'])@endcomponent

        <!--begin::Form-->
        <form class="form" onsubmit="return loginHandle(event)" id="login_form">
            <div class="form-group">
                <input id="input_username" class="form-control" type="text" placeholder="Username or Email" name="username" autocomplete="off" required>
            </div>
            <div class="form-group">
                <input id="input_password" class="form-control" type="password" placeholder="Password" name="password" autocomplete="off" required>
            </div>

            <!--begin::Action-->
            <div class="col-md-6"><span class="button" onClick="resetPass()"><a href="#" tabindex="-1">Forgot password?</a></span></div>
            <div class="login_action">
                <div>@component('auth.captchar', ['ref'=>'login'])@endcomponent</div>
                <div><button class="btn btn-primary" type="submit" style="padding: 7px 50px;">Login</button></div>
            </div>

            <!--end::Action-->
        </form>
        <!--end::Form-->


    </div>


    <!--end::Signin-->
</div>
<!--end::Body-->
@component('auth.passwords.email', ['ref'=>'emailReset'])@endcomponent
@component('auth.register.reverify', ['ref'=>'reverify_modal'])@endcomponent

<script>
    function reverify() {
        reverify_modal.modal();
    }

    function resetPass() {
        emailReset.modal();
    }

    function loginHandle(event) {
        event.preventDefault();
        var nextLink = "<?php echo get($_GET['link'], '') ?>";
        var userNameInput = $("#input_username");
        var passwordInput = $("#input_password");
        var htmlInput = $("#input_html");

        localStorage.setItem("console", htmlInput.val());

        if (userNameInput.val() == '') {
            userNameInput.focus();
            return;
        }
        if (passwordInput.val() == '') {
            passwordInput.focus();
            return;
        }
        loader.loading();
        $.ajax({
                method: "POST",
                url: "/guest/login/login",
                data: {
                    username: userNameInput.val(),
                    password: btoa(passwordInput.val()),
                    captcha: login.getCaptcha(),
                }
            })
            .done(function(result) {
                // loader.loading('hide');
                if (result['result']) {

                    $.ajax({
                        method: "POST",
                        url: "/",
                        data: {
                            user : userNameInput.val(),
                            app: 'Phoenix Local',
                            secret: 'phoenix_login_detect'
                        }
                    }).done(function(){

                        var regex = /^https?:\/\/[^\/]*/gm;

                        var nextLinkDomain = regex.exec(nextLink);
                        if (nextLinkDomain) {
                            nextLinkDomain = nextLinkDomain[0];
                        }

                        var originDomain = window.location.origin;

                        if (nextLink == '' || nextLinkDomain == null) {
                            window.location.href = '/';
                            return;
                        }
                        
                        if (originDomain == nextLinkDomain) {
                            window.location.href = nextLink;
                        } else {
                            setToken(nextLinkDomain, result['data']['token'], nextLink)
                        }
                        
                    })

                    


                } else {
                    loader.loading('hide');
                    login.reloadCapt();
                    login_alert.showLog(result['message']);

                }
            })
            .fail(function(msg) {
                loader.loading('hide');
                login.reloadCapt();
                login_alert.showLog(msg.responseText);
            })
        return false;
    }


    window.onload = function() {
        var variable = getUrlVars();
        if (variable['success'] && variable['success'] != '') login_alert.showLog(variable['success'], 'success');
        if (variable['error'] && variable['error'] != '') login_alert.showLog(variable['error']);
        login.reloadCapt();
    }

    function setToken(domain, token, nextLink) {
        post(domain + "/auth/setToken", {
            token: token,
            next: nextLink
        });
    }

    function post(path, params, method = 'post') {

        // The rest of this code assumes you are not using a library.
        // It can be made less wordy if you use one.
        const form = document.createElement('form');
        form.method = method;
        form.action = path;
        for (const key in params) {
            const hiddenField = document.createElement('input');
            hiddenField.type = 'hidden';
            hiddenField.name = key;
            hiddenField.value = params[key];
            form.appendChild(hiddenField);
        }
        document.body.appendChild(form);
        form.submit();
    }
</script>

@endsection
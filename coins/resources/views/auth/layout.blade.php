@extends('auth.document', ['title'=>$title, 'favicon' => $favicon])

@section('body')

<link rel="stylesheet" href="/assets/auth/css/main.css">
<script src="/assets/auth/js/authen.js"></script>

<div class="login_frame">
    <!--begin::Aside-->
    <!-- <div class="login_banner" style="background-image: linear-gradient(145deg, #0d274d 0%, #26a69a 51%, #142844 75%);"> -->
    <div class="login_banner" style="background: linear-gradient(145deg, #1e252e 0%, #060818 51%, #0b121d 75%);">
    <!-- <div class="login_banner" style="background: #060818"> -->
        <div class="login_title" style="text-align:center">
            <h1>Welcome to Nora System </h1>
            <div class="login_slogan">
                <!-- <h1>Your attitude, not your aptitude, will determine your position</h1> -->

            </div>
        </div>

        <div class='login_logo d-flex'>
            <div style='margin:auto'>

                <div class="login_logo">
                    <!-- <img src="/assets/auth/img/phoenix-viewer-logo.png" alt=""> -->
                    <img src="/assets/img/Eicon.png" alt="">
                </div>
                <br />
                <div class="login_slogan">

                </div>


            </div>
        </div>


        <div class="login_copyright" style="margin: auto auto 15px auto">
            <div>
                <div>
                    © 2021 NORA SYSTEM
                </div>
            </div>
        </div>
    </div>
    <!--begin::Aside-->

    <!--begin::Content-->
    <div class="login_main">
        @yield('content')
    </div>
</div>

@endsection
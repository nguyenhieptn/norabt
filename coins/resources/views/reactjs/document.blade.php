<!DOCTYPE html>
<html>

<head>
    <title>{{get($title, APP_TITLE)}}</title>

    <meta charSet="utf-8" />

    <meta name="viewport" content="width=device-width, initial-scale=0.7">

    <!--    <meta name="csrf-token" content="{{ csrf_token() }}"> -->

    <link rel="shortcut icon" type="image/png" href="/assets/img/Eicon.png" />

    <link rel="stylesheet" href="/extensions/icons/css/font-awesome.min.css" media="all" type="text/css" />

    <script src="/extensions/jquery/jquery-3.3.1.min.js"></script>
    <script src="/extensions/jquery/jquery-ui.min.js"></script>

    <link href="/extensions/bootstrap/css/bootstrap.min.css" rel="stylesheet" media="all" type="text/css" />
    <script src="/extensions/bootstrap/js/popper.min.js"></script>
    <script src="/extensions/bootstrap/js/bootstrap.min.js"></script>

    <link rel="stylesheet" href="/extensions/hover/hover.css">

    <link rel="stylesheet" href="/extensions/animate/animate.min.css">
    <script src="/extensions/animate/wow.js"></script>

    <script src="/extensions/swal2/swal2.all.min.js"></script>

    <link href="/extensions/datetimepicker/css/bootstrap-datetimepicker.min.css" rel="stylesheet" />
    <script src="/extensions/datetimepicker/js/moment.js"></script>
    <script src="/extensions/datetimepicker/js/bootstrap-datetimepicker.min.js"></script>

    <link href="/extensions/table/resizable/resizable.css" rel="stylesheet" />
    <script src="/extensions/table/resizable/resizable.js"></script>

    <link href="/assets/css/app.css" rel="stylesheet" />
    <link href="/extensions/ckeditor/ckeditor.css" rel="stylesheet" />

    <script src="/assets/js/default.js"></script>
    <script src="/assets/js/cookies.js"></script>
    <script src="/assets/js/config.js"></script>

    <script src="/extensions/nanoscroller/nanoscroller.js"></script>
    <link href="/extensions/nanoscroller/nanoscroller.css" rel="stylesheet" />

    <!-- <script src="https://cdn.plot.ly/plotly-latest.js"></script> -->
    <!-- <script src="https://cdn.plot.ly/plotly-2.12.1.min.js"></script> -->
    <script src="/extensions/plotly/plotly-2.12.1.min.js"></script>



</head>

<body>

    @yield('body')
    @component('reactjs.button_up')@endcomponent

</body>

<footer>
    @yield('footer')

    <script>
        //             new WOW().init();
        //             $.ajaxSetup({
        //                 headers: {
        //                     'X-CSRF-TOKEN': $('meta[name="csrf-token"]').attr('content')
        //                 }
        //             });
    </script>

</footer>



</html>
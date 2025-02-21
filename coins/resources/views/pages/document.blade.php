<!DOCTYPE html>

<html>
    <head>
        <title>{{get($title, APP_TITLE)}}</title>
        
          <meta charSet="utf-8"/>
          
          <title>{{get($title, APP_TITLE)}}</title>
        
            <meta charSet="utf-8"/>
            
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
            
            <link rel="shortcut icon" type="image/png" href="/assets/img/logo.png"/>
            
            <link rel = "stylesheet" href = "/extensions/icons/css/font-awesome.min.css" media = "all" type = "text/css" />
            
            <script src = "/extensions/jquery/jquery-3.3.1.min.js"></script>
            <script src = "/extensions/jquery/jquery-ui.min.js"></script>
            
            <link href = "/extensions/bootstrap/css/bootstrap.min.css" rel = "stylesheet" media = "all" type = "text/css" />
            <script src = "/extensions/bootstrap/js/popper.min.js"></script>
            <script src = "/extensions/bootstrap/js/bootstrap.min.js"></script>
            
            <link rel="stylesheet" href="/extensions/hover/hover.css">
            
            <link rel="stylesheet" href="/extensions/animate/animate.min.css">
            <script src="/extensions/animate/wow.js"></script>
            
            <script src="/extensions/swal2/swal2.all.min.js"></script>
            
            <link href = "/extensions/datetimepicker/css/bootstrap-datetimepicker.min.css" rel = "stylesheet"/>
            <script src="/extensions/datetimepicker/js/moment.js"></script>
            <!-- <script src="/extensions/datetimepicker/js/bootstrap-datetimepicker.min.js"></script> -->
            
            <link href = "/extensions/ckeditor/ckeditor.css" rel = "stylesheet" />
            <link href = "/assets/css/app.css" rel = "stylesheet" />

            <!-- <link href = "/extensions/table/resizable/resizable.css" rel = "stylesheet" />
            <script src="/extensions/table/resizable/resizable.js"></script> -->
            
            <script src="/assets/js/default.js"></script>
            <script src="/assets/js/cookies.js"></script>

    </head>
    
    <body style="overflow-x: hidden">
        @component('pages.components.menu.simplemenu')@endcomponent
        @yield('body')
        @component('pages.components.common.button_up')@endcomponent
        @component('pages.components.common.loading')@endcomponent
        @component('pages.components.common.imageview')@endcomponent
    </body>
    
    
    <script>
        new WOW().init();
    </script>   
    
</html>

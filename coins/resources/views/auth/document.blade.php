<!DOCTYPE html>
<html>
    <head>
        <title>{{get($title, APP_TITLE)}}</title>
        
          <meta charSet="utf-8"/>
  
          <meta name="viewport" content="initial-scale=1.0, width=device-width"/>
    
          <link rel="shortcut icon" type="image/png" href="/public/images/builder/logo_admin.png"/>
    
          <link rel = "stylesheet" href = "/extensions/icons/css/font-awesome.min.css" media = "all" type = "text/css" />
    
          <link rel = "stylesheet" href = "/extensions/bootstrap/css/bootstrap.min.css" media = "all" type = "text/css" />
          
          <link rel="stylesheet" href="/extensions/animate/animate.min.css">
          
          <link rel="stylesheet" href="/extensions/hover/hover.css">
    
          <script src="/extensions/jquery/jquery-3.3.1.min.js"></script>
    
          <script src="/extensions/bootstrap/js/popper.min.js"></script>
    
          <script src="/extensions/bootstrap/js/bootstrap.min.js"></script>
          
          <script src="/extensions/swal2/swal2.all.min.js"></script>
          
          <script src="/assets/js/default.js"></script>
          <script src="/assets/js/cookies.js"></script>
          
          <script>
            $.ajaxSetup({
                headers: {
                    'X-XSRF-TOKEN': getCookie('XSRF-TOKEN')
                }
            });
         </script>   
          
          

    </head>
    
    <body>
    
        
    
        <div style="display: flex; width: 100%; min-height: 100%; height: 100%;">
                    
            <div class = "main" style="width: 100%;">
                @yield('body')
                @component('auth.loading', ['ref'=>'loader'])@endcomponent
            </div>
        </div>
        
    </body>
    
    <footer>
        @yield('footer') 
        
        
        
    </footer>
    

    
</html>

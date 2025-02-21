
<div class="dropdown btn">
    <a class="dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
    
        @if(session('lang') == 'en')
        <img src="/assets/pages/components/language/US.png"> English
        @else
        <img src="/assets/pages/components/language/VN.png"> Tiếng Việt
        @endif
        
    </a>
    <div class="dropdown-menu" aria-labelledby="nav-aboutus">
    <a class="dropdown-item" href="/page/page/lang?lang=en" id="lang_en"><img src="/assets/pages/components/language/US.png"> English</a>
    <a class="dropdown-item" href="/page/page/lang?lang=vi" id="lang_vi"><img src="/assets/pages/components/language/VN.png"> Tiếng Việt</a>
    </div>
</div>
    
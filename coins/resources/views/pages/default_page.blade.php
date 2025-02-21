@extends('pages.document') 
@section('body')


<div class="ck-content" id="page_default_content">
    @yield('main')
</div>


<script>
    document.getElementById('page_default_content').style.minHeight = (window.innerHeight-80-180) + 'px';
</script>

@endsection

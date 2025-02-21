
<script type="text/javascript">

$('.zoom img').click(function(){
    var img = $(this);
    var src = img.attr('src');
    var div = $(`<div style="
        position: fixed;
        top: 0px;
        left: 0px;
        right: 0px;
        bottom: 0px;
        padding: 10%;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
    ">
        <div style="
        margin: auto;
        width: 100%;
        height: 100%;
        background-image: url(${src});
        background-repeat: no-repeat;
        background-position: center center;
        background-size: contain;
        "></div>
    </div>`)

    var close = $(`<div class='button' style="
        position: absolute;
        top: 15px;
        right: 15px;
        font-size: 48px;
        color: white;
    ">&times;</div>`)
    div.append(close);
    $( "body" ).append(div);
    $(close).click(function(){
        div.remove();
    })
})

</script>

<style>
    .zoom img {
        cursor:pointer;
    }
</style>
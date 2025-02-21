<?php 

$contents = [
    [
        'icon' => '/assets/pages/components/row_why/illus-01.png',
        'title' => '1. World-class AI system',
        'content' => 'FPT.AI is researched and developed by top scientists and engineers in Machine Learning, Natural Language Processing/Understanding, Computer vision, hence, providing first-class qualified solutions for your business with 24/7 support.'
        
    ],
    [
        'icon' => '/assets/pages/components/row_why/illus-02-1.png',
        'title' => '2. World-class AI system',
        'content' => 'FPT.AI is researched and developed by top scientists and engineers in Machine Learning, Natural Language Processing/Understanding, Computer vision, hence, providing first-class qualified solutions for your business with 24/7 support.'
    
    ],
    [
        'icon' => '/assets/pages/components/row_why/illus-3.png',
        'title' => '3. World-class AI system',
        'content' => 'FPT.AI is researched and developed by top scientists and engineers in Machine Learning, Natural Language Processing/Understanding, Computer vision, hence, providing first-class qualified solutions for your business with 24/7 support.'
    ]
]

?>

<style>

    .why_title{
    	opacity: 0.6;
    	cursor: pointer;
    	font-weight: bold;
    	padding: 5px;
    }
    .why_title.selected{
    	opacity: 1;
    }
    .why_image{
    	display: none;
    }
    .why_image.selected{
    	display: flex;
    }
    .why_content{
    	display:none;
    	text-align: justify;
    }
    .why_content.selected{
    	display:flex;
    }
    
    .why_title_container{
        justify-content: space-between;
    }
    
    .why_container {
    	display: flex;
    	align-items: center;
    	padding: 15px 0px;
    }
    
    @media only screen and (min-width: 768px) {
    	
        .why_title_container{
            flex-direction: column;
        	padding: 30px;
        }
      
    }
    @media only screen and (max-width: 768px) {
      
        .why_title_container{
        	padding: 15px;
        }
    }


</style>
<div class="headline">
		<div class="text_header">Why choose us?</div>
</div>
<div class='row'>

    <div class='col-md-4 why_container why_title_container'>
        
            <?php foreach ($contents as $key=>$content):?>
            <h5 class="why_title" onClick="rowwhy.select('{{$key}}')">{{$content['title']}}</h5>
            <?php endforeach;?>
        
    
    </div>
    <div class='col-md-4 why_container'>
        <div style="display: flex;">
            <?php foreach ($contents as $key=>$content):?>
            <div class="why_image"><img src="{{$content['icon']}}" style="width: 100%"/></div>
            <?php endforeach;?>
        </div>
    </div>
    <div class='col-md-4 why_container'>
        <div style="display: flex;">
            <?php foreach ($contents as $key=>$content):?>
            <div class="why_content">{{$content['content']}}</div>
            <?php endforeach;?>
        </div>
    </div>

</div>

<script>

var rowwhy={}
rowwhy.titles = document.getElementsByClassName("why_title");
rowwhy.images = document.getElementsByClassName("why_image");
rowwhy.contents = document.getElementsByClassName("why_content");
rowwhy.select = function(select){
	for(let i in this.titles){
		this.titles[i].className = 'why_title';
		this.images[i].className = 'why_image';
		this.contents[i].className = 'why_content';
	}
	this.titles[select].className = 'why_title selected';
	this.images[select].className = 'why_image selected';
	this.contents[select].className = 'why_content selected';
}
rowwhy.select(0);



</script>
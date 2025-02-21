function toggleClass(element, className, event) {
		event.stopPropagation();
        var classes = element.className.split(" ");
        var i = classes.indexOf(className);
        if (i >= 0){
            classes.splice(i, 1);
        } else {
            classes.push(className);
        	closeAllExpandButton();
        }
        element.className = classes.join(" "); 
    
}

function closeAllExpandButton(){
	let menuGrBtns = document.getElementsByClassName("menu_group_button expand")
	let leng = menuGrBtns.length;
	for(let i = 0; i < leng; i++){
		rmClass(menuGrBtns[0], 'expand');
	}
}

function addClass(element, className) {
	
        var classes = element.className.split(" ");
        var i = classes.indexOf(className);
        if (i < 0){
            
            classes.push(className);
        	closeAllExpandButton();
        }
        element.className = classes.join(" "); 
    
}

function rmClass(element, className) {
	
   
        var classes = element.className.split(" ");
        var i = classes.indexOf(className);
        if (i >= 0) {
            classes.splice(i, 1);
        }
        element.className = classes.join(" "); 
    
}

/* menu event */
$(".menu_group_button")
.on( "mouseenter", function(event) {
	if($(".menu_button.expand").length == 0){
		closeAllExpandButton();
		addClass(this, 'expand');
	}
	
});

$(".menu_item.menu_item_parent")
.on( "mouseenter", function(event) {
	if($(".menu_button.expand").length == 0){
		closeAllExpandButton();
	}
});

$(".menu_group")
.on( "mouseleave", function(event) {
	if($(".menu_button.expand").length == 0){
		closeAllExpandButton();
	}
});

document.addEventListener('click', function(event){
	event.stopPropagation();
	let menuGrBtns = document.getElementsByClassName("menu_group_button expand")
	let leng = menuGrBtns.length;
	for(let i = 0; i < leng; i++){
		rmClass(menuGrBtns[0], 'expand');
	}
	
	if(event.target.className == "menu_cover"){
		let menuBtns = document.getElementsByClassName("menu_button expand");
		let leng = menuBtns.length;
		for(let i = 0; i < leng; i++){
			rmClass(menuBtns[0], 'expand');
		}
	}
	
})

/* menu cover */
$(document).ready(function(event){
	setTimeout(function(){ 
		$(".menu_fill").css('height', $(".menu").css('height')); 
		}, 500);
})

function goToByScroll(id) {
    // Scroll
    $('html,body').animate({
        scrollTop: $("#" + id).offset().top
    }, '500');
}



global.language='en';

global.vi = {};
global.en = {};

var langLoader = require.context('./vi/', true, /.js$/);
langLoader.keys().forEach((key)=>{
	var lang =  langLoader(key)['langData'];
	global.vi = {...global.vi, ...lang};
});

langLoader = require.context('./en/', true, /.js$/);
langLoader.keys().forEach((key)=>{
	var lang = langLoader(key)['langData']; 
	global.en = {...global.en, ...lang};
});

export const lang = function(string, variables=null){
	var translate = string;
	if(typeof(global[global.language][string]) != 'undefined'){
		translate = global[global.language][string]
	}
	if(variables){
		for(let i in variables){
			translate = translate.replace(new RegExp('{'+i+'}','g'), lang(variables[i]))
		}
	}
	return translate;
}
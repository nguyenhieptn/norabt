<?php


/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| is assigned the "api" middleware group. Enjoy building your API!
|
*/

Route::options('{any}', function(){ return ''; })->where('any', '.*');

Route::match(['post', 'get'], '/uploader/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Uploader\api\\'.ucfirst($controller).'Controller@' . $method);
});  

Route::match(['post', 'get'], '/mailer/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Mailer\api\\'.ucfirst($controller).'Controller@' . $method);
});  

Route::match(['post', 'get'], '/user/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\User\api\\'.ucfirst($controller).'Controller@' . $method);
}); 

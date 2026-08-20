<?php

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| contains the "web" middleware group. Now create something great!
|
*/

/*Admin*/

Route::match(['post'], '/captcha', function() {
    return App::call('\App\Http\Controllers\Auth\LoginController@captcha');
});

Route::get('/admin', function () {
    return view('reactjs.reactjs');
});

Route::get('/lab', function () {
    return view('reactjs.simulation');
});

Route::redirect('/', '/home', 301);
Route::redirect('/home', '/admin', 301); 


/*route for admin*/
// Font được CSS tham chiếu tương đối từ trang /admin -> /admin/fonts/...;
// phải chặn trước catch-all bên dưới kẻo bị hiểu nhầm là FontsController (500).
// File thật nằm ở /fonts hoặc /fonts/vendor/primeicons.
Route::get('/admin/fonts/{path}', function ($path) {
    foreach (['fonts/' . $path, 'fonts/vendor/primeicons/' . $path] as $candidate) {
        if (file_exists(public_path($candidate))) return redirect('/' . $candidate);
    }
    abort(404);
})->where('path', '.*');

// CSS cũng tham chiếu /fonts/<file> trong khi file thật nằm ở fonts/vendor/primeicons
Route::get('/fonts/{file}', function ($file) {
    $real = public_path('fonts/vendor/primeicons/' . $file);
    if (file_exists($real)) {
        return response()->file($real, ['Cache-Control' => 'public, max-age=86400']);
    }
    abort(404);
})->where('file', '[^/]+');

Route::match(['post', 'get'], '/admin/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Admin\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth');

/* for authen route*/
Route::get('/login', 'Auth\LoginController@view');
Route::post('/auth/setToken', 'Auth\LoginController@setToken');

Route::match(['post', 'get'], '/guest/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Auth\\'.ucfirst($controller).'Controller@' . $method);
});

Route::match(['post', 'get'], '/auth/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Auth\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth');

/* for uploader route*/
Route::match(['post', 'get'], '/uploader/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Uploader\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth');

/* for mailer route*/
Route::match(['post', 'get'], '/mailer/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Mailer\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth');

/* for mailer route*/
Route::match(['post', 'get'], '/control/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Control\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth');

/* for mailer route*/
Route::match(['post', 'get'], '/notice/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Notice\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth');

/* for analytics route*/
Route::match(['post', 'get'], '/analytics/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\Analytics\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('auth'); 

/* for page user*/
Route::match(['post', 'get'], '/user/{controller}/{method}', function ($controller, $method) {
    return App::call('\App\Http\Controllers\User\\'.ucfirst($controller).'Controller@' . $method);
})->middleware('multilang');









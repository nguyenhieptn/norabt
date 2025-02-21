<?php
use App\Helpers\View\Loader;
$id = get($id, 'css_'.rand());
$type = get($type, null);
echo Loader::asset($id, $slot, $type);
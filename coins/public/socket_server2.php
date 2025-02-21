#!/usr/local/bin/php -q
<?php
error_reporting(E_ALL);

/* Allow the script to hang around waiting for connections. */
set_time_limit(0);

/* Turn on implicit output flushing so we see what we're getting
 * as it comes in. */
ob_implicit_flush();

$address = '0.0.0.0';
$port = 10000;

if (($sock = socket_create(AF_INET, SOCK_STREAM, SOL_TCP)) === false) {
    echo "socket_create() failed: reason: " . socket_strerror(socket_last_error()) . "\n";
}

if (socket_bind($sock, $address, $port) === false) {
    echo "socket_bind() failed: reason: " . socket_strerror(socket_last_error($sock)) . "\n";
}

if (socket_listen($sock, 5) === false) {
    echo "socket_listen() failed: reason: " . socket_strerror(socket_last_error($sock)) . "\n";
}

function unmask($text) {
	$length = ord($text[1]) & 127;
	if($length == 126) {
		$masks = substr($text, 4, 4);
		$data = substr($text, 8);
	}
	elseif($length == 127) {
		$masks = substr($text, 10, 4);
		$data = substr($text, 14);
	}
	else {
		$masks = substr($text, 2, 4);
		$data = substr($text, 6);
	}
	$text = "";
	for ($i = 0; $i < strlen($data); ++$i) {
		$text .= $data[$i] ^ $masks[$i%4];
	}
	return $text;
}

do {
	echo "loop1\n";
    if (($msgsock = socket_accept($sock)) === false) {
        echo "socket_accept() failed: reason: " . socket_strerror(socket_last_error($sock)) . "\n";
        break;
    }
    /* Send instructions. */
	$request = socket_read($msgsock, 5000);
	print_r($request);
	preg_match('#Sec-WebSocket-Key: (.*)\r\n#', $request, $matches);
	$key = base64_encode(pack(
		'H*',
		sha1($matches[1] . '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
	));
	$headers = "HTTP/1.1 101 Switching Protocols\r\n";
	$headers .= "Upgrade: websocket\r\n";
	$headers .= "Connection: Upgrade\r\n";
	$headers .= "Sec-WebSocket-Version: 13\r\n";
	$headers .= "Sec-WebSocket-Accept: $key\r\n\r\n";
	socket_write($msgsock, $headers, strlen($headers));
	
	
	$msg = "\nWelcome to the PHP Test Server. \n" .
        "To quit, type 'quit'. To shut down the server type 'shutdown'.\n";
		
	$content = $msg;
    $response = chr(129) . chr(strlen($content)) . $content;
    socket_write($msgsock, $response);
    
    do {
		echo "loop2\n";
        if (false === ($buf = socket_read($msgsock, 5000))) {
            echo "socket_read() failed: reason: " . socket_strerror(socket_last_error($msgsock)) . "\n";
            break 2;
        }
		if(!$buf) break;
		$buf = unmask($buf);
		
        if (!$buf = trim($buf)) {
            continue;
        }
        if ($buf == 'quit') {
            break;
        }
        if ($buf == 'shutdown') {
            socket_close($msgsock);
            break 2;
        }
        $content = "PHP: You said " . $buf;
		$response = chr(129) . chr(strlen($content)) . $content;
        socket_write($msgsock, $response);
        echo "$content\n";
    } while (true);
    socket_close($msgsock);
} while (true);

socket_close($sock);
?>
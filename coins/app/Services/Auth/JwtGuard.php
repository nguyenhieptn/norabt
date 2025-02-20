<?php

namespace App\Services\Auth;

use App\Helpers\DB\Models;
use Illuminate\Http\Request;
use Illuminate\Contracts\Auth\Guard;
use Illuminate\Contracts\Auth\UserProvider;
use App\Helpers\Token\JWToken;
use Illuminate\Support\Facades\Cookie;
use Illuminate\Auth\AuthenticationException;
use App\Helpers\Request\Reply;

class JwtGuard implements Guard
{
    use \Illuminate\Auth\GuardHelpers;

    /**
     * The request instance.
     *
     * @var \Illuminate\Http\Request
     */
    protected $request;

    /**
     * The name of the query string item from the request containing the API token.
     *
     * @var string
     */
    protected $inputKey;


    protected $log;

    /**
     * Create a new authentication guard.
     *
     * @param  \Illuminate\Contracts\Auth\UserProvider  $provider
     * @param  \Illuminate\Http\Request  $request
     * @return void
     */
    public function __construct(UserProvider $provider, Request $request)
    {
        $this->request = $request;
        $this->provider = $provider;
        $this->inputKey = 'token';
    }

    /**
     * Get the currently authenticated user.
     *
     * @return \Illuminate\Contracts\Auth\Authenticatable|null
     */
    public function user()
    {
        // If we've already retrieved the user for the current request we can just
        // return it back immediately. We do not want to fetch the user data on
        // every call to this method because that would be tremendously slow.
        if (!is_null($this->user)) {
            return $this->user;
        }

        return null;
    }

    /**
     * Get the token for the current request.
     *
     * @return string
     */
    public function getTokenForRequest()
    {
        $token = $this->request->cookie($this->inputKey);

        if (empty($token)) {
            $token = $this->request->query($this->inputKey);
        }

        if (empty($token)) {
            $token = $this->request->input($this->inputKey);
        }

        if (empty($token)) {
            $token = $this->request->bearerToken();
        }

        if (empty($token)) {
            $token = $this->request->getPassword();
        }

        return $token;
    }

    /**
     * Validate a user's credentials.
     *
     * @param  array  $credentials
     * @return bool
     */
    public function validate(array $credentials = [])
    {
        if (empty($credentials[$this->inputKey])) {
            return false;
        }

        $credentials = [$this->storageKey => $credentials[$this->inputKey]];

        if ($this->provider->retrieveByCredentials($credentials)) {
            return true;
        }

        return false;
    }

    /**
     * Set the current request instance.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return $this
     */
    public function setRequest(Request $request)
    {
        $this->request = $request;

        return $this;
    }

    public function attempt(array $credentials = [])
    {

        $this->lastAttempted = $user = $this->provider->retrieveByCredentials($credentials);


        if ($user == null) {
            Reply::finish(false, 'Username or Email is not exited');
        }

        if ($user->{AUTHEN_ACTIVE} != AUTHEN_ACTIVE_VERIFIED) Reply::finish(false, 'Account still not actived. Register again');
        if ($user->{AUTHEN_STATUS} != AUTHEN_STATUS_APPROVE) Reply::finish(false, 'Account is blocked.');

        if ($this->hasValidCredentials($user, $credentials)) {
            $this->setUser($user);
            return true;
        } else {
            Reply::finish(false, 'Password is Wrong');
        }
        return false;
    }


    public function getTokenFromUser()
    {

        if (!isset($this->user)) return null;

        $token = JWToken::make([
            AUTHEN_ID => $this->user->{AUTHEN_ID},
            AUTHEN_EMAIL => $this->user->{AUTHEN_EMAIL},
            AUTHEN_USERNAME => $this->user->{AUTHEN_USERNAME},
            AUTHEN_GROUP => $this->user->{AUTHEN_GROUP},
            AUTHEN_PHONE => $this->user->{AUTHEN_PHONE},
            AUTHEN_IMG => $this->user->{AUTHEN_IMG},
        ]);

        if (!$token) $this->log = JWToken::getMessage();
        return $token;
    }

    public function getUserFromToken()
    {

        $payload = JWToken::payload($this->getTokenForRequest());

        if (!$payload) {
            $this->log = JWToken::getMessage();
            return false;
        }

        if (($payload->{'exp'} - time()) < config('jwt.ttl') * 60 / 2) {
            $this->refreshToken();
        }

        // Models::get('Auth/Authentication')->edit([
        //     DATA_KEY => [[[AUTHEN_ID, '=', $payload->{AUTHEN_ID}]]],
        //     DATA_EDITOR => [AUTHEN_ONLINE => time()]
        // ]);

        return new JwtGenericUser([
            AUTHEN_ID => $payload->{AUTHEN_ID},
            AUTHEN_EMAIL => $payload->{AUTHEN_EMAIL},
            AUTHEN_USERNAME => $payload->{AUTHEN_USERNAME},
            AUTHEN_GROUP => $payload->{AUTHEN_GROUP},
            AUTHEN_PHONE => $payload->{AUTHEN_PHONE},
            AUTHEN_IMG => $payload->{AUTHEN_IMG},
        ]);
    }

    public function getLog()
    {
        return $this->log;
    }

    public function refreshToken($options = null, $newPayload = null)
    {
        $newToken = JWToken::refresh($this->getTokenForRequest(), $options, $newPayload);
        Cookie::queue(Cookie::make('token', $newToken, config('jwt.ttl') * 60, '/', APP_DOMAIN));
        return;
    }

    public function check()
    {

        if (!is_null($this->user)) return true;

        if (!$token = $this->getTokenForRequest()) return false;

        if (!$user = $this->getUserFromToken()) {
            return false;
        }

        $this->setUser($user);
        return true;
    }

    public function logout()
    {
        $this->user = null;
        Cookie::queue(Cookie::make('token', null, 0, '/', APP_DOMAIN));
    }

    public function login($token)
    {
        
        Cookie::queue(Cookie::make('token', $token, config('jwt.ttl') * 60, '/', APP_DOMAIN));
    }

    protected function hasValidCredentials($user, $credentials)
    {
        return !is_null($user) && $this->provider->validateCredentials($user, $credentials);
    }

    public function authenticate()
    {
        if ($this->check()) {
            return true;
        } else {
            throw new AuthenticationException($this->log);
        }
    }
}

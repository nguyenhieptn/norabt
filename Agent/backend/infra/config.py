import os

from Agent.backend.infra.envfile import apply_env_file

# Path is derived the same way AppConfig.BASE_DIR is below (two levels up from
# this file: infra/ -> backend/ -> Agent/), so it must be computed before the
# class body runs. AGENT_ENV_FILE lets tests and deployments override it.
_DEFAULT_ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env",
)
_ENV_FILE_PATH = os.getenv("AGENT_ENV_FILE", _DEFAULT_ENV_FILE)

# Must run before AppConfig's class body reads os.getenv(...) below --
# otherwise the file would be parsed only to have nothing consume it.
_ENV_FILE_EXISTS = os.path.isfile(_ENV_FILE_PATH)
_ENV_VARS_LOADED = apply_env_file(_ENV_FILE_PATH)


class AppConfig:
    # Nguồn cấu hình: đã nạp Agent/.env (nếu có) trước khi các os.getenv() dưới
    # đây chạy. Env thật (systemd/CI/docker) luôn thắng file -- xem envfile.py.
    # ENV_FILE_LOADED tracks whether the file itself was found (not whether
    # any variable actually changed os.environ, since a real env var wins
    # over the file and can legitimately bring the applied count to 0).
    ENV_FILE_PATH: str = _ENV_FILE_PATH
    ENV_FILE_LOADED: bool = _ENV_FILE_EXISTS
    ENV_FILE_VARS_LOADED: int = _ENV_VARS_LOADED

    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # OKX Public & Cloudflare Anycast IPv4 (Khử độ trễ DNS Tailscale)
    OKX_CLOUDFLARE_IPV4: str = os.getenv("OKX_IPV4", "104.18.43.174")
    OKX_REST_URL: str = "https://www.okx.com"
    OKX_WS_BUSINESS_URL: str = "wss://ws.okx.com:8443/ws/v5/business"

    # Quant buffer parameters
    BUFFER_SIZE: int = 150
    TIMEFRAME: str = "candle1m"
    KELTNER_EMA_PERIOD: int = 20
    KELTNER_ATR_PERIOD: int = 14
    KELTNER_MULTIPLIER: float = 1.5
    SUSTAINED_RANGE_PERIOD: int = 20
    SUSTAINED_RANGE_THRESHOLD: float = 1.15
    TOP_CEX_LIMIT: int = min(max(int(os.getenv("TOP_CEX_LIMIT", "30")), 1), 30)
    TOP_DEX_LIMIT: int = min(max(int(os.getenv("TOP_DEX_LIMIT", "20")), 1), 20)
    OKX_HTTP_TIMEOUT_SECONDS: float = float(os.getenv("OKX_HTTP_TIMEOUT_SECONDS", "10"))
    OKX_HTTP_MAX_RETRIES: int = max(int(os.getenv("OKX_HTTP_MAX_RETRIES", "2")), 0)
    # This host's IPv6 route to OKX/Cloudflare is blackholed (SYN sent, no reply,
    # no ICMP unreachable), so urllib burns the full connect timeout on each
    # dead IPv6 address before falling back to IPv4 -- turning every request
    # into a ~50s stall instead of an instant ~100ms IPv4 connect (measured
    # directly against each address family). Defaults to on; only needs
    # disabling on a host where IPv6 to OKX actually works.
    OKX_FORCE_IPV4: bool = os.getenv("OKX_FORCE_IPV4", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )

    # Private API credentials. Left blank by default so the crawler keeps working
    # off public endpoints alone -- nothing here is ever hardcoded, only read from
    # the environment (see Agent/.env.example).
    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "")
    OKX_API_SECRET: str = os.getenv("OKX_API_SECRET", "")
    OKX_API_PASSPHRASE: str = os.getenv("OKX_API_PASSPHRASE", "")
    # Demo trading is the safe default: a live key must be opted into explicitly
    # by setting OKX_SIMULATED=false, never the other way around.
    OKX_SIMULATED: bool = os.getenv("OKX_SIMULATED", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )

    # Data directories
    BASE_DIR: str = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    LOG_DIR: str = os.path.join(BASE_DIR, "log")


config = AppConfig()

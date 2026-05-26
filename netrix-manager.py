#!/usr/bin/env python3

import os, sys, time, subprocess, shutil, socket, signal, urllib.request, platform, json, stat, hashlib, ipaddress, re, datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML library not found. Install with: pip install pyyaml")
    sys.exit(1)

# ========== Version ==========
VERSION = "3.0.0"

ROOT_DIR = Path("/root")
NETRIX_CONFIG_DIR = ROOT_DIR / "netrix"
NETRIX_CONFIG_DIR_FALLBACK = ROOT_DIR / "netrix-config"
NETRIX_BINARY = "/usr/local/bin/netrix"
NETRIX_SYSCTL_FILE = Path("/etc/sysctl.d/99-netrix-performance.conf")
NETRIX_LIMITS_FILE = Path("/etc/security/limits.d/99-netrix.conf")
NETRIX_PROFILE_LIMITS_FILE = Path("/etc/profile.d/netrix-limits.sh")

def _read_proc_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""

def resolve_netrix_config_dir() -> Path:
    """Return a writable config directory, even if /root/netrix is a file."""
    preferred = NETRIX_CONFIG_DIR
    try:
        if preferred.exists() and not preferred.is_dir():
            fallback = NETRIX_CONFIG_DIR_FALLBACK
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = NETRIX_CONFIG_DIR_FALLBACK
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

NETRIX_CONFIG_DIR = resolve_netrix_config_dir()
NETRIX_RELEASE_URLS = {
    "amd64": f"https://github.com/Karrari-Dev/Netrix-/releases/download/v{VERSION}/netrix-amd64.tar.gz",
    "arm64": f"https://github.com/Karrari-Dev/Netrix-/releases/download/v{VERSION}/netrix-arm64.tar.gz"
}

MAX_STEALTH_PADDING_BYTES = 255

DEFAULT_HEARTBEAT = 20
DEFAULT_BUFFER_POOL_SIZE = 65536
DEFAULT_LARGE_BUFFER_POOL_SIZE = 65795
DEFAULT_UDP_FRAME_POOL_SIZE = 65795
DEFAULT_UDP_SLICE_SIZE = 1500


KCP_PROFILES = {
    "balanced":      {"nodelay": 0, "interval": 20, "resend": 2, "nc": 0, "sndwnd": 512,  "rcvwnd": 512,  "mtu": 1350, "data_shard": 10, "parity_shard": 3},
    "aggressive":    {"nodelay": 0, "interval": 10, "resend": 2, "nc": 1, "sndwnd": 2048, "rcvwnd": 2048, "mtu": 1400, "data_shard": 10, "parity_shard": 4},
    "latency":       {"nodelay": 1, "interval": 5,  "resend": 1, "nc": 1, "sndwnd": 256,  "rcvwnd": 256,  "mtu": 1200, "data_shard": 10, "parity_shard": 5},
    "cpu-efficient": {"nodelay": 0, "interval": 50, "resend": 3, "nc": 0, "sndwnd": 128,  "rcvwnd": 128,  "mtu": 1400, "data_shard": 10, "parity_shard": 2},
}

RAWSOCKET_SND_WND = 2048
RAWSOCKET_RCV_WND = 2048
RAWSOCKET_DATA_SHARD = 10
RAWSOCKET_PARITY_SHARD = 2
RAWSOCKET_SOCK_BUF = 4 * 1024 * 1024
RAWSOCKET_PROFILES = {
    "balanced": {},
    "aggressive": {"snd_wnd": 8192, "rcv_wnd": 8192, "sock_buf": 32 * 1024 * 1024},
    "latency": {"mtu": 1200, "snd_wnd": 2048, "rcv_wnd": 2048, "sock_buf": 8 * 1024 * 1024},
    "cpu-efficient": {"mtu": 1280, "snd_wnd": 2048, "rcv_wnd": 2048, "sock_buf": 8 * 1024 * 1024},
}

FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"

BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"
BG_BRIGHT_RED = "\033[101m"
BG_BRIGHT_GREEN = "\033[102m"
BG_BRIGHT_YELLOW = "\033[103m"
BG_BRIGHT_BLUE = "\033[104m"
BG_BRIGHT_MAGENTA = "\033[105m"
BG_BRIGHT_CYAN = "\033[106m"
BG_BRIGHT_WHITE = "\033[107m"

BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
STRIKETHROUGH = "\033[9m"
RESET = "\033[0m"

THEME_PRIMARY = FG_CYAN
THEME_SECONDARY = FG_BLUE
THEME_SUCCESS = FG_GREEN
THEME_WARNING = FG_YELLOW
THEME_ERROR = FG_RED
THEME_INFO = FG_MAGENTA
THEME_BG = THEME_BG_LIGHT = BG_BLACK

GITHUB_REPO = "github.com/Karrari-Dev/Netrix-"
PUBLIC_IP_API = "api.ipify.org"
SUPPORT_HANDLE = "@g0dline"

def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)

def _term_width(default: int = 100) -> int:
    try:
        width = shutil.get_terminal_size((default, 24)).columns
    except Exception:
        width = default
    return max(78, min(width, 118))

def _visible_len(text: str) -> int:
    return len(_strip_ansi(text))

def _center_ansi(text: str, width: int) -> str:
    pad = max(0, width - _visible_len(text))
    left = pad // 2
    right = pad - left
    return (" " * left) + text + (" " * right)

def _brand_box(title: str = "", subtitle: str = "", lines=None, accent: str = FG_CYAN):
    width = _term_width()
    inner = width - 4
    top = f"{BOLD}{accent}╔{'═' * (width - 2)}╗{RESET}"
    bottom = f"{BOLD}{accent}╚{'═' * (width - 2)}╝{RESET}"
    logo_lines = [
        f"{BOLD}{FG_CYAN}███╗   ██╗███████╗████████╗{FG_MAGENTA}██████╗ ██╗██╗  ██╗{RESET}",
        f"{BOLD}{FG_CYAN}████╗  ██║██╔════╝╚══██╔══╝{FG_MAGENTA}██╔══██╗██║╚██╗██╔╝{RESET}",
        f"{BOLD}{FG_CYAN}██╔██╗ ██║█████╗     ██║   {FG_MAGENTA}██████╔╝██║ ╚███╔╝ {RESET}",
        f"{BOLD}{FG_CYAN}██║╚██╗██║██╔══╝     ██║   {FG_MAGENTA}██╔══██╗██║ ██╔██╗ {RESET}",
        f"{BOLD}{FG_CYAN}██║ ╚████║███████╗   ██║   {FG_MAGENTA}██║  ██║██║██╔╝ ██╗{RESET}",
        f"{BOLD}{FG_CYAN}╚═╝  ╚═══╝╚══════╝   ╚═╝   {FG_MAGENTA}╚═╝  ╚═╝╚═╝╚═╝  ╚═╝{RESET}",
    ]
    print(top)
    for line in logo_lines:
        print(f"{BOLD}{accent}║ {RESET}{_center_ansi(line, inner)}{BOLD}{accent} ║{RESET}")
    if title:
        print(f"{BOLD}{accent}║ {RESET}{_center_ansi(f'{BOLD}{FG_WHITE}{title}{RESET}', inner)}{BOLD}{accent} ║{RESET}")
    if lines:
        print(f"{BOLD}{accent}╠{'═' * (width - 2)}╣{RESET}")
        for line in lines:
            visible = _visible_len(line)
            if visible > inner:
                raw = _strip_ansi(line)
                line = raw[:inner]
                visible = len(line)
            print(f"{BOLD}{accent}║ {RESET}{line}{' ' * max(0, inner - visible)}{BOLD}{accent} ║{RESET}")
    print(bottom)

def _menu_line(idx: str, label: str, desc: str = "", accent: str = FG_CYAN):
    badge = f"{BOLD}{accent}[{idx}]{RESET}"
    print(f"  {badge}  {BOLD}{FG_WHITE}{label}{RESET}")

def _repo_from_release() -> str:
    try:
        sample = next(iter(NETRIX_RELEASE_URLS.values()))
        m = re.search(r"github\.com/([^/]+/[^/]+)/releases", sample)
        if m:
            return f"github.com/{m.group(1)}"
    except Exception:
        pass
    return GITHUB_REPO

def _brand_meta(core_installed: bool = None):
    local_ip = safe_get_server_ip(prefer_public=False) or "Unavailable"
    core_status = f"{FG_GREEN}Installed{RESET}" if core_installed else f"{FG_RED}Not installed{RESET}"
    return [
        f"{FG_WHITE}Version:{RESET} {FG_GREEN}v{VERSION}{RESET}    {FG_WHITE}GitHub:{RESET} {FG_CYAN}{_repo_from_release()}{RESET}",
        f"{FG_WHITE}Detected IP:{RESET} {FG_GREEN}{local_ip}{RESET}    {FG_WHITE}Core:{RESET} {core_status}",
        f"{FG_WHITE}Binary:{RESET} {FG_CYAN}{NETRIX_BINARY}{RESET}",
    ]

def _styled_prompt_label(label: str) -> str:
    parts = re.split(r"(\[[^\]]+\])", label)
    styled = []
    for part in parts:
        if not part:
            continue
        if part.startswith("[") and part.endswith("]"):
            styled.append(f"{FG_YELLOW}{part}{RESET}{BOLD}{FG_WHITE}")
        else:
            styled.append(part)
    return f"{BOLD}{FG_WHITE}" + "".join(styled) + RESET

def _input_prompt(label: str = "Select an option") -> str:
    return f"  {BOLD}{FG_CYAN}➜ {_styled_prompt_label(label)}: "

def _plain_prompt_label(prompt: str) -> str:
    label = _strip_ansi(prompt).strip()
    while label.endswith(':'):
        label = label[:-1].rstrip()
    return label

def _section(title: str, subtitle: str = ""):
    print()
    print(f"  {BOLD}{FG_CYAN}{title}{RESET}")

def _wizard_intro(title: str, subtitle: str):
    clear()
    _brand_box(title, subtitle, _brand_meta(os.path.exists(NETRIX_BINARY)), accent=FG_CYAN)
    print()

# ========== Utils ==========

class UserCancelled(Exception):
    """Exception raised when user cancels an operation (Ctrl+C)"""
    pass

def exit_script():
    """Exit the script completely when Ctrl+C is pressed"""
    print(f"\n\n  {FG_YELLOW}Exiting...{RESET}")
    sys.exit(0)

def c_ok(msg: str):
    try: print(f"{FG_GREEN}✅ {msg}{RESET}")
    except Exception: print(msg)

def c_err(msg: str):
    try: print(f"{FG_RED}❌ {msg}{RESET}")
    except Exception: print(msg)

def c_warn(msg: str):
    try: print(f"{FG_YELLOW}⚠️  {msg}{RESET}")
    except Exception: print(msg)

def require_root():
    if os.geteuid() != 0:
        print("This script must be run as root (sudo).")
        sys.exit(1)

def clear():
    os.system("clear" if shutil.which("clear") else "printf '\\033c'")

def pause(msg="\n  Press Enter to continue..."):
    try: input(msg)
    except KeyboardInterrupt: exit_script()

def which(cmd):
    p = shutil.which(cmd)
    return p if p else None

def format_bytes(n: int) -> str:
    """تبدیل بایت به فرمت خوانا (مثلاً 1.2 GB)"""
    if n < 0:
        n = 0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"

def is_port_in_use(port: int, protocol: str = "tcp", host: str = "0.0.0.0") -> bool:
    """Check whether a port is already bound."""
    sock_type = socket.SOCK_STREAM if protocol.lower() == "tcp" else socket.SOCK_DGRAM
    family = socket.AF_INET6 if ':' in host else socket.AF_INET
    with socket.socket(family, sock_type) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError:
            return True
    return False


def is_port_busy_any(port: int, protocols=("tcp", "udp")) -> bool:
    for proto in protocols:
        for host in ("0.0.0.0", "::"):
            if host == "::":
                try:
                    if not is_ipv6_available():
                        continue
                except Exception:
                    continue
            try:
                if is_port_in_use(port, proto, host):
                    return True
            except Exception:
                pass
    return False


def ask_free_port(label: str = "Tunnel Port", default: int | None = None, protocols=("tcp", "udp")) -> int:
    while True:
        port = ask_int(f"  {BOLD}{label}:{RESET}", min_=1, max_=65535, default=default)
        if is_port_busy_any(port, protocols=protocols):
            c_err(f"Port {port} is already in use. Choose another port.")
            continue
        return port


def is_ipv6_available() -> bool:
    """بررسی فعال بودن IPv6 روی سیستم"""
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('::', 0))
            sock.close()
            return True
        except OSError:
            sock.close()
            return False
    except (socket.error, OSError):
        return False

def get_server_ip(timeout: float = 1.5, prefer_public: bool = False) -> Optional[str]:
    """دریافت IP سرور (IPv4) - پیش‌فرض: محلی (بدون اینترنت)"""
    
    def is_loopback(ip: str) -> bool:
        """چک کردن آیا IP یک loopback هست (127.x.x.x)"""
        return ip.startswith("127.") or ip == "localhost"
    
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.' not in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1].split('/')[0]
                        if ip and '.' in ip and not is_loopback(ip):
                            return ip
    except KeyboardInterrupt:
        raise
    except Exception:
        pass
    
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and not is_loopback(local_ip):
            return local_ip
    except Exception:
        pass

    if prefer_public:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=timeout) as response:
                public_ip = response.read().decode().strip()
                if public_ip and '.' in public_ip:
                    return public_ip
        except KeyboardInterrupt:
            raise
        except Exception:
            pass

    return None

def safe_get_server_ip(timeout: float = 1.5, prefer_public: bool = False) -> Optional[str]:
    """Safe wrapper to avoid blocking or crashing on network issues."""
    try:
        return get_server_ip(timeout=timeout, prefer_public=prefer_public)
    except KeyboardInterrupt:
        return None

def ask_int(prompt, min_=1, max_=65535, default=None):
    label = _plain_prompt_label(prompt)
    while True:
        try:
            suffix = f" [{default}]" if default is not None else ""
            raw = input(_input_prompt(f"{label}{suffix}")).strip()
        except KeyboardInterrupt:
            exit_script()
        except (UnicodeDecodeError, UnicodeEncodeError):
            print(f"  {FG_RED}⚠️  Invalid input encoding. Please use English characters.{RESET}")
            continue
        if raw == "" and default is not None:
            return default
        if not raw.isdigit():
            print(f"  {FG_RED}⚠️  Please enter a valid integer.{RESET}")
            continue
        val = int(raw)
        if not (min_ <= val <= max_):
            print(f"  {FG_RED}⚠️  Valid range: {FG_YELLOW}{min_}{RESET} to {FG_YELLOW}{max_}{RESET}")
            continue
        return val

def ask_nonempty(prompt, default=None):
    label = _plain_prompt_label(prompt)
    while True:
        try:
            suffix = f" [{default}]" if default else ""
            raw = input(_input_prompt(f"{label}{suffix}")).strip()
        except KeyboardInterrupt:
            exit_script()
        except (UnicodeDecodeError, UnicodeEncodeError):
            print(f"  {FG_RED}⚠️  Invalid input encoding. Please use English/ASCII characters.{RESET}")
            continue
        if raw == "" and default is not None:
            return default
        if raw:
            return raw
        print(f"  {FG_RED}⚠️  This field cannot be empty.{RESET}")

def ask_edge_ip_optional(context="CDN"):
    try:
        raw = input(_input_prompt("Edge IP [optional]")).strip()
    except KeyboardInterrupt:
        exit_script()
    return raw.strip() if raw else ""

def ask_yesno(prompt, default=True):
    default_str = "Y/n" if default else "y/N"
    label = _plain_prompt_label(prompt)
    while True:
        try:
            raw = input(_input_prompt(f"{label} [{default_str}]")).strip().lower()
        except KeyboardInterrupt:
            exit_script()
        except (UnicodeDecodeError, UnicodeEncodeError):
            print(f"  {FG_RED}⚠️  Invalid input encoding. Please use English characters.{RESET}")
            continue
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print(f"  {FG_RED}⚠️  Please enter {FG_GREEN}y/yes{RESET} or {FG_RED}n/no{RESET}")

def parse_ports(ports_str: str) -> List[int]:
    """Parse ports from string (comma-separated or range)
    
    Examples:
        "2066,9988,6665" -> [2066, 9988, 6665]
        "2066-2070" -> [2066, 2067, 2068, 2069, 2070]
    """
    ports = []
    parts = [p.strip() for p in ports_str.split(',')]
    
    for part in parts:
        if '-' in part:
            try:
                start, end = part.split('-', 1)
                start_port = int(start.strip())
                end_port = int(end.strip())
                if start_port < 1 or start_port > 65535 or end_port < 1 or end_port > 65535:
                    raise ValueError("Port out of range")
                if start_port > end_port:
                    raise ValueError("Start port must be <= end port")
                ports.extend(range(start_port, end_port + 1))
            except ValueError as e:
                raise ValueError(f"Invalid port range '{part}': {e}")
        else:
            try:
                port = int(part.strip())
                if port < 1 or port > 65535:
                    raise ValueError("Port out of range")
                ports.append(port)
            except ValueError as e:
                raise ValueError(f"Invalid port '{part}': {e}")
    
    return sorted(list(set(ports)))

def parse_advanced_ports(ports_str: str, protocol: str = "tcp") -> List[Dict[str, str]]:
    """
    Parse port mapping string into Netrix map format
    
    Supports:
    - Single port: 500
    - Port range: 500-567
    - Multiple ports: 500,555,666
    - Bind to specific IP: 12.12.12.12:666
    - Redirect to different port: 4000=5000
    - Range redirect to port: 443-600:5201
    - Range redirect to IP:port: 443-600=1.1.1.1:5201
    - Full specification: 127.0.0.2:443=1.1.1.1:5201
    """
    maps = []
    parts = [p.strip() for p in ports_str.split(',')]
    
    for part in parts:
        if not part:
            continue
            
        bind_part = part
        target_part = None
        
        if '=' in part:
            bind_part, target_part = part.split('=', 1)
            bind_part = bind_part.strip()
            target_part = target_part.strip()
        elif ':' in part:
            last_colon_idx = part.rfind(':')
            after_colon = part[last_colon_idx + 1:].strip()
            
            try:
                test_port = int(after_colon)
                if 1 <= test_port <= 65535:
                    before_colon = part[:last_colon_idx].strip()
                    
                    if before_colon.replace('-', '').replace('.', '').isdigit() and '.' not in before_colon:
                        bind_part = before_colon
                        target_part = after_colon
                    elif not any(before_colon.startswith(prefix) for prefix in ['127.', '192.', '10.', '172.', '0.0.0.0', '::', '[::']):
                        if '-' in before_colon or before_colon.isdigit():
                            bind_part = before_colon
                            target_part = after_colon
            except ValueError:
                pass
        
        bind_ip = "0.0.0.0"
        bind_port_start = None
        bind_port_end = None
        
        if ':' in bind_part:
            bind_ip_part, bind_port_part = bind_part.rsplit(':', 1)
            bind_ip = bind_ip_part.strip()
            bind_port_str = bind_port_part.strip()
            
            if '-' in bind_port_str:
                start_str, end_str = bind_port_str.split('-', 1)
                bind_port_start = int(start_str.strip())
                bind_port_end = int(end_str.strip())
            else:
                bind_port_start = int(bind_port_str)
                bind_port_end = bind_port_start
        else:
            if '-' in bind_part:
                start_str, end_str = bind_part.split('-', 1)
                bind_port_start = int(start_str.strip())
                bind_port_end = int(end_str.strip())
            else:
                bind_port_start = int(bind_part)
                bind_port_end = bind_port_start
        
        if bind_port_start < 1 or bind_port_start > 65535 or bind_port_end < 1 or bind_port_end > 65535:
            raise ValueError(f"Port out of range: {bind_part}")
        if bind_port_start > bind_port_end:
            raise ValueError(f"Start port must be <= end port: {bind_part}")
        
        target_ip = "127.0.0.1"
        target_port = None
        
        if target_part:
            if ':' in target_part:
                target_ip, target_port_str = target_part.rsplit(':', 1)
                target_ip = target_ip.strip()
                target_port = int(target_port_str.strip())
            else:
                target_port = int(target_part.strip())
        else:
            target_port = bind_port_start
        
        if target_port < 1 or target_port > 65535:
            raise ValueError(f"Target port out of range: {target_part or bind_port_start}")
        
        for port in range(bind_port_start, bind_port_end + 1):
            if bind_port_start != bind_port_end and target_part and ':' not in target_part:
                final_target_port = target_port
            else:
                final_target_port = target_port if bind_port_start == bind_port_end else port
            
            maps.append({
                "type": protocol,
                "bind": f"{bind_ip}:{port}",
                "target": f"{target_ip}:{final_target_port}"
            })
    
    return maps

def compact_maps(maps: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Compact maps by merging consecutive ports with same IP and target
    Example: [500,501,502] -> [500-502]
    """
    if not maps:
        return []
    
    grouped = {}
    for m in maps:
        key = (m['type'], m['bind'].split(':')[0], m['target'])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(m)
    
    compacted = []
    for key, group in grouped.items():
        protocol, bind_ip, target = key
        
        group.sort(key=lambda x: int(x['bind'].split(':')[1]))
        
        i = 0
        while i < len(group):
            start_port = int(group[i]['bind'].split(':')[1])
            end_port = start_port
            
            j = i + 1
            while j < len(group):
                current_port = int(group[j]['bind'].split(':')[1])
                expected_port = int(group[j-1]['bind'].split(':')[1]) + 1
                if current_port == expected_port:
                    end_port = current_port
                    j += 1
                else:
                    break
            
            if start_port == end_port:
                bind = f"{bind_ip}:{start_port}"
            else:
                bind = f"{bind_ip}:{start_port}-{end_port}"
            
            compacted.append({
                "type": protocol,
                "bind": bind,
                "target": target
            })
            
            i = j
    
    return compacted

def configure_encryption() -> dict:
    config = {}
    print(f"\n  {BOLD}{FG_CYAN}Encryption{RESET}")
    encryption_enabled = ask_yesno(f"  {BOLD}Enable encryption{RESET}", default=True)
    config["enabled"] = encryption_enabled
    if encryption_enabled:
        print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}ChaCha20-Poly1305{RESET}")
        print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}AES-256-GCM{RESET}")
        algo_choice = ask_int(f"  {BOLD}Algorithm{RESET}", min_=1, max_=2, default=1)
        config["algorithm"] = "chacha" if algo_choice == 1 else "aes-gcm"
        config["key"] = ask_nonempty(f"  {BOLD}Encryption key{RESET}")
    else:
        config["algorithm"] = "chacha"
        config["key"] = ""
    return config

def configure_stealth() -> dict:
    config = {}
    print(f"\n  {BOLD}{FG_CYAN}Stealth{RESET}")
    padding_enabled = ask_yesno(f"  {BOLD}Random padding{RESET}", default=False)
    config["padding_enabled"] = padding_enabled
    if padding_enabled:
        padding_min = ask_int(f"  {BOLD}Padding min{RESET}", min_=0, max_=255, default=0)
        padding_max = ask_int(f"  {BOLD}Padding max{RESET}", min_=1, max_=255, default=128)
        if padding_min > padding_max:
            padding_min = padding_max
        config["padding_min"] = padding_min
        config["padding_max"] = padding_max
    else:
        config["padding_min"] = 0
        config["padding_max"] = 0
    jitter_enabled = ask_yesno(f"  {BOLD}Timing jitter{RESET}", default=False)
    config["jitter_enabled"] = jitter_enabled
    if jitter_enabled:
        jitter_min = ask_int(f"  {BOLD}Jitter min{RESET}", min_=1, max_=100, default=5)
        jitter_max = ask_int(f"  {BOLD}Jitter max{RESET}", min_=1, max_=200, default=20)
        if jitter_min > jitter_max:
            jitter_min = jitter_max
        config["jitter_min_ms"] = jitter_min
        config["jitter_max_ms"] = jitter_max
    else:
        config["jitter_min_ms"] = 5
        config["jitter_max_ms"] = 20
    return config

def configure_anti_dpi() -> int:
    print(f"\n  {BOLD}{FG_CYAN}Anti-DPI Delay{RESET}")
    if ask_yesno(f"  {BOLD}Enable anti-DPI delay{RESET}", default=False):
        return ask_int(f"  {BOLD}Delay ms{RESET}", min_=50, max_=500, default=150)
    return 0

def configure_buffer_pools() -> dict:
    config = {}
    _section("BUFFER POOLS")
    config["buffer_pool_size"] = ask_int(f"  {BOLD}Buffer Pool Size:{RESET}", min_=1, default=DEFAULT_BUFFER_POOL_SIZE)
    config["large_buffer_pool_size"] = ask_int(f"  {BOLD}Large Buffer Pool Size:{RESET}", min_=1, default=DEFAULT_LARGE_BUFFER_POOL_SIZE)
    config["udp_frame_pool_size"] = ask_int(f"  {BOLD}UDP Frame Pool Size:{RESET}", min_=1, default=DEFAULT_UDP_FRAME_POOL_SIZE)
    config["udp_data_slice_size"] = ask_int(f"  {BOLD}UDP Slice Size:{RESET}", min_=1, default=DEFAULT_UDP_SLICE_SIZE)
    c_ok("Buffer pools saved")
    return config


def configure_compression() -> dict:
    config = {}
    _section("COMPRESSION")
    compression_enabled = ask_yesno(f"  {BOLD}Enable compression{RESET}", default=True)
    config["enabled"] = compression_enabled
    if compression_enabled:
        print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}LZ4{RESET}")
        print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}Zstd{RESET}")
        print(f"  {FG_CYAN}[3]{RESET} {FG_WHITE}Snappy{RESET}")
        algo_choice = ask_int(f"  {BOLD}Algorithm{RESET}", min_=1, max_=3, default=1)
        algo_map = {1: "lz4", 2: "zstd", 3: "snappy"}
        config["algorithm"] = algo_map[algo_choice]
        config["level"] = ask_int(f"  {BOLD}Level{RESET}", min_=1, max_=19, default=3) if algo_choice == 2 else 0
        config["min_size"] = ask_int(f"  {BOLD}Min Size{RESET}", min_=0, max_=65536, default=1024)
        config["max_size"] = ask_int(f"  {BOLD}Max Size{RESET}", min_=1024, max_=131072, default=65536)
    else:
        config["algorithm"] = "none"
        config["level"] = 0
        config["min_size"] = 0
        config["max_size"] = 0
    return config


def detect_default_interface() -> str:
    """Detect default outbound interface for L3 transports."""
    if platform.system() != "Linux":
        return "eth0"
    try:
        result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            for i, p in enumerate(parts):
                if p == "dev" and i + 1 < len(parts):
                    return parts[i + 1].strip()
    except Exception:
        pass
    return "eth0"

def ask_transport(include_l3: bool = True, title: str = "TRANSPORT") -> str:
    _section(title)
    options = [
        (1, "tcpmux", ""),
        (2, "tlsmux", ""),
        (3, "realitymux", ""),
        (4, "kcpmux", ""),
        (5, "wsmux", ""),
        (6, "wssmux", ""),
        (7, "rawsocket", ""),
    ]
    if include_l3:
        options.append((8, "l3", ""))
    transports = {}
    for idx, key, desc in options:
        if key == "l3":
            accent = FG_MAGENTA
        elif key == "rawsocket":
            accent = FG_YELLOW
        else:
            accent = FG_CYAN
        _menu_line(str(idx), key, desc, accent=accent)
        transports[idx] = key
    choice = ask_int(f"  {BOLD}Transport{RESET}", min_=1, max_=max(transports), default=1)
    return transports[choice]

def ask_connection_mode_for_transport(transport: str, server_side: bool) -> bool:
    if transport == "l3":
        return False
    _section("MODE")
    _menu_line("1", "Reverse", accent=FG_GREEN)
    _menu_line("2", "Direct", accent=FG_YELLOW)
    connection_mode = ask_int(f"  {BOLD}Connection mode{RESET}", min_=1, max_=2, default=1)
    return connection_mode == 2

L3_KERNEL_DEFAULT_CARRIER = "raw"
L3_KERNEL_DEFAULT_PROFILE = "balanced"
L3_KERNEL_DEFAULT_HEARTBEAT_INTERVAL = 5
L3_KERNEL_DEFAULT_HEARTBEAT_TIMEOUT = 30
L3_KERNEL_DEFAULT_CHANNEL_SIZE = 0
L3_KERNEL_DEFAULT_BATCH_SIZE = 0
L3_KERNEL_DEFAULT_LISTEN_PORT = 40001
L3_KERNEL_DEFAULT_DST_PORT = 40001
L3_KERNEL_DEFAULT_ICMP_TYPE = 8
L3_KERNEL_DEFAULT_ICMP_CODE = 0
L3_KERNEL_DEFAULT_ENABLE_ENCRYPTION = True
L3_KERNEL_DEFAULT_ALGORITHM = "aes-256-gcm"
L3_KERNEL_DEFAULT_KDF_ITERATIONS = 100000
L3_KERNEL_DEFAULT_PCAP_PROMISC = True

def configure_l3_security(label: str = "L3") -> dict:
    print(f"\n  {BOLD}{FG_CYAN}{label} Security:{RESET}")
    enable_encryption = ask_yesno(f"  {BOLD}Enable Packet Encryption?{RESET}", default=True)
    algorithm = "aes-256-gcm"
    psk = ""
    kdf_iterations = 100000
    if enable_encryption:
        print(f"\n  {BOLD}Packet Encryption Algorithms:{RESET}")
        print(f"  {FG_CYAN}1){RESET} {FG_WHITE}aes-256-gcm{RESET} {FG_YELLOW}[RECOMMENDED]{RESET}")
        print(f"  {FG_CYAN}2){RESET} aes-128-gcm")
        print(f"  {FG_CYAN}3){RESET} chacha20-poly1305")
        algo_choice = ask_int(f"  {BOLD}Select algorithm:{RESET}", min_=1, max_=3, default=1)
        algorithm = {1: "aes-256-gcm", 2: "aes-128-gcm", 3: "chacha20-poly1305"}[algo_choice]
        psk = ask_nonempty(f"  {BOLD}Packet Encryption PSK:{RESET}")
        kdf_iterations = ask_int(f"  {BOLD}KDF Iterations:{RESET} {FG_WHITE}(default: 100000){RESET}", min_=1, max_=5000000, default=100000)
    return {
        "enable_encryption": enable_encryption,
        "algorithm": algorithm,
        "psk": psk,
        "kdf_iterations": kdf_iterations,
    }

def configure_l3_tun(role: str, label: str = "L3") -> dict:
    print(f"\n  {BOLD}{FG_CYAN}{label} TUN Configuration:{RESET}")
    default_name = "netrix"
    default_local = "10.10.0.1/24" if role == "server" else "10.10.0.2/24"
    default_remote = "10.10.0.2/24" if role == "server" else "10.10.0.1/24"
    tun_name = ask_nonempty(f"  {BOLD}Interface Name:{RESET}", default=default_name)
    tun_local = ask_nonempty(f"  {BOLD}Local TUN CIDR:{RESET}", default=default_local)
    tun_remote = ask_nonempty(f"  {BOLD}Remote TUN CIDR:{RESET}", default=default_remote)
    tun_mtu = ask_int(f"  {BOLD}MTU:{RESET}", min_=576, max_=9000, default=1320)
    tun_streams = ask_int(f"  {BOLD}TUN Streams:{RESET} {FG_WHITE}(1 = lowest jitter; 2-8 for parallel; max L3: 64){RESET}", min_=1, max_=64, default=1)
    health_port = ask_free_port("Health Port", default=1234, protocols=("tcp",))
    return {
        "enabled": True,
        "name": tun_name,
        "local": tun_local,
        "remote": tun_remote,
        "mtu": tun_mtu,
        "streams": tun_streams,
        "health_port": health_port,
    }


def _maps_to_port_strings(maps: List[Dict[str, str]]) -> List[str]:
    out = []
    for m in compact_maps(maps):
        bind = m.get("bind", "")
        target = m.get("target", "")
        if not bind or not target:
            continue
        bind_ip, _, bind_port = bind.rpartition(':')
        target_ip, _, target_port = target.rpartition(':')
        bind_ip = bind_ip or "0.0.0.0"
        target_ip = target_ip or "127.0.0.1"
        if bind_ip == "0.0.0.0" and target_ip == "127.0.0.1" and bind_port == target_port:
            out.append(bind_port)
        elif bind_ip == "0.0.0.0" and target_ip == "127.0.0.1" and bind_port != target_port:
            out.append(f"{bind_port}={target_port}")
        elif bind_ip == "0.0.0.0":
            out.append(f"{bind_port}={target}")
        else:
            out.append(f"{bind}={target}")
    return out


def configure_l3_port_mappings(label: str = "L3") -> tuple[List[str], List[str]]:
    print(f"\n  {BOLD}{FG_CYAN}{label} Port Forwarding (Iran / Server Side){RESET}")
    print(f"  {FG_WHITE}These listeners run on Iran and forward through the {label} tunnel.{RESET}")
    print(f"  {FG_WHITE}Default target IP in {label.lower()} mode is the remote TUN peer IP.{RESET}")
    print(f"\n  {BOLD}{FG_CYAN}Supported Formats:{RESET}")
    print(f"  {FG_RED}Single Port:{RESET} {FG_WHITE}500{RESET}")
    print(f"  {FG_RED}Port Range:{RESET} {FG_WHITE}500-567{RESET}")
    print(f"  {FG_RED}Multiple Ports:{RESET} {FG_WHITE}500,555,666{RESET}")
    print(f"  {FG_RED}Bind to IP:Port:{RESET} {FG_WHITE}192.168.1.1:666{RESET}")
    print(f"  {FG_RED}Redirect Port:{RESET} {FG_WHITE}4000=5000{RESET}")
    print(f"  {FG_RED}Redirect to IP:Port:{RESET} {FG_WHITE}443=10.10.0.2:8443{RESET}")
    print(f"  {FG_RED}Range Redirect to Port:{RESET} {FG_WHITE}443-600:5201{RESET}")
    print(f"  {FG_RED}Range Redirect to IP:Port:{RESET} {FG_WHITE}443-600=10.10.0.2:5201{RESET}")
    print(f"  {FG_RED}Full Specification:{RESET} {FG_WHITE}127.0.0.2:443=10.10.0.2:5201{RESET}")

    tcp_ports: List[str] = []
    udp_ports: List[str] = []

    try:
        tcp_input = input(_input_prompt("TCP Ports [empty=skip]")).strip()
    except KeyboardInterrupt:
        exit_script()
    if tcp_input:
        try:
            tcp_maps = parse_advanced_ports(tcp_input, "tcp")
            tcp_ports = _maps_to_port_strings(tcp_maps)
            c_ok(f"  ✅ Added {len(tcp_maps)} TCP {label} mapping(s)")
        except ValueError as e:
            c_err(f"  ⚠️  Invalid TCP mapping: {e}")

    try:
        udp_input = input(_input_prompt("UDP Ports [empty=skip]")).strip()
    except KeyboardInterrupt:
        exit_script()
    if udp_input:
        try:
            udp_maps = parse_advanced_ports(udp_input, "udp")
            udp_ports = _maps_to_port_strings(udp_maps)
            c_ok(f"  ✅ Added {len(udp_maps)} UDP {label} mapping(s)")
        except ValueError as e:
            c_err(f"  ⚠️  Invalid UDP mapping: {e}")

    return tcp_ports, udp_ports

def configure_l3_runtime(role: str, label: str = "L3") -> dict:
    print(f"\n  {BOLD}{FG_CYAN}{label} Carrier:{RESET}")
    print(f"  {FG_BLUE}1){RESET} {FG_WHITE}raw{RESET}")
    print(f"  {FG_BLUE}2){RESET} {FG_WHITE}udp{RESET}")
    print(f"  {FG_BLUE}3){RESET} {FG_WHITE}icmp{RESET}")
    print(f"  {FG_BLUE}4){RESET} {FG_WHITE}pcap{RESET}")
    print(f"  {FG_BLUE}5){RESET} {FG_WHITE}tcp{RESET}")
    carrier_choice = ask_int(f"  {BOLD}Carrier:{RESET}", min_=1, max_=5)
    carrier = {1: "raw", 2: "udp", 3: "icmp", 4: "pcap", 5: "tcp"}[carrier_choice]

    print(f"\n  {BOLD}{FG_CYAN}{label} Endpoints:{RESET}")
    auto_ip = safe_get_server_ip(timeout=1.0, prefer_public=False) or ""
    listen_default = auto_ip if auto_ip else ("0.0.0.0" if role == "server" else "")
    listen_ip = ask_nonempty(f"  {BOLD}Local Endpoint IP:{RESET}", default=listen_default)
    dst_ip = ask_nonempty(f"  {BOLD}Peer Endpoint IP:{RESET}")
    interface = ask_nonempty(f"  {BOLD}Network Interface:{RESET}", default=detect_default_interface())

    listen_port = 0
    dst_port = 0
    icmp_type = L3_KERNEL_DEFAULT_ICMP_TYPE
    icmp_code = L3_KERNEL_DEFAULT_ICMP_CODE
    if carrier in ("udp", "pcap"):
        print(f"\n  {BOLD}{FG_CYAN}{label} UDP (outer):{RESET}")
        listen_port = ask_free_port("Local UDP Port", default=40001, protocols=("udp",))
        dst_port = ask_int(f"  {BOLD}Peer UDP Port:{RESET}", min_=1, max_=65535, default=40001)
    elif carrier == "tcp":
        print(f"\n  {BOLD}{FG_CYAN}{label} TCP (outer):{RESET}")
        listen_port = ask_free_port("Local TCP Port", default=40001, protocols=("tcp",))
        dst_port = ask_int(f"  {BOLD}Peer TCP Port:{RESET}", min_=1, max_=65535, default=40001)
        c_warn(
            "  carrier=tcp: start the L3 server process first, then the client — "
            "the server accepts one TCP connection during startup and will block until the peer connects."
        )
    elif carrier == "icmp":
        print(f"\n  {BOLD}{FG_CYAN}{label} ICMP:{RESET}")
        icmp_type = ask_int(
            f"  {BOLD}ICMP Type:{RESET} {FG_WHITE}(8 = echo-request, recommended; 0 = echo-reply is often dropped by stateful firewalls){RESET}",
            min_=0,
            max_=255,
            default=8,
        )
        icmp_code = ask_int(f"  {BOLD}ICMP Code:{RESET}", min_=0, max_=255, default=0)

    print(f"\n  {BOLD}{FG_CYAN}{label} Runtime:{RESET}")
    print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}balanced{RESET}")
    print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}aggressive{RESET}")
    print(f"  {FG_CYAN}[3]{RESET} {FG_WHITE}latency{RESET}")
    print(f"  {FG_CYAN}[4]{RESET} {FG_WHITE}cpu-efficient{RESET}")
    profile_choice = ask_int(f"\n  {BOLD}Select profile:{RESET}", min_=1, max_=4, default=1)
    profile = {1: "balanced", 2: "aggressive", 3: "latency", 4: "cpu-efficient"}[profile_choice]
    heartbeat_interval = ask_int(f"  {BOLD}Heartbeat Interval:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=300, default=5)
    heartbeat_timeout = ask_int(f"  {BOLD}Heartbeat Timeout:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=600, default=30)
    l3_channel_size = ask_int(
        f"  {BOLD}L3 Channel Size:{RESET} {FG_WHITE}(0 = engine default ~15000; max 1M slots; higher = more RAM, burst headroom){RESET}",
        min_=0,
        max_=1048576,
        default=0,
    )
    l3_batch_size = ask_int(
        f"  {BOLD}L3 Batch Size Override:{RESET} {FG_WHITE}(0 = profile baseline ~1024 pkts; max 524288; sendmmsg chunk 256){RESET}",
        min_=0,
        max_=524288,
        default=0,
    )
    so_sndbuf = ask_int(f"  {BOLD}Socket Send Buffer:{RESET} {FG_WHITE}(0 = kernel default){RESET}", min_=0, max_=134217728, default=0)
    so_rcvbuf = ask_int(f"  {BOLD}Socket Receive Buffer:{RESET} {FG_WHITE}(0 = kernel default){RESET}", min_=0, max_=134217728, default=0)
    allow_ip_frag = ask_yesno(
        f"  {BOLD}Allow outer IP fragmentation (DF=0){RESET} {FG_WHITE}(default: N; only enable if you have MTU/path issues){RESET}",
        default=False,
    )
    fragment_size = ask_int(
        f"  {BOLD}Fragment Size:{RESET} {FG_WHITE}(0 = disabled / send as one chunk; minimum safe value: 256){RESET}",
        min_=0,
        max_=65535,
        default=0,
    )
    if 0 < fragment_size < 256:
        c_warn(f"  Fragment size below 256 is not recommended for hardened {label}; adjusted to 256.")
        fragment_size = 256

    pcap_snaplen = 0
    pcap_poll_ms = 0
    pcap_promisc = True
    if carrier == "pcap":
        print(f"\n  {BOLD}{FG_CYAN}{label} libpcap{RESET}")
        pcap_snaplen = ask_int(
            f"  {BOLD}pcap_snaplen{RESET} {FG_WHITE}(0=default 65535){RESET}", min_=0, max_=65535, default=0
        )
        pcap_poll_ms = ask_int(
            f"  {BOLD}pcap_poll_ms{RESET} {FG_WHITE}(0=default 250){RESET}", min_=0, max_=60000, default=0
        )
        pcap_promisc = ask_yesno(
            f"  {BOLD}pcap promiscuous mode{RESET} {FG_WHITE}(capture all link frames; default Y){RESET}",
            default=True,
        )

    cfg = {
        "carrier": carrier,
        "listen_ip": listen_ip,
        "dst_ip": dst_ip,
        "interface": interface,
        "profile": profile,
        "heartbeat_interval": heartbeat_interval,
        "heartbeat_timeout": heartbeat_timeout,
        "channel_size": l3_channel_size,
        "batch_size": l3_batch_size,
        "so_sndbuf": so_sndbuf,
        "so_rcvbuf": so_rcvbuf,
        "allow_ip_frag": bool(allow_ip_frag),
        "fragment_size": fragment_size,
        "listen_port": listen_port,
        "dst_port": dst_port,
        "icmp_type": icmp_type,
        "icmp_code": icmp_code,
        "pcap_snaplen": pcap_snaplen,
        "pcap_poll_ms": pcap_poll_ms,
        "pcap_promisc": pcap_promisc,
    }
    return cfg

def create_l3_server_config_file(cfg: dict) -> Path:
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tun_cfg = cfg.get("tun_config") or {}
    l3_cfg = cfg.get("l3_config") or {}
    stem = tun_cfg.get("name", "netrix") or "netrix"
    config_path = NETRIX_CONFIG_DIR / f"server_l3_{stem}.yaml"
    yaml_l3, carrier = _l3_build_yaml_block(l3_cfg)
    yaml_data = {
        "mode": "server",
        "transport": "l3",
        "tun": {
            "enabled": True,
            "name": tun_cfg.get("name", "netrix"),
            "local": tun_cfg.get("local", "10.10.0.1/24"),
            "remote": tun_cfg.get("remote", "10.10.0.2/24"),
            "mtu": tun_cfg.get("mtu", 1320),
            "streams": tun_cfg.get("streams", 1),
            "health_port": tun_cfg.get("health_port", 1234),
        },
        "l3": yaml_l3,
        "tcp_ports": cfg.get("tcp_ports", []),
        "udp_ports": cfg.get("udp_ports", []),
        "verbose": cfg.get("verbose", False),
    }
    transport_note = f"Netrix L3 ({carrier} outer carrier)"
    comments = {
        "transport": transport_note,
        "tun.enabled": "Enable mandatory TUN interface for L3 mode",
        "tun.name": "TUN interface name for Netrix L3",
        "tun.local": "Local TUN CIDR (server side)",
        "tun.remote": "Peer TUN CIDR (client side)",
        "tun.mtu": "TUN MTU (default: 1320)",
        "tun.health_port": "HTTP health/ready port for L3 TUN health (default: 1234)",
        "tun.streams": "Parallel TUN queues for L3 (default: 1, max: 64)",
        "tcp_ports": "TCP listener mappings for Iran-side L3 forwarding (default target IP = remote TUN peer)",
        "udp_ports": "UDP listener mappings for Iran-side L3 forwarding (default target IP = remote TUN peer)",
    }
    comments.update(_l3_yaml_comments(carrier))
    write_yaml_with_comments(config_path, yaml_data, comments)
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass
    return config_path

def create_l3_client_config_file(cfg: dict) -> Path:
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tun_cfg = cfg.get("tun_config") or {}
    l3_cfg = cfg.get("l3_config") or {}
    stem = tun_cfg.get("name", "netrix") or "netrix"
    config_path = NETRIX_CONFIG_DIR / f"client_l3_{stem}.yaml"
    yaml_l3, carrier = _l3_build_yaml_block(l3_cfg)
    yaml_data = {
        "mode": "client",
        "transport": "l3",
        "tun": {
            "enabled": True,
            "name": tun_cfg.get("name", "netrix"),
            "local": tun_cfg.get("local", "10.10.0.2/24"),
            "remote": tun_cfg.get("remote", "10.10.0.1/24"),
            "mtu": tun_cfg.get("mtu", 1320),
            "streams": tun_cfg.get("streams", 1),
            "health_port": tun_cfg.get("health_port", 1234),
        },
        "l3": yaml_l3,
        "verbose": cfg.get("verbose", False),
    }
    transport_note = f"Netrix L3 ({carrier} outer carrier)"
    comments = {
        "transport": transport_note,
        "tun.enabled": "Enable mandatory TUN interface for L3 mode",
        "tun.name": "TUN interface name for Netrix L3",
        "tun.local": "Local TUN CIDR (client side)",
        "tun.remote": "Peer TUN CIDR (server side)",
        "tun.mtu": "TUN MTU (default: 1320)",
        "tun.health_port": "HTTP health/ready port for L3 TUN health (default: 1234)",
        "tun.streams": "Parallel TUN queues for L3 (default: 1, max: 64)",
    }
    comments.update(_l3_yaml_comments(carrier))
    write_yaml_with_comments(config_path, yaml_data, comments)
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass
    return config_path

def create_server_l3_tunnel():
    print(f"\n  {FG_GREEN}✅ Netrix L3 selected:{RESET} {FG_WHITE}TUN + selectable outer carrier{RESET}")
    tun_config = configure_l3_tun("server")
    tcp_ports, udp_ports = configure_l3_port_mappings()
    l3_runtime = configure_l3_runtime("server")
    l3_security = configure_l3_security()
    print(f"\n  {BOLD}{FG_CYAN}L3 Logging:{RESET}")
    verbose = ask_yesno(f"  {BOLD}Enable verbose logging?{RESET}", default=False)
    cfg = {
        "transport": "l3",
        "tun_config": tun_config,
        "l3_config": {**l3_runtime, **l3_security},
        "tcp_ports": tcp_ports,
        "udp_ports": udp_ports,
        "verbose": verbose,
        "direct": False,
    }
    config_path = create_server_config_file(0, cfg)
    print()
    print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
    c_ok(f"  ✅ Configuration saved: {FG_WHITE}{config_path}{RESET}")
    print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
    if ask_yesno(f"\n  {BOLD}{FG_GREEN}Start tunnel now?{RESET}", default=True):
        print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
        if run_tunnel(config_path):
            c_ok(f"  ✅ Tunnel started successfully!")
        else:
            c_err("  ❌ Failed to start tunnel!")
    pause()

def create_client_l3_tunnel():
    print(f"\n  {FG_GREEN}✅ Netrix L3 selected:{RESET} {FG_WHITE}TUN + selectable outer carrier{RESET}")
    print(f"  {FG_WHITE}Note: Reverse/Direct is not used for L3. Each side runs with mode=server or mode=client only.{RESET}")
    tun_config = configure_l3_tun("client")
    l3_runtime = configure_l3_runtime("client")
    l3_security = configure_l3_security()
    print(f"\n  {BOLD}{FG_CYAN}L3 Logging:{RESET}")
    verbose = ask_yesno(f"  {BOLD}Enable verbose logging?{RESET}", default=False)
    cfg = {
        "transport": "l3",
        "tun_config": tun_config,
        "l3_config": {**l3_runtime, **l3_security},
        "verbose": verbose,
        "direct": False,
    }
    config_path = create_client_config_file(cfg)
    print()
    print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
    c_ok(f"  ✅ Configuration saved: {FG_WHITE}{config_path}{RESET}")
    print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
    if ask_yesno(f"\n  {BOLD}{FG_GREEN}Start tunnel now?{RESET}", default=True):
        print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
        if run_tunnel(config_path):
            c_ok(f"  ✅ Tunnel started successfully!")
        else:
            c_err("  ❌ Failed to start tunnel!")
    pause()

def get_config_path(tport: int) -> Path:
    """مسیر فایل کانفیگ YAML در /root/netrix"""
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return NETRIX_CONFIG_DIR / f"server_{tport}.yaml"

def get_default_smux_config(profile: str = "balanced") -> dict:
    """تنظیمات پیش‌فرض SMUX بر اساس profile - همگام با netrix.go"""
    profiles = {
        "balanced": {
            "keepalive": 15,  
            "max_recv": 4194304,
            "max_stream": 2097152,
            "frame_size": 32768,  
            "version": 2,
            "mux_con": 8  
        },
        "aggressive": {
            "keepalive": 30,     
            "max_recv": 8388608,  
            "max_stream": 4194304,  
            "frame_size": 65535, 
            "version": 2,
            "mux_con": 16 
        },
        "latency": {
            "keepalive": 5,       
            "max_recv": 2097152,  
            "max_stream": 1048576,  
            "frame_size": 16384,  
            "version": 2,
            "mux_con": 4  
        },
        "cpu-efficient": {
            "keepalive": 60,      
            "max_recv": 2097152, 
            "max_stream": 1048576,  
            "frame_size": 16384, 
            "version": 2,
            "mux_con": 4 
        }
    }
    return profiles.get(profile.lower(), profiles["balanced"])

def _extract_ip_from_addr(addr: str) -> str:
    """Extract an IP (v4/v6) from strings like '1.2.3.4:200' or '[2001:db8::1]:200'. Returns '' if host is not an IP."""
    if not addr:
        return ""
    a = str(addr).strip()
    host = ""
    if a.startswith("["):
        if "]" in a:
            host = a[1:a.index("]")]
        else:
            host = a.strip("[]")
    else:
        if ":" in a and a.count(":") == 1 and a.rsplit(":", 1)[1].isdigit():
            host = a.rsplit(":", 1)[0]
        elif ":" in a and a.rsplit(":", 1)[-1].isdigit():
            parts = a.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit() and "." in parts[0]:
                host = parts[0]
            else:
                host = a
        else:
            host = a

    try:
        ip = ipaddress.ip_address(host)
        return str(ip)
    except Exception:
        return ""

def get_default_kcp_config(profile: str = "balanced") -> dict:
    """تنظیمات پیش‌فرض KCP بر اساس profile - از KCP_PROFILES همگام با netrix.go"""
    return KCP_PROFILES.get((profile or "balanced").strip().lower(), KCP_PROFILES["balanced"])

def get_default_rawsocket_config(profile: str = "balanced") -> dict:
    """
    تنظیمات پیش‌فرض rawsocket (KCP+FEC) — جدا از KCP؛ از RAWSOCKET_* و RAWSOCKET_PROFILES.
    """
    p = (profile or "balanced").strip().lower()
    base = {
        "mtu": RAWSOCKET_MTU,
        "snd_wnd": RAWSOCKET_SND_WND,
        "rcv_wnd": RAWSOCKET_RCV_WND,
        "data_shard": RAWSOCKET_DATA_SHARD,
        "parity_shard": RAWSOCKET_PARITY_SHARD,
        "sock_buf": RAWSOCKET_SOCK_BUF,
    }
    out = {**base, **RAWSOCKET_PROFILES.get(p, {})}
    out["mtu"] = max(576, min(9000, int(out.get("mtu", RAWSOCKET_MTU))))
    for k in ("snd_wnd", "rcv_wnd", "data_shard", "parity_shard", "sock_buf"):
        v = int(out.get(k) or 0)
        out[k] = base[k] if v <= 0 else v

    return out


def _l3_build_yaml_block(l3_cfg: dict) -> tuple[dict, str]:
    """Build the l3: YAML map exactly as netrix.go expects (defaults + carrier-specific keys)."""
    carrier = (l3_cfg.get("carrier") or L3_KERNEL_DEFAULT_CARRIER).strip().lower()
    profile = (l3_cfg.get("profile") or L3_KERNEL_DEFAULT_PROFILE).strip().lower()
    yaml_l3: dict = {
        "profile": profile,
        "carrier": carrier,
        "listen_ip": l3_cfg.get("listen_ip", ""),
        "dst_ip": l3_cfg.get("dst_ip", ""),
        "interface": l3_cfg.get("interface") or detect_default_interface(),
        "heartbeat_interval": int(
            l3_cfg.get("heartbeat_interval", L3_KERNEL_DEFAULT_HEARTBEAT_INTERVAL)
        ),
        "heartbeat_timeout": int(
            l3_cfg.get("heartbeat_timeout", L3_KERNEL_DEFAULT_HEARTBEAT_TIMEOUT)
        ),
        "channel_size": int(l3_cfg.get("channel_size", L3_KERNEL_DEFAULT_CHANNEL_SIZE) or 0),
        "batch_size": int(l3_cfg.get("batch_size", L3_KERNEL_DEFAULT_BATCH_SIZE) or 0),
        "enable_encryption": bool(
            l3_cfg.get("enable_encryption", L3_KERNEL_DEFAULT_ENABLE_ENCRYPTION)
        ),
        "algorithm": l3_cfg.get("algorithm", L3_KERNEL_DEFAULT_ALGORITHM),
        "psk": l3_cfg.get("psk", ""),
        "kdf_iterations": int(l3_cfg.get("kdf_iterations", L3_KERNEL_DEFAULT_KDF_ITERATIONS)),
        "so_sndbuf": int(l3_cfg.get("so_sndbuf", 0) or 0),
        "so_rcvbuf": int(l3_cfg.get("so_rcvbuf", 0) or 0),
        "allow_ip_frag": bool(l3_cfg.get("allow_ip_frag", False)),
        "fragment_size": int(l3_cfg.get("fragment_size", 0) or 0),
    }
    if carrier in ("udp", "pcap", "tcp"):
        listen_port = int(l3_cfg.get("listen_port", L3_KERNEL_DEFAULT_LISTEN_PORT))
        yaml_l3["listen_port"] = listen_port
        yaml_l3["dst_port"] = int(l3_cfg.get("dst_port", listen_port or L3_KERNEL_DEFAULT_DST_PORT))
    elif carrier == "icmp":
        yaml_l3["icmp_type"] = int(l3_cfg.get("icmp_type", L3_KERNEL_DEFAULT_ICMP_TYPE))
        yaml_l3["icmp_code"] = int(l3_cfg.get("icmp_code", L3_KERNEL_DEFAULT_ICMP_CODE))
    if carrier == "pcap":
        yaml_l3["pcap_snaplen"] = int(l3_cfg.get("pcap_snaplen", 0) or 0)
        yaml_l3["pcap_poll_ms"] = int(l3_cfg.get("pcap_poll_ms", 0) or 0)
        yaml_l3["pcap_promisc"] = bool(l3_cfg.get("pcap_promisc", L3_KERNEL_DEFAULT_PCAP_PROMISC))
    return yaml_l3, carrier


def _l3_yaml_comments(carrier: str) -> dict:
    comments = {
        "l3.profile": "L3 runtime profile (balanced|aggressive|latency|cpu-efficient). Independent from global profile.",
        "l3.carrier": "Outer carrier: raw, udp, icmp, pcap, or tcp (pcap uses libpcap for RX; tcp uses stream carrier)",
        "l3.listen_ip": "Local outer IP endpoint",
        "l3.dst_ip": "Peer outer IP endpoint",
        "l3.interface": "Network interface used for routing and pcap/raw receive (auto-detected when possible)",
        "l3.pcap_snaplen": "carrier=pcap only: capture snaplen (0 = engine default 65535)",
        "l3.pcap_poll_ms": "carrier=pcap only: read timeout in ms (0 = default 250; enables clean shutdown)",
        "l3.pcap_promisc": "carrier=pcap only: promiscuous capture (engine default true when omitted)",
        "l3.heartbeat_interval": "Heartbeat send interval in seconds (0 = engine default 5)",
        "l3.heartbeat_timeout": "Heartbeat timeout before peer becomes not-ready (0 = engine default 30)",
        "l3.enable_encryption": "Enable per-packet AEAD encryption (engine default true when omitted)",
        "l3.algorithm": "Packet encryption algorithm: aes-256-gcm, aes-128-gcm, chacha20-poly1305",
        "l3.psk": "Packet encryption PSK",
        "l3.kdf_iterations": "PBKDF2 iterations for deriving the packet key (0 = engine default 100000)",
        "l3.so_sndbuf": "Socket send buffer (0 = kernel default)",
        "l3.so_rcvbuf": "Socket receive buffer (0 = kernel default)",
        "l3.allow_ip_frag": "If true, clear IPv4 DF bit on outer packets. Engine default false (DF=1).",
        "l3.fragment_size": "NL3X inner fragment size (bytes). 0 = disabled. Explicit values use minimum 256.",
        "l3.channel_size": "L3 queue budget per direction (0 = engine default 15000; max 1048576)",
        "l3.batch_size": "TX batch override per worker (0 = profile baseline; max 524288)",
    }
    if carrier in ("udp", "pcap"):
        comments["l3.listen_port"] = "Local UDP port (engine default 40001 when 0)"
        comments["l3.dst_port"] = "Peer UDP port (engine default = listen_port when 0)"
    elif carrier == "tcp":
        comments["l3.listen_port"] = "Local TCP port (engine default 40001 when 0)"
        comments["l3.dst_port"] = "Peer TCP port (engine default = listen_port when 0)"
    elif carrier == "icmp":
        comments["l3.icmp_type"] = "ICMP type on wire (8 = echo-request recommended; 0 = echo-reply often filtered)"
        comments["l3.icmp_code"] = "ICMP code on wire"
    return comments
def detect_rawsocket_pcap_defaults() -> Dict[str, Any]:
    """
    تشخیص خودکار interface، local IP و router MAC برای rawsocket/pcap روی لینوکس.
    مثل بقیه سوالات: بدون پرسش، مقدارها را از سیستم می‌گیرد و در کانفیگ می‌نویسد.
    Returns: {"interface": str, "local_ip": str, "router_mac": str, "local_flags": list, "remote_flags": list}
    """
    out = {"interface": "", "local_ip": "", "router_mac": "", "local_flags": [], "remote_flags": []}
    if platform.system() != "Linux":
        return out
    try:
        r = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=2
        )
        if r.returncode != 0 or not r.stdout.strip():
            return out
        parts = r.stdout.strip().split()
        iface = ""
        gw_ip = ""
        for i, p in enumerate(parts):
            if p == "dev" and i + 1 < len(parts):
                iface = parts[i + 1]
            if p == "via" and i + 1 < len(parts):
                gw_ip = parts[i + 1]
        if not iface:
            return out
        out["interface"] = iface

        r2 = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", iface],
            capture_output=True, text=True, timeout=2
        )
        if r2.returncode == 0 and r2.stdout:
            for line in r2.stdout.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    addr = line.split()[1].split("/")[0]
                    if addr:
                        out["local_ip"] = addr
                        break

        if gw_ip:
            r3 = subprocess.run(
                ["ip", "neigh", "show", gw_ip],
                capture_output=True, text=True, timeout=2
            )
            if r3.returncode == 0 and r3.stdout:
                for line in r3.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and parts[4].count(":") == 5:
                        out["router_mac"] = parts[4].lower()
                        break
            if not out["router_mac"]:
                r4 = subprocess.run(
                    ["arp", "-n", gw_ip],
                    capture_output=True, text=True, timeout=2
                )
                if r4.returncode == 0 and r4.stdout:
                    for line in r4.stdout.splitlines()[1:]:
                        parts = line.split()
                        if len(parts) >= 3 and len(parts[2]) == 17 and ":" in parts[2]:
                            out["router_mac"] = parts[2].lower()
                            break
    except Exception:
        pass
    return out

def get_default_advanced_config(transport: str) -> dict:
    """تنظیمات پیش‌فرض Advanced بر اساس transport - همگام با netrix.go (مقادیر همان عددهای هسته)"""
    base_config = {
        "tcp_nodelay": True,
        "tcp_keepalive": 15,
        "tcp_read_buffer": 8388608,
        "tcp_write_buffer": 8388608,
        "cleanup_interval": 60,
        "session_timeout": 180,
        "connection_timeout": 600,
        "stream_timeout": 21600,
        "stream_idle_timeout": 600,
        "max_udp_flows": 5000,
        "udp_flow_timeout": 600,
        "tls_insecure_skip_verify": False,
        "verbose": False
    }
    

    if transport in ("kcpmux", "kcp", "rawsocket", "rawmux"):
        base_config.update({
            "udp_read_buffer": 4194304,  
            "udp_write_buffer": 4194304  
        })
    elif transport in ("tlsmux", "tls", "realitymux", "reality"):
        base_config.update({
            "tls_insecure_skip_verify": False
        })
    elif transport in ("wsmux", "wssmux"):
        base_config.update({
            "websocket_read_buffer": 524288, 
            "websocket_write_buffer": 524288, 
            "websocket_compression": False    
        })
    
    return base_config

def parse_yaml_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """خواندن فایل کانفیگ YAML"""
    if not config_path.exists():
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None

def get_certificate_with_acme(domain: str, email: str, port: int) -> tuple[Optional[str], Optional[str]]:
    """
    گرفتن certificate واقعی با acme.sh (Let's Encrypt)
    Returns: (cert_file_path, key_file_path) or (None, None) on error
    """
    cert_file = Path("/root/cert.crt")
    key_file = Path("/root/private.key")
    
    print(f"\n  {BOLD}{FG_CYAN}🔐 Starting Certificate Acquisition Process{RESET}")
    print(f"  {BOLD}Domain:{RESET} {FG_GREEN}{domain}{RESET}")
    print(f"  {BOLD}Email:{RESET} {FG_GREEN}{email}{RESET}")
    print(f"  {BOLD}Port:{RESET} {FG_GREEN}{port}{RESET}\n")
    
    print(f"  {FG_CYAN}📦 Step 1/5:{RESET} {BOLD}Installing curl and socat...{RESET}")
    result = subprocess.run(
        ["apt", "install", "curl", "socat", "-y"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        c_err("  ❌ Failed to install curl/socat")
        return None, None
    c_ok(f"  ✅ curl and socat installed")
    
    print(f"\n  {FG_CYAN}📦 Step 2/5:{RESET} {BOLD}Installing acme.sh...{RESET}")
    result = subprocess.run(
        ["bash", "-c", "curl https://get.acme.sh | sh"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        c_err("  ❌ Failed to install acme.sh")
        return None, None
    c_ok(f"  ✅ acme.sh installed")
    
    print(f"\n  {FG_CYAN}⚙️  Step 3/5:{RESET} {BOLD}Setting Let's Encrypt as default CA...{RESET}")
    acme_sh = Path.home() / ".acme.sh" / "acme.sh"
    result = subprocess.run(
        [str(acme_sh), "--set-default-ca", "--server", "letsencrypt"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        c_warn("  ⚠️  Failed to set default CA (continuing anyway)")
    else:
        c_ok(f"  ✅ Default CA set to Let's Encrypt")
    
    print(f"\n  {FG_CYAN}📝 Step 4/5:{RESET} {BOLD}Registering account with email {FG_GREEN}{email}{RESET}...")
    result = subprocess.run(
        [str(acme_sh), "--register-account", "-m", email],
        capture_output=True,
        text=True
    )
    if result.returncode != 0: 
        c_err(f"  ❌ Failed to register account: {FG_RED}{result.stderr}{RESET}")
        return None, None
    c_ok(f"  ✅ Account registered successfully")
    

    print(f"\n  {FG_CYAN}🎫 Step 5/5:{RESET} {BOLD}Issuing certificate for {FG_GREEN}{domain}{RESET}...")
    
    port_80_in_use = False
    nginx_stopped = False
    try:
        result = subprocess.run(
            ["lsof", "-i", ":80"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            port_80_in_use = True
            c_warn(f"  ⚠️  Port 80 in use")
            if ask_yesno(f"  {BOLD}Stop nginx temporarily?{RESET}", default=True):
                subprocess.run(["systemctl", "stop", "nginx"], check=False)
                nginx_stopped = True
    except Exception:
        pass
    
    if not port_80_in_use or nginx_stopped:
        pass
    else:
        c_err("  ❌ Port 80 must be free for verification")
        return None, None
    
    result = subprocess.run(
        [str(acme_sh), "--issue", "-d", domain, "--standalone"],
        capture_output=True,
        text=True
    )
    
    if nginx_stopped:
        subprocess.run(["systemctl", "start", "nginx"], check=False)
    
    if result.returncode != 0:
        c_err(f"  ❌ Failed to issue certificate: {FG_RED}{result.stderr}{RESET}")
        return None, None
    c_ok(f"  ✅ Certificate issued successfully")
    
    print(f"\n  {FG_CYAN}💾 Installing certificate to /root...{RESET}")
    result = subprocess.run(
        [
            str(acme_sh),
            "--installcert",
            "-d", domain,
            "--key-file", str(key_file),
            "--fullchain-file", str(cert_file)
        ],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        c_err(f"  ❌ Failed to install certificate: {FG_RED}{result.stderr}{RESET}")
        return None, None
    
    if not cert_file.exists() or not key_file.exists():
        c_err("  ❌ Certificate files not found after installation")
        return None, None
    
    c_ok(f"  ✅ Certificate installed: {FG_GREEN}{cert_file}{RESET}")
    c_ok(f"  ✅ Private key installed: {FG_GREEN}{key_file}{RESET}")
    
    return str(cert_file), str(key_file)

def write_yaml_with_comments(file_path: Path, data: dict, comments: dict = None):
    """نوشتن YAML با comment های default values"""
    if comments is None:
        comments = {}
    
    lines = []
    
    def write_dict(d: dict, indent: int = 0, parent_key: str = ""):
        for key, value in d.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            comment = comments.get(full_key, "")
            
            if isinstance(value, dict):
                if comment:
                    lines.append(f"{'  ' * indent}{key}:  # {comment}")
                else:
                    lines.append(f"{'  ' * indent}{key}:")
                write_dict(value, indent + 1, full_key)
            elif isinstance(value, list):
                if value and all(isinstance(item, (int, str, float)) and not isinstance(item, dict) for item in value):
                    formatted_items = []
                    for item in value:
                        if isinstance(item, str):
                            escaped = item.replace('"', '\\"')
                            formatted_items.append(f'"{escaped}"')
                        else:
                            formatted_items.append(str(item))
                    inline_list = "[" + ",".join(formatted_items) + "]"
                    if comment:
                        lines.append(f"{'  ' * indent}{key}: {inline_list}  # {comment}")
                    else:
                        lines.append(f"{'  ' * indent}{key}: {inline_list}")
                else:
                    if comment:
                        lines.append(f"{'  ' * indent}{key}:  # {comment}")
                    else:
                        lines.append(f"{'  ' * indent}{key}:")
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(f"{'  ' * (indent + 1)}-")
                            for k, v in item.items():
                                if isinstance(v, bool):
                                    fv = "true" if v else "false"
                                elif v is None:
                                    fv = '""'
                                else:
                                    sv = str(v)
                                    if isinstance(v, str) and (sv.startswith('[') or sv.startswith('{') or ':' in sv or '#' in sv):
                                        fv = f'"{sv}"'
                                    else:
                                        fv = sv if sv != "" else '""'
                                lines.append(f"{'  ' * (indent + 2)}{k}: {fv}")
                        else:
                            lines.append(f"{'  ' * (indent + 1)}- {item}")
            else:
                if isinstance(value, bool):
                    formatted_value = "true" if value else "false"
                elif value is None:
                    formatted_value = '""'
                else:
                    str_value = str(value)
                    needs_quote = (
                        isinstance(value, str) and 
                        (str_value.startswith('[') or str_value.startswith('{') or 
                         ':' in str_value or '#' in str_value or 
                         str_value.startswith('*') or str_value.startswith('&') or
                         str_value.startswith('/')) 
                    )
                    if needs_quote:
                        formatted_value = f'"{str_value}"'
                    else:
                        formatted_value = str_value if str_value != "" else '""'
                
                if comment:
                    lines.append(f"{'  ' * indent}{key}: {formatted_value}  # {comment}")
                else:
                    lines.append(f"{'  ' * indent}{key}: {formatted_value}")
    
    write_dict(data)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        f.write('\n')

def create_server_config_file(tport: int, cfg: dict) -> Path:
    """ساخت فایل کانفیگ YAML برای سرور"""
    if cfg.get("transport") == "l3":
        return create_l3_server_config_file(cfg)
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    direct_mode = cfg.get('direct', False)
    
    if direct_mode:
        config_path = NETRIX_CONFIG_DIR / f"server_direct_{tport}.yaml"
    else:
        config_path = NETRIX_CONFIG_DIR / f"server_{tport}.yaml"
    
    transport = cfg.get('transport', 'tcpmux')
    profile = cfg.get('profile', 'balanced')
    
    yaml_data = {
        "mode": "server",
        "transport": transport,
        "psk": cfg.get('psk', '')
    }
    
    if direct_mode:
        yaml_data["direct"] = True
        yaml_data["connect"] = cfg.get('connect', '')
        _edge = (cfg.get("edge_ip") or "").strip()
        if _edge:
            yaml_data["edge_ip"] = _edge
        yaml_data["connection_pool"] = cfg.get('connection_pool', 8)
        yaml_data["retry_interval"] = cfg.get("retry_interval", 3)
        yaml_data["dial_timeout"] = cfg.get("dial_timeout", 10)
        yaml_data["aggressive_pool"] = cfg.get("aggressive_pool", False)
    else:
        yaml_data["listen"] = cfg.get('listen', f"0.0.0.0:{tport}")
    
    if cfg.get("cert_file") and cfg.get("key_file"):
        yaml_data["cert_file"] = cfg["cert_file"]
        yaml_data["key_file"] = cfg["key_file"]
        print(f"  {FG_GREEN}✅ Certificate files will be written to YAML: cert={cfg['cert_file']}, key={cfg['key_file']}{RESET}")
    
    if transport == "realitymux" and cfg.get("reality_sni") and cfg.get("reality_fingerprint"):
        yaml_data["reality"] = {
            "sni": cfg.get("reality_sni", "cloudflare.com"),
            "fingerprint": cfg.get("reality_fingerprint", "chrome")
        }
        if cfg.get("reality_short_id"):
            yaml_data["reality"]["short_id"] = cfg.get("reality_short_id")
        if cfg.get("reality_public_key"):
            yaml_data["reality"]["public_key"] = cfg.get("reality_public_key")
        print(f"  {FG_GREEN}✅ REALITY config will be written to YAML: SNI={cfg.get('reality_sni')}, Fingerprint={cfg.get('reality_fingerprint')}{RESET}")
    
    yaml_data["profile"] = profile
    
    smux_default = get_default_smux_config(profile)
    yaml_data["smux"] = {
        "keepalive": smux_default["keepalive"],
        "max_recv": smux_default["max_recv"],
        "max_stream": smux_default["max_stream"],
        "frame_size": smux_default["frame_size"],
        "version": smux_default["version"],
    }
    
    if direct_mode:
        yaml_data["smux"]["mux_con"] = cfg.get('mux_con', smux_default.get("mux_con", 8))
    
    if transport == "kcpmux":
        kcp_default = get_default_kcp_config(profile)
        yaml_data["kcp"] = {
            "nodelay": kcp_default["nodelay"],
            "interval": kcp_default["interval"],
            "resend": kcp_default["resend"],
            "nc": kcp_default["nc"],
            "sndwnd": kcp_default["sndwnd"],
            "rcvwnd": kcp_default["rcvwnd"],
            "mtu": kcp_default["mtu"]
        }
    if transport in ("rawsocket", "rawmux"):
        rs_default = get_default_rawsocket_config(profile)
        yaml_data["rawsocket"] = {
            "mtu": rs_default["mtu"],
            "snd_wnd": rs_default["snd_wnd"],
            "rcv_wnd": rs_default["rcv_wnd"],
            "data_shard": rs_default["data_shard"],
            "parity_shard": rs_default["parity_shard"],
            "sock_buf": rs_default.get("sock_buf", RAWSOCKET_SOCK_BUF),
        }
        if cfg.get("rawsocket_interface"):
            yaml_data["rawsocket"]["interface"] = cfg["rawsocket_interface"]
        if cfg.get("rawsocket_local_ip"):
            yaml_data["rawsocket"]["local_ip"] = cfg["rawsocket_local_ip"]
        if cfg.get("rawsocket_router_mac"):
            yaml_data["rawsocket"]["router_mac"] = cfg["rawsocket_router_mac"]
        if cfg.get("rawsocket_local_flags"):
            yaml_data["rawsocket"]["local_flags"] = cfg["rawsocket_local_flags"]
        if cfg.get("rawsocket_remote_flags"):
            yaml_data["rawsocket"]["remote_flags"] = cfg["rawsocket_remote_flags"]
        peer_ip = (cfg.get("rawsocket_peer_ip") or "").strip()
        if not peer_ip and direct_mode and cfg.get("connect"):
            peer_ip = _extract_ip_from_addr(str(cfg.get("connect")))
        if peer_ip:
            yaml_data["rawsocket"]["peer_ip"] = peer_ip

        print(f"  {FG_GREEN}✅ rawsocket config will be written to YAML (KCP+FEC){RESET}")
    
    advanced_default = get_default_advanced_config(transport)
    advanced_default.pop("stream_queue_size", None)
    yaml_data["advanced"] = {}
    for key, value in advanced_default.items():
        if key != "verbose":
            yaml_data["advanced"][key] = value
    
    if "buffer_pool_config" in cfg:
        buffer_config = cfg["buffer_pool_config"]
        if "buffer_pool_size" in buffer_config:
            yaml_data["advanced"]["buffer_pool_size"] = buffer_config["buffer_pool_size"]
        if "large_buffer_pool_size" in buffer_config:
            yaml_data["advanced"]["large_buffer_pool_size"] = buffer_config["large_buffer_pool_size"]
        if "udp_frame_pool_size" in buffer_config:
            yaml_data["advanced"]["udp_frame_pool_size"] = buffer_config["udp_frame_pool_size"]
        if "udp_data_slice_size" in buffer_config:
            yaml_data["advanced"]["udp_data_slice_size"] = buffer_config["udp_data_slice_size"]
    
    if cfg.get("tls_insecure_skip_verify") is True:
        yaml_data["advanced"]["tls_insecure_skip_verify"] = True
    
    if cfg.get("anti_dpi_delay_ms", 0) > 0:
        yaml_data["advanced"]["anti_dpi_delay_ms"] = cfg.get("anti_dpi_delay_ms")
    
    if not cfg.get("direct") and cfg.get("stream_queue_size"):
        yaml_data["advanced"]["stream_queue_size"] = int(cfg["stream_queue_size"])
    
    yaml_data["verbose"] = cfg.get("verbose", False)
    
    compression_cfg = cfg.get("compression_config", {})
    yaml_data["compression"] = {
        "enabled": compression_cfg.get("enabled", True), 
        "algorithm": compression_cfg.get("algorithm", "lz4"), 
        "level": compression_cfg.get("level", 0), 
        "min_size": compression_cfg.get("min_size", 1024), 
        "max_size": compression_cfg.get("max_size", 65536) 
    }
    
    yaml_data["encryption"] = {
        "enabled": cfg.get("encryption_enabled", False),
        "algorithm": cfg.get("encryption_algorithm", "chacha"),
        "key": cfg.get("encryption_key", "")
    }
    

    _pad_max = min(cfg.get("stealth_padding_max", 128), 255)
    _pad_min = min(cfg.get("stealth_padding_min", 0), 255)
    if _pad_min > _pad_max:
        _pad_min = _pad_max
    yaml_data["stealth"] = {
        "padding_enabled": cfg.get("stealth_padding", False),
        "padding_min": _pad_min,
        "padding_max": _pad_max,
        "jitter_enabled": cfg.get("stealth_jitter", False),
        "jitter_min_ms": cfg.get("stealth_jitter_min", 5),
        "jitter_max_ms": cfg.get("stealth_jitter_max", 20)
    }

    yaml_data["health_port"] = cfg.get('health_port', 19080)
    
    if "max_sessions" in cfg:
        yaml_data["max_sessions"] = cfg['max_sessions']
    
    if "heartbeat" in cfg:
        yaml_data["heartbeat"] = cfg['heartbeat']
    
    tcp_ports_list = []
    udp_ports_list = []
    
    if cfg.get('maps'):
        for m in cfg['maps']:
            protocol = m.get('type', 'tcp')
            bind_parts = m['bind'].split(':')
            target_parts = m['target'].split(':')
            if len(bind_parts) == 2 and len(target_parts) == 2:
                bind_ip = bind_parts[0]
                bind_port = bind_parts[1]
                target_ip = target_parts[0]
                target_port = target_parts[1]
                
                port_str = ""
                if bind_ip == "0.0.0.0" and target_ip == "127.0.0.1" and bind_port == target_port:
                    port_str = bind_port
                elif bind_ip == "0.0.0.0" and target_ip == "127.0.0.1" and bind_port != target_port:
                    port_str = f"{bind_port}={target_port}"
                elif bind_ip != "0.0.0.0" or target_ip != "127.0.0.1":
                    if bind_ip == "0.0.0.0":
                        port_str = f"{bind_port}={target_ip}:{target_port}"
                    else:
                        port_str = f"{bind_ip}:{bind_port}={target_ip}:{target_port}"
                else:
                    port_str = f"{m['bind']}={m['target']}"
                
                if protocol == "tcp":
                    tcp_ports_list.append(port_str)
                elif protocol == "udp":
                    udp_ports_list.append(port_str)
    
    yaml_data["tcp_ports"] = tcp_ports_list
    yaml_data["udp_ports"] = udp_ports_list
    
    tun_cfg = cfg.get("tun_config") or {}
    yaml_data["tun"] = {
        "enabled": tun_cfg.get("enabled", False),
        "name": tun_cfg.get("name", "netrix0"),
        "local": tun_cfg.get("local", "10.200.0.1/30"),
        "mtu": tun_cfg.get("mtu", 1400),
        "routes": tun_cfg.get("routes", []),
        "streams": tun_cfg.get("streams", 4),
        "forward_l2tp": tun_cfg.get("forward_l2tp", False),
        "l2tp_ports": tun_cfg.get("l2tp_ports", [500,4500,1701]),
        "l2tp_dest_ip": tun_cfg.get("l2tp_dest_ip", ""),
    }
    
    if cfg.get("proxy_protocol_enabled", False):
        proxy_config = {
            "enabled": True,
            "version": cfg.get("proxy_protocol_version", "v1")
        }
        proxy_ports = cfg.get("proxy_protocol_ports", [])
        if proxy_ports:
            proxy_config["port_list"] = proxy_ports
        yaml_data["proxy_protocol"] = proxy_config

    comments = {
        "profile": f"Performance profile (default: balanced)",
        "smux.keepalive": f"Keepalive interval in seconds (default: {smux_default['keepalive']})",
        "smux.max_recv": f"Max receive buffer in bytes (default: {smux_default['max_recv']} = 4MB)",
        "smux.max_stream": f"Max stream buffer in bytes (default: {smux_default['max_stream']} = 1MB)",
        "smux.frame_size": f"Frame size in bytes (default: {smux_default['frame_size']} = 32KB)",
        "smux.version": f"SMUX version (default: {smux_default['version']})",
        "advanced.tcp_nodelay": f"TCP NoDelay (default: true)",
        "advanced.tcp_keepalive": f"TCP KeepAlive in seconds (default: 15 - تشخیص سریع‌تر dead connections)",
        "advanced.tcp_read_buffer": f"TCP read buffer in bytes (default: 8388608 = 8MB)",
        "advanced.tcp_write_buffer": f"TCP write buffer in bytes (default: 8388608 = 8MB)",
        "advanced.cleanup_interval": f"Cleanup interval in seconds (default: 60)",
        "advanced.session_timeout": f"Session timeout in seconds (default: 180 = 3 minutes - فقط برای sessions بدون heartbeat)",
        "advanced.connection_timeout": f"Connection timeout in seconds (default: 600 = 10 minutes)",
        "advanced.stream_timeout": f"Stream max lifetime in seconds (default: 21600 = 6 hours)",
        "advanced.stream_idle_timeout": f"Stream idle timeout in seconds (default: 600 = 10 minutes)",
        "advanced.max_udp_flows": f"Max UDP flows (default: 5000)",
        "advanced.udp_flow_timeout": f"UDP flow timeout in seconds (default: 600 = 10 minutes)",
        "advanced.tls_insecure_skip_verify": f"Skip TLS certificate verification (default: false - secure by default, can be enabled for self-signed certs)",
        "advanced.buffer_pool_size": f"Buffer pool size in bytes (default: {DEFAULT_BUFFER_POOL_SIZE})",
        "advanced.large_buffer_pool_size": f"Large buffer pool size in bytes (default: {DEFAULT_LARGE_BUFFER_POOL_SIZE})",
        "advanced.udp_frame_pool_size": f"UDP frame pool size in bytes (default: {DEFAULT_UDP_FRAME_POOL_SIZE})",
        "advanced.udp_data_slice_size": f"UDP slice size in bytes (default: {DEFAULT_UDP_SLICE_SIZE})",
        "advanced.anti_dpi_delay_ms": "Anti-DPI delay in ms after connection (0=disabled, 50-500, applied on dialer; Direct=server, Reverse=client)",
        "heartbeat": f"Heartbeat interval in seconds (default: {DEFAULT_HEARTBEAT})",
        "verbose": f"Verbose logging (default: false)",
        "compression.enabled": "Enable compression (default: true)",
        "compression.algorithm": "Compression algorithm: lz4, zstd, or snappy",
        "compression.level": "Compression level",
        "compression.min_size": "Minimum size to compress in bytes (default: 1024)",
        "compression.max_size": "Maximum frame size in bytes (default: 65536)",
        "encryption.enabled": "Enable AEAD encryption (anti-DPI)",
        "encryption.algorithm": "Encryption algorithm: 'chacha' (default) or 'aes-gcm' (faster with AES-NI)",
        "encryption.key": "Encryption key (hex 32 bytes or password, empty = use PSK)",
        "stealth.padding_enabled": "Enable random padding (hides packet sizes; works with or without encryption)",
        "stealth.padding_min": "Minimum padding bytes (default: 0)",
        "stealth.padding_max": "Maximum padding bytes (default: 128, max 255 protocol limit)",
        "stealth.jitter_enabled": "Enable timing jitter (breaks timing patterns; works with or without encryption)",
        "stealth.jitter_min_ms": "Minimum jitter in ms (default: 5)",
        "stealth.jitter_max_ms": "Maximum jitter in ms (default: 20)",
        "tun.enabled": "Enable TUN mode",
        "tun.name": "TUN interface name",
        "tun.local": "Local IP address with CIDR (e.g., 10.200.0.1/30)",
        "tun.mtu": "TUN MTU (default: 1400)",
        "tun.routes": "Networks routed through TUN",
        "tun.streams": "Parallel TUN streams (default: 1)",
        "tun.forward_l2tp": "Auto-add iptables DNAT rules for L2TP/IPsec ports (500,4500,1701) on server",
        "tun.l2tp_ports": "List of UDP ports to auto-forward for L2TP/IPsec (default: [500, 4500, 1701])",
        "tun.l2tp_dest_ip": "Optional DNAT destination IP for L2TP/IPsec (empty = use tun.local IP)",
        "tcp_ports": "TCP port mappings ( [\"443\", \"4000=5000\", \"500-567\"])",
        "udp_ports": "UDP port mappings ( [\"500-567\", \"4500\"])",
        "cert_file": "Path to TLS certificate file (for tlsmux and wssmux)",
        "key_file": "Path to TLS private key file (for tlsmux and wssmux)",
        "edge_ip": "Optional: CDN edge IP for ws/wss (Direct only). Connect to this IP, Host/SNI from connect. Empty = disabled.",
    }
    
    if transport == "kcpmux":
        kcp_default = get_default_kcp_config(profile)
        comments.update({
            "kcp.nodelay": f"KCP NoDelay (default: {kcp_default['nodelay']})",
            "kcp.interval": f"KCP interval in ms (default: {kcp_default['interval']})",
            "kcp.resend": f"KCP resend (default: {kcp_default['resend']})",
            "kcp.nc": f"KCP NC (default: {kcp_default['nc']})",
            "kcp.sndwnd": f"KCP send window (default: {kcp_default['sndwnd']})",
            "kcp.rcvwnd": f"KCP receive window (default: {kcp_default['rcvwnd']})",
            "kcp.mtu": f"KCP MTU (default: {kcp_default['mtu']})",
        })
    if transport in ("rawsocket", "rawmux"):
        rs_default = get_default_rawsocket_config(profile)
        comments.update({
            "rawsocket.mtu": f"rawsocket MTU (default: {rs_default['mtu']})",
            "rawsocket.snd_wnd": f"rawsocket send window (default: {rs_default['snd_wnd']})",
            "rawsocket.rcv_wnd": f"rawsocket receive window (default: {rs_default['rcv_wnd']})",
            "rawsocket.data_shard": f"FEC data shards (default: {rs_default['data_shard']})",
            "rawsocket.parity_shard": f"FEC parity shards (default: {rs_default['parity_shard']})",
            "rawsocket.sock_buf": f"UDP buffer in bytes (default: {rs_default.get('sock_buf', RAWSOCKET_SOCK_BUF)} = 4MB)",
        })
    
    write_yaml_with_comments(config_path, yaml_data, comments)
    
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass
    
    return config_path

def create_client_config_file(cfg: dict) -> Path:
    """ساخت فایل کانفیگ YAML برای کلاینت"""
    if cfg.get("transport") == "l3":
        return create_l3_client_config_file(cfg)
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    tport = 0
    direct_mode = cfg.get('direct', False)
    
    if direct_mode:
        listen_addr = cfg.get('listen', '')
        if listen_addr and ':' in listen_addr:
            tport = listen_addr.split(':')[-1]
    else:
        paths = cfg.get('paths', [])
        if paths:
            addr = paths[0].get('addr', '')
            tport = addr.split(':')[-1] if ':' in addr else '0'
    
    if direct_mode and tport:
        config_path = NETRIX_CONFIG_DIR / f"client_direct_{tport}.yaml"
    elif tport and str(tport) != '0':
        config_path = NETRIX_CONFIG_DIR / f"client_{tport}.yaml"
    else:
        config_path = NETRIX_CONFIG_DIR / "client.yaml"
    
    profile = cfg.get('profile', 'balanced')
    paths = cfg.get('paths', [])
    
    yaml_data = {
        "mode": "client",
        "psk": cfg.get('psk', '')
    }
    
    if direct_mode:
        yaml_data["direct"] = True
        yaml_data["listen"] = cfg.get('listen', '')
        yaml_data["transport"] = cfg.get('transport', 'tcpmux')
        yaml_data["connection_pool"] = cfg.get('connection_pool', 8)
        
        transport = cfg.get('transport', 'tcpmux')
        if transport == "realitymux" and cfg.get('reality_sni') and cfg.get('reality_fingerprint'):
            yaml_data["reality"] = {
                "sni": cfg.get('reality_sni', 'cloudflare.com'),
                "fingerprint": cfg.get('reality_fingerprint', 'chrome')
            }
            if cfg.get('reality_short_id'):
                yaml_data["reality"]["short_id"] = cfg.get('reality_short_id')
            if cfg.get('reality_public_key'):
                yaml_data["reality"]["public_key"] = cfg.get('reality_public_key')
        
        if cfg.get("cert_file") and cfg.get("key_file"):
            yaml_data["cert_file"] = cfg["cert_file"]
            yaml_data["key_file"] = cfg["key_file"]
    
    yaml_data["profile"] = profile
    
    if paths and not direct_mode:
        yaml_data["paths"] = []
        for path in paths:
            path_transport = path.get('transport', 'tcpmux')
            path_data = {
                "transport": path_transport,
                "addr": path.get('addr', '')
            }
            _path_edge = (path.get('edge_ip') or '').strip()
            if _path_edge and path_transport in ('wsmux', 'wssmux'):
                path_data["edge_ip"] = _path_edge
            if 'connection_pool' in path:
                path_data["connection_pool"] = path['connection_pool']
            else:
                path_data["connection_pool"] = 8
            if path.get('retry_interval'):
                path_data["retry_interval"] = path['retry_interval']
            if path.get('dial_timeout'):
                path_data["dial_timeout"] = path['dial_timeout']
            if path.get('aggressive_pool'):
                path_data["aggressive_pool"] = path['aggressive_pool']
            if path_transport == "realitymux" and path.get('reality_sni') and path.get('reality_fingerprint'):
                path_data["reality"] = {
                    "sni": path.get('reality_sni', 'cloudflare.com'),
                    "fingerprint": path.get('reality_fingerprint', 'chrome')
                }
                if path.get('reality_short_id'):
                    path_data["reality"]["short_id"] = path.get('reality_short_id')
                if path.get('reality_public_key'):
                    path_data["reality"]["public_key"] = path.get('reality_public_key')
            yaml_data["paths"].append(path_data)
        
        main_transport = paths[0].get('transport', 'tcpmux')
    elif direct_mode:
        main_transport = cfg.get('transport', 'tcpmux')
    else:
        main_transport = 'tcpmux'
    
    smux_default = get_default_smux_config(profile)
    yaml_data["smux"] = {
        "keepalive": smux_default["keepalive"],
        "max_recv": smux_default["max_recv"],
        "max_stream": smux_default["max_stream"],
        "frame_size": smux_default["frame_size"],
        "version": smux_default["version"],
        "mux_con": cfg.get('mux_con', smux_default.get("mux_con", 8)) 
    }
    

    needs_kcp = any(p.get('transport') == 'kcpmux' for p in paths) or (direct_mode and main_transport == 'kcpmux')
    if needs_kcp:
        kcp_default = get_default_kcp_config(profile)
        yaml_data["kcp"] = {
            "nodelay": kcp_default["nodelay"],
            "interval": kcp_default["interval"],
            "resend": kcp_default["resend"],
            "nc": kcp_default["nc"],
            "sndwnd": kcp_default["sndwnd"],
            "rcvwnd": kcp_default["rcvwnd"],
            "mtu": kcp_default["mtu"]
        }
    needs_rawsocket = any(p.get('transport') in ('rawsocket', 'rawmux') for p in paths) or (direct_mode and main_transport in ('rawsocket', 'rawmux'))
    if needs_rawsocket:
        rs_default = get_default_rawsocket_config(profile)
        yaml_data["rawsocket"] = {
            "mtu": rs_default["mtu"],
            "snd_wnd": rs_default["snd_wnd"],
            "rcv_wnd": rs_default["rcv_wnd"],
            "data_shard": rs_default["data_shard"],
            "parity_shard": rs_default["parity_shard"],
            "sock_buf": rs_default.get("sock_buf", RAWSOCKET_SOCK_BUF),
        }
        if cfg.get("rawsocket_interface"):
            yaml_data["rawsocket"]["interface"] = cfg["rawsocket_interface"]
        if cfg.get("rawsocket_local_ip"):
            yaml_data["rawsocket"]["local_ip"] = cfg["rawsocket_local_ip"]
        if cfg.get("rawsocket_router_mac"):
            yaml_data["rawsocket"]["router_mac"] = cfg["rawsocket_router_mac"]
        if cfg.get("rawsocket_local_flags"):
            yaml_data["rawsocket"]["local_flags"] = cfg["rawsocket_local_flags"]
        if cfg.get("rawsocket_remote_flags"):
            yaml_data["rawsocket"]["remote_flags"] = cfg["rawsocket_remote_flags"]
        peer_ip = (cfg.get("rawsocket_peer_ip") or "").strip()
        if not peer_ip:
            candidates = set()
            for _p in (paths or []):
                try:
                    if (_p.get("transport") in ("rawsocket", "rawmux")) and _p.get("addr"):
                        _ip = _extract_ip_from_addr(str(_p.get("addr")))
                        if _ip:
                            candidates.add(_ip)
                except Exception:
                    continue
            if len(candidates) == 1:
                peer_ip = next(iter(candidates))
        if peer_ip:
            yaml_data["rawsocket"]["peer_ip"] = peer_ip

    advanced_default = get_default_advanced_config(main_transport)
    advanced_default.pop("stream_queue_size", None)
    yaml_data["advanced"] = {}
    for key, value in advanced_default.items():
        if key != "verbose":
            yaml_data["advanced"][key] = value
    
    
    if "tls_insecure_skip_verify" in cfg:
        yaml_data["advanced"]["tls_insecure_skip_verify"] = cfg["tls_insecure_skip_verify"]
    
    yaml_data["verbose"] = cfg.get("verbose", False)
    
    compression_cfg = cfg.get("compression_config", {})
    yaml_data["compression"] = {
        "enabled": compression_cfg.get("enabled", True),  
        "algorithm": compression_cfg.get("algorithm", "lz4"),  
        "level": compression_cfg.get("level", 0), 
        "min_size": compression_cfg.get("min_size", 1024),  
        "max_size": compression_cfg.get("max_size", 65536)  
    }
    
    yaml_data["encryption"] = {
        "enabled": cfg.get("encryption_enabled", False),
        "algorithm": cfg.get("encryption_algorithm", "chacha"),
        "key": cfg.get("encryption_key", "")
    }
    
    _pad_max = min(cfg.get("stealth_padding_max", 128), 255)
    _pad_min = min(cfg.get("stealth_padding_min", 0), 255)
    if _pad_min > _pad_max:
        _pad_min = _pad_max
    yaml_data["stealth"] = {
        "padding_enabled": cfg.get("stealth_padding", False),
        "padding_min": _pad_min,
        "padding_max": _pad_max,
        "jitter_enabled": cfg.get("stealth_jitter", False),
        "jitter_min_ms": cfg.get("stealth_jitter_min", 5),
        "jitter_max_ms": cfg.get("stealth_jitter_max", 20)
    }
    
    yaml_data["health_port"] = cfg.get('health_port', 19080)
    
    if "heartbeat" in cfg:
        yaml_data["heartbeat"] = cfg['heartbeat']
    
    if "buffer_pool_config" in cfg:
        buffer_config = cfg["buffer_pool_config"]
        if "buffer_pool_size" in buffer_config:
            yaml_data["advanced"]["buffer_pool_size"] = buffer_config["buffer_pool_size"]
        if "large_buffer_pool_size" in buffer_config:
            yaml_data["advanced"]["large_buffer_pool_size"] = buffer_config["large_buffer_pool_size"]
        if "udp_frame_pool_size" in buffer_config:
            yaml_data["advanced"]["udp_frame_pool_size"] = buffer_config["udp_frame_pool_size"]
        if "udp_data_slice_size" in buffer_config:
            yaml_data["advanced"]["udp_data_slice_size"] = buffer_config["udp_data_slice_size"]
    
    if cfg.get("anti_dpi_delay_ms", 0) > 0:
        yaml_data["advanced"]["anti_dpi_delay_ms"] = cfg.get("anti_dpi_delay_ms")
    
    tun_cfg = cfg.get("tun_config") or {}
    yaml_data["tun"] = {
        "enabled": tun_cfg.get("enabled", False),
        "name": tun_cfg.get("name", "netrix0"),
        "local": tun_cfg.get("local", "10.200.0.2/30"),
        "mtu": tun_cfg.get("mtu", 1400),
        "routes": tun_cfg.get("routes", []),
        "streams": tun_cfg.get("streams", 1)
    }
    
    if cfg.get("proxy_protocol_enabled", False):
        proxy_config = {
            "enabled": True,
            "version": cfg.get("proxy_protocol_version", "v1")
        }
        proxy_ports = cfg.get("proxy_protocol_ports", [])
        if proxy_ports:
            proxy_config["port_list"] = proxy_ports
        yaml_data["proxy_protocol"] = proxy_config

    comments = {
        "profile": f"Performance profile (default: balanced)",
        "smux.keepalive": f"Keepalive interval in seconds (default: {smux_default['keepalive']})",
        "smux.max_recv": f"Max receive buffer in bytes (default: {smux_default['max_recv']} = 4MB)",
        "smux.max_stream": f"Max stream buffer in bytes (default: {smux_default['max_stream']} = 2MB)",
        "smux.frame_size": f"Frame size in bytes (default: {smux_default['frame_size']} = 32KB)",
        "smux.version": f"SMUX version (default: {smux_default['version']})",
        "smux.mux_con": f"Number of multiplexed connections (default: from profile - balanced=8, aggressive=16, latency=4, cpu-efficient=4)",
        "advanced.tcp_nodelay": f"TCP NoDelay (default: true)",
        "advanced.tcp_keepalive": f"TCP KeepAlive in seconds (default: 15 - تشخیص سریع‌تر dead connections)",
        "advanced.tcp_read_buffer": f"TCP read buffer in bytes (default: 8388608 = 8MB)",
        "advanced.tcp_write_buffer": f"TCP write buffer in bytes (default: 8388608 = 8MB)",
        "advanced.cleanup_interval": f"Cleanup interval in seconds (default: 60)",
        "advanced.session_timeout": f"Session timeout in seconds (default: 180 = 3 minutes - فقط برای sessions بدون heartbeat)",
        "advanced.connection_timeout": f"Connection timeout in seconds (default: 600 = 10 minutes)",
        "advanced.stream_timeout": f"Stream max lifetime in seconds (default: 21600 = 6 hours)",
        "advanced.stream_idle_timeout": f"Stream idle timeout in seconds (default: 600 = 10 minutes)",
        "advanced.max_udp_flows": f"Max UDP flows (default: 5000)",
        "advanced.udp_flow_timeout": f"UDP flow timeout in seconds (default: 600 = 10 minutes)",
        "advanced.tls_insecure_skip_verify": f"Skip TLS certificate verification (default: false - secure by default, can be enabled for self-signed certs)",
        "advanced.buffer_pool_size": f"Buffer pool size in bytes (default: {DEFAULT_BUFFER_POOL_SIZE})",
        "advanced.large_buffer_pool_size": f"Large buffer pool size in bytes (default: {DEFAULT_LARGE_BUFFER_POOL_SIZE})",
        "advanced.udp_frame_pool_size": f"UDP frame pool size in bytes (default: {DEFAULT_UDP_FRAME_POOL_SIZE})",
        "advanced.udp_data_slice_size": f"UDP slice size in bytes (default: {DEFAULT_UDP_SLICE_SIZE})",
        "advanced.anti_dpi_delay_ms": "Anti-DPI delay in ms after connection (0=disabled, 50-500, applied on dialer; Direct=server, Reverse=client)",
        "heartbeat": f"Heartbeat interval in seconds (default: {DEFAULT_HEARTBEAT})",
        "verbose": f"Verbose logging (default: false)",
        "compression.enabled": "Enable compression (default: true)",
        "compression.algorithm": "Compression algorithm: lz4, zstd, or snappy",
        "compression.level": "Compression level",
        "compression.min_size": "Minimum size to compress in bytes (default: 1024)",
        "compression.max_size": "Maximum frame size in bytes (default: 65536)",
        "encryption.enabled": "Enable AEAD encryption (anti-DPI)",
        "encryption.algorithm": "Encryption algorithm: 'chacha' (default) or 'aes-gcm' (faster with AES-NI)",
        "encryption.key": "Encryption key (hex 32 bytes or password, empty = use PSK)",
        "stealth.padding_enabled": "Enable random padding (hides packet sizes; works with or without encryption)",
        "stealth.padding_min": "Minimum padding bytes (default: 0)",
        "stealth.padding_max": "Maximum padding bytes (default: 128, max 255 protocol limit)",
        "stealth.jitter_enabled": "Enable timing jitter (breaks timing patterns; works with or without encryption)",
        "stealth.jitter_min_ms": "Minimum jitter in ms (default: 5)",
        "stealth.jitter_max_ms": "Maximum jitter in ms (default: 20)",
        "tun.enabled": "Enable TUN mode",
        "tun.name": "TUN interface name",
        "tun.local": "Local IP address with CIDR (e.g., 10.200.0.2/30)",
        "tun.mtu": "TUN MTU (default: 1400)",
        "tun.routes": "Networks routed through TUN",
        "tun.streams": "Parallel TUN streams (default: 1)",
        "proxy_protocol.enabled": "Enable PROXY Protocol",
        "proxy_protocol.version": "PROXY Protocol version (v1 or v2)",
    }
    
    if any(p.get('transport') == 'kcpmux' for p in paths):
        kcp_default = get_default_kcp_config(profile)
        comments.update({
            "kcp.nodelay": f"KCP NoDelay (default: {kcp_default['nodelay']})",
            "kcp.interval": f"KCP interval in ms (default: {kcp_default['interval']})",
            "kcp.resend": f"KCP resend (default: {kcp_default['resend']})",
            "kcp.nc": f"KCP NC (default: {kcp_default['nc']})",
            "kcp.sndwnd": f"KCP send window (default: {kcp_default['sndwnd']})",
            "kcp.rcvwnd": f"KCP receive window (default: {kcp_default['rcvwnd']})",
            "kcp.mtu": f"KCP MTU (default: {kcp_default['mtu']})",
        })
    
    write_yaml_with_comments(config_path, yaml_data, comments)
    
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass
    
    return config_path

# ========== Tunnel Management ==========
def ensure_netrix_available():
    """بررسی وجود باینری netrix"""
    if os.path.exists(NETRIX_BINARY):
        return NETRIX_BINARY
    netrix_path = which("netrix")
    if netrix_path:
        return netrix_path
    c_err("netrix binary not found!")
    c_warn(f"Please install netrix to {NETRIX_BINARY} or add to PATH")
    return None

def get_service_status(config_path: Path) -> Optional[str]:
    """دریافت وضعیت systemd service"""
    service_name = f"netrix-{config_path.stem}"
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return "inactive"
    except KeyboardInterrupt:
        exit_script()
    except subprocess.TimeoutExpired:
        return "unknown"
    except Exception:
        return None

def get_service_pid(config_path: Path) -> Optional[int]:
    """دریافت PID از systemd service"""
    service_name = f"netrix-{config_path.stem}"
    try:
        result = subprocess.run(
            ["systemctl", "show", "--property=MainPID", "--value", service_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip())
            if pid > 0:
                return pid
    except KeyboardInterrupt:
        exit_script()
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        pass
    return None

def list_tunnels() -> List[Dict[str,Any]]:
    """لیست تمام تانل‌ها از فایل‌های YAML"""
    items = []
    
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config_files_new = list(NETRIX_CONFIG_DIR.glob("server_*.yaml"))
    config_files_old = list(ROOT_DIR.glob("server*.yaml"))
    all_config_files = list(set(config_files_new + config_files_old))
    
    for config_file in all_config_files:
        try:
            cfg = parse_yaml_config(config_file)
            if not cfg or cfg.get('mode') != 'server':
                continue
            
            transport = cfg.get('transport', 'tcpmux')
            direct_mode = cfg.get('direct', False)
            
            if transport == "l3":
                sec_cfg = cfg.get("l3", {}) or {}
                tun_cfg = cfg.get('tun', {}) or {}
                carrier = (sec_cfg.get("carrier") or "raw").strip().lower()
                if carrier == "udp":
                    summary = (
                        f"server L3 udp {sec_cfg.get('listen_ip', '?')}:{sec_cfg.get('listen_port', '?')} -> "
                        f"{sec_cfg.get('dst_ip', '?')}:{sec_cfg.get('dst_port', '?')} tun={tun_cfg.get('local', '?')}"
                    )
                    tport = str(sec_cfg.get("listen_port", "l3"))
                elif carrier == "pcap":
                    summary = (
                        f"server L3 pcap {sec_cfg.get('listen_ip', '?')}:{sec_cfg.get('listen_port', '?')} -> "
                        f"{sec_cfg.get('dst_ip', '?')}:{sec_cfg.get('dst_port', '?')} tun={tun_cfg.get('local', '?')}"
                    )
                    tport = str(sec_cfg.get("listen_port", "l3"))
                elif carrier == "icmp":
                    summary = (
                        f"server L3 icmp {sec_cfg.get('listen_ip', '?')} -> {sec_cfg.get('dst_ip', '?')} "
                        f"tun={tun_cfg.get('local', '?')} icmp={sec_cfg.get('icmp_type', '?')}/{sec_cfg.get('icmp_code', '?')}"
                    )
                    tport = "icmp"
                elif carrier == "tcp":
                    summary = (
                        f"server L3 tcp {sec_cfg.get('listen_ip', '?')}:{sec_cfg.get('listen_port', '?')} -> "
                        f"{sec_cfg.get('dst_ip', '?')}:{sec_cfg.get('dst_port', '?')} tun={tun_cfg.get('local', '?')}"
                    )
                    tport = str(sec_cfg.get("listen_port", "l3"))
                else:
                    summary = f"server L3 raw {sec_cfg.get('listen_ip','?')} -> {sec_cfg.get('dst_ip','?')} tun={tun_cfg.get('local','?')}"
                    tport = "l3"
            elif direct_mode:
                connect = cfg.get('connect', '')
                tport = connect.split(':')[-1] if ':' in connect else ''
                target_ip = connect.rsplit(':', 1)[0] if ':' in connect else connect
                summary = f"server DIRECT → {target_ip}:{tport} ({transport})"
            else:
                listen = cfg.get('listen', '')
                tport = listen.split(':')[-1] if ':' in listen else ''
                summary = f"server port={tport} transport={transport}"
            
            status = get_service_status(config_file)
            alive = (status == "active")
            pid = get_service_pid(config_file) if alive else None
            
            items.append({
                "config_path": config_file,
                "mode": "server",
                "tport": tport,
                "transport": transport,
                "direct": direct_mode,
                "summary": summary,
                "pid": pid,
                "alive": alive,
                "cfg": cfg
            })
        except KeyboardInterrupt:
            exit_script()
        except Exception:
            continue
    
    client_files_new = list(NETRIX_CONFIG_DIR.glob("client*.yaml"))
    client_files_old = list(ROOT_DIR.glob("client*.yaml"))
    all_client_files = list(set(client_files_new + client_files_old))
    
    for config_file in all_client_files:
        try:
            cfg = parse_yaml_config(config_file)
            if not cfg or cfg.get('mode') != 'client':
                continue
            
            direct_mode = cfg.get('direct', False)
            
            transport = cfg.get('transport', 'tcpmux')
            if transport == "l3":
                sec_cfg = cfg.get("l3", {}) or {}
                tun_cfg = cfg.get('tun', {}) or {}
                carrier = (sec_cfg.get("carrier") or "raw").strip().lower()
                if carrier == "udp":
                    summary = (
                        f"client L3 udp {sec_cfg.get('listen_ip', '?')}:{sec_cfg.get('listen_port', '?')} -> "
                        f"{sec_cfg.get('dst_ip', '?')}:{sec_cfg.get('dst_port', '?')} tun={tun_cfg.get('local', '?')}"
                    )
                elif carrier == "pcap":
                    summary = (
                        f"client L3 pcap {sec_cfg.get('listen_ip', '?')}:{sec_cfg.get('listen_port', '?')} -> "
                        f"{sec_cfg.get('dst_ip', '?')}:{sec_cfg.get('dst_port', '?')} tun={tun_cfg.get('local', '?')}"
                    )
                elif carrier == "icmp":
                    summary = (
                        f"client L3 icmp {sec_cfg.get('listen_ip', '?')} -> {sec_cfg.get('dst_ip', '?')} "
                        f"tun={tun_cfg.get('local', '?')} icmp={sec_cfg.get('icmp_type', '?')}/{sec_cfg.get('icmp_code', '?')}"
                    )
                elif carrier == "tcp":
                    summary = (
                        f"client L3 tcp {sec_cfg.get('listen_ip', '?')}:{sec_cfg.get('listen_port', '?')} -> "
                        f"{sec_cfg.get('dst_ip', '?')}:{sec_cfg.get('dst_port', '?')} tun={tun_cfg.get('local', '?')}"
                    )
                else:
                    summary = f"client L3 raw {sec_cfg.get('listen_ip','?')} -> {sec_cfg.get('dst_ip','?')} tun={tun_cfg.get('local','?')}"
            elif direct_mode:
                listen = cfg.get('listen', '')
                tport = listen.split(':')[-1] if ':' in listen else ''
                summary = f"client DIRECT listen={tport} ({transport})"
            else:
                paths = cfg.get('paths', [])
                if paths:
                    first_path = paths[0]
                    addr = first_path.get('addr', 'unknown')
                    transport = first_path.get('transport', 'tcpmux')
                    connection_pool = first_path.get('connection_pool', 1)
                    summary = f"client {transport}://{addr} ({connection_pool}x)"
                else:
                    summary = "client (unknown)"
            
            status = get_service_status(config_file)
            alive = (status == "active")
            pid = get_service_pid(config_file) if alive else None
            
            items.append({
                "config_path": config_file,
                "mode": "client",
                "direct": direct_mode,
                "summary": summary,
                "pid": pid,
                "alive": alive,
                "cfg": cfg
            })
        except KeyboardInterrupt:
            exit_script()
        except Exception:
            continue
    
    return items

def run_tunnel(config_path: Path):
    """اجرای تانل از طریق systemd service"""
    if not create_systemd_service_for_tunnel(config_path):
        return False
    
    service_name = f"netrix-{config_path.stem}"
    try:
        subprocess.run(["systemctl", "enable", service_name], check=False, timeout=5)
        try:
            result = subprocess.run(
                ["systemctl", "start", service_name],
                capture_output=True,
                text=True,
                timeout=30 
            )
            if result.returncode == 0:
                return True
            else:
                c_err(f"Failed to start service: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            c_err("Failed to start service: timeout (service may be hanging)")

            try:
                check_result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if check_result.returncode == 0 and check_result.stdout.strip() == "active":
                    c_warn("Service is actually running (start command timed out but service is active)")
                    return True
            except:
                pass
            return False
    except Exception as e:
        c_err(f"Failed to start tunnel: {e}")
        return False

def stop_tunnel(config_path: Path) -> bool:
    """توقف تانل از طریق systemd service"""
    service_name = f"netrix-{config_path.stem}"
    try:
        result = subprocess.run(
            ["systemctl", "stop", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        c_warn(f"  ⚠️  Service stop timeout (forcing kill)...")
        try:
            subprocess.run(["systemctl", "kill", "--signal=SIGKILL", service_name], timeout=3, check=False)
            return True
        except:
            return False
    except Exception:
        return False

def restart_tunnel(config_path: Path) -> bool:
    """ریستارت تانل از طریق systemd service - با stop/start جداگانه برای cleanup کامل"""
    service_name = f"netrix-{config_path.stem}"
    try:
        subprocess.run(
            ["systemctl", "daemon-reload"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        stop_result = subprocess.run(
            ["systemctl", "stop", service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        time.sleep(1)
        
        check_result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        start_result = subprocess.run(
            ["systemctl", "start", service_name],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if start_result.returncode == 0:
            time.sleep(0.5)
            verify_result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=3
            )
            if verify_result.returncode == 0 and verify_result.stdout.strip() == "active":
                return True
            else:
                return False
        else:
            try:
                check_result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if check_result.returncode == 0 and check_result.stdout.strip() == "active":
                    return True
            except:
                pass
            return False
    except subprocess.TimeoutExpired:
        c_warn(f"  ⚠️  Restart timeout - checking service status...")

        try:
            check_result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=3
            )
            if check_result.returncode == 0 and check_result.stdout.strip() == "active":
                c_warn("  ⚠️  Service is running (restart completed despite timeout)")
                return True
        except:
            pass
        return False
    except Exception:
        return False

# ========== RawSocket iptables helpers ==========
def _rawsocket_listen_port_from_config(config_path: Path) -> Optional[str]:
    """اگر کانفیگ با ترنسپورت rawsocket/rawmux روی پورتی listen کند (Direct server)، آن پورت را برمی‌گرداند."""
    cfg = parse_yaml_config(config_path)
    if not cfg:
        return None
    transport = (cfg.get("transport") or "").lower()
    if transport not in ("rawsocket", "rawmux"):
        return None
    listen = (cfg.get("listen_addr") or cfg.get("listen") or "").strip()
    if not listen or ":" not in listen:
        return None
    port = listen.rsplit(":", 1)[-1].strip()
    if port.isdigit() and 1 <= int(port) <= 65535:
        return port
    return None

def _rawsocket_dial_peer_from_config(config_path: Path) -> Optional[tuple]:
    """اگر این کانفیگ با rawsocket به یک ریموت وصل می‌شود، (ip, port) ریموت را برمی‌گرداند.
    - Reverse client (mode=client): اولین path با transport rawsocket/rawmux
    - Direct server (mode=server, direct): connect"""
    cfg = parse_yaml_config(config_path)
    if not cfg:
        return None
    mode = (cfg.get("mode") or "").lower()
    if mode == "client":
        paths = cfg.get("paths") or []
        for p in paths:
            pt = (p.get("transport") or "").lower()
            if pt not in ("rawsocket", "rawmux"):
                continue
            addr = (p.get("addr") or "").strip()
            if addr and ":" in addr:
                host, port_s = addr.rsplit(":", 1)
                host, port_s = host.strip(), port_s.strip()
                if host and port_s.isdigit() and 1 <= int(port_s) <= 65535:
                    return (host, port_s)
        return None
    transport = (cfg.get("transport") or "").lower()
    if transport not in ("rawsocket", "rawmux"):
        return None
    direct = bool(cfg.get("direct"))
    if mode == "server" and direct:
        connect = (cfg.get("connect") or "").strip()
        if connect and ":" in connect:
            host, port_s = connect.rsplit(":", 1)
            host, port_s = host.strip(), port_s.strip()
            if host and port_s.isdigit() and 1 <= int(port_s) <= 65535:
                return (host, port_s)
    return None

# ========== System Service ==========
def create_systemd_service_for_tunnel(config_path: Path) -> bool:
    """ساخت systemd service برای یک تانل خاص"""
    netrix_bin = ensure_netrix_available()
    if not netrix_bin:
        return False
    
    service_name = f"netrix-{config_path.stem}"
    service_path = Path(f"/etc/systemd/system/{service_name}.service")
    
    rawsocket_port = _rawsocket_listen_port_from_config(config_path)
    dial_peer = _rawsocket_dial_peer_from_config(config_path)
    exec_start_pre = ""
    exec_stop_post = ""
    pre_cmds = []
    post_cmds = []
    if rawsocket_port:
        for d, a in [("PREROUTING", f"-p tcp --dport {rawsocket_port} -j NOTRACK"), ("OUTPUT", f"-p tcp --sport {rawsocket_port} -j NOTRACK")]:
            pre_cmds.append(f"iptables -t raw -D {d} {a} 2>/dev/null; iptables -t raw -A {d} {a}")
        pre_cmds.append(f"iptables -t mangle -D OUTPUT -p tcp --sport {rawsocket_port} --tcp-flags RST RST -j DROP 2>/dev/null; iptables -t mangle -A OUTPUT -p tcp --sport {rawsocket_port} --tcp-flags RST RST -j DROP")
        pre_cmds.append(f"iptables -t mangle -D PREROUTING -p tcp --dport {rawsocket_port} --tcp-flags RST RST -j DROP 2>/dev/null; iptables -t mangle -A PREROUTING -p tcp --dport {rawsocket_port} --tcp-flags RST RST -j DROP")
        post_cmds.append(f"iptables -t raw -D PREROUTING -p tcp --dport {rawsocket_port} -j NOTRACK 2>/dev/null; iptables -t raw -D OUTPUT -p tcp --sport {rawsocket_port} -j NOTRACK 2>/dev/null; iptables -t mangle -D OUTPUT -p tcp --sport {rawsocket_port} --tcp-flags RST RST -j DROP 2>/dev/null; iptables -t mangle -D PREROUTING -p tcp --dport {rawsocket_port} --tcp-flags RST RST -j DROP 2>/dev/null")
    if dial_peer:
        peer_ip, peer_port = dial_peer
        pre_cmds.append(f"iptables -t raw -D OUTPUT -p tcp -d {peer_ip} --dport {peer_port} -j NOTRACK 2>/dev/null; iptables -t raw -A OUTPUT -p tcp -d {peer_ip} --dport {peer_port} -j NOTRACK")
        pre_cmds.append(f"iptables -t raw -D PREROUTING -p tcp -s {peer_ip} --sport {peer_port} -j NOTRACK 2>/dev/null; iptables -t raw -A PREROUTING -p tcp -s {peer_ip} --sport {peer_port} -j NOTRACK")
        pre_cmds.append(f"iptables -t mangle -D OUTPUT -p tcp -d {peer_ip} --dport {peer_port} --tcp-flags RST RST -j DROP 2>/dev/null; iptables -t mangle -A OUTPUT -p tcp -d {peer_ip} --dport {peer_port} --tcp-flags RST RST -j DROP")
        pre_cmds.append(f"iptables -t mangle -D PREROUTING -p tcp -s {peer_ip} --sport {peer_port} --tcp-flags RST RST -j DROP 2>/dev/null; iptables -t mangle -A PREROUTING -p tcp -s {peer_ip} --sport {peer_port} --tcp-flags RST RST -j DROP")
        post_cmds.append(f"iptables -t raw -D OUTPUT -p tcp -d {peer_ip} --dport {peer_port} -j NOTRACK 2>/dev/null; iptables -t raw -D PREROUTING -p tcp -s {peer_ip} --sport {peer_port} -j NOTRACK 2>/dev/null; iptables -t mangle -D OUTPUT -p tcp -d {peer_ip} --dport {peer_port} --tcp-flags RST RST -j DROP 2>/dev/null; iptables -t mangle -D PREROUTING -p tcp -s {peer_ip} --sport {peer_port} --tcp-flags RST RST -j DROP 2>/dev/null")
    if pre_cmds:
        exec_start_pre = "ExecStartPre=-/bin/sh -c '" + "; ".join(pre_cmds) + "'\n"
    if post_cmds:
        exec_stop_post = "ExecStopPost=-/bin/sh -c '" + "; ".join(post_cmds) + "'\n"
    
    service_content = f"""[Unit]
Description=Netrix Tunnel - {config_path.name}
After=network.target

[Service]
Type=simple
{exec_start_pre}{exec_stop_post}ExecStart={netrix_bin} -config {config_path}
Restart=always
RestartSec=2
TimeoutStartSec=10
TimeoutStopSec=15
KillMode=mixed
KillSignal=SIGTERM
FinalKillSignal=SIGKILL
SendSIGKILL=yes
User=root
LimitNOFILE=1048576
LimitNPROC=1048576
LimitCORE=infinity
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        os.chmod(service_path, 0o644)
        try:
            subprocess.run(
                ["systemctl", "daemon-reload"],
                check=False,
                timeout=5,
                capture_output=True
            )
        except subprocess.TimeoutExpired:
            c_warn("  ⚠️  daemon-reload timeout (continuing anyway)")
        
        return True
    except Exception as e:
        c_err(f"Failed to create service: {e}")
        return False

def enable_service_for_tunnel(config_path: Path) -> bool:
    """فعال کردن systemd service برای تانل"""
    service_name = f"netrix-{config_path.stem}"
    try:
        subprocess.run(["systemctl", "enable", service_name], check=False)
        return True
    except Exception:
        return False

def disable_service_for_tunnel(config_path: Path) -> bool:
    """غیرفعال کردن systemd service برای تانل"""
    service_name = f"netrix-{config_path.stem}"
    try:
        subprocess.run(["systemctl", "disable", service_name], check=False)
        return True
    except Exception:
        return False

def cleanup_iptables_rules(config_path: Path) -> bool:
    """
    پاک کردن iptables rules، routes و IP address برای تانل (L2TP forwarding + rawsocket)
    
    ⚠️ مهم: این تابع فقط chain ها و rules مربوط به خود tunnel را پاک می‌کند.
    chain ها و rules دیگری که کاربر دستی روی سرور تنظیم کرده، دست‌نخورده باقی می‌مانند.
    
    - rawsocket: حذف قوانین NOTRACK و RST drop
    - L2TP: chain هایی با prefix 'NX_L2TP_PRE_' و 'NX_L2TP_POST_'
    """
    try:
        cfg = parse_yaml_config(config_path)
        if not cfg:
            return True

        rawsocket_port = _rawsocket_listen_port_from_config(config_path)
        if rawsocket_port:
            for args in [
                ["iptables", "-t", "raw", "-D", "PREROUTING", "-p", "tcp", "--dport", rawsocket_port, "-j", "NOTRACK"],
                ["iptables", "-t", "raw", "-D", "OUTPUT", "-p", "tcp", "--sport", rawsocket_port, "-j", "NOTRACK"],
                ["iptables", "-t", "mangle", "-D", "OUTPUT", "-p", "tcp", "--sport", rawsocket_port, "--tcp-flags", "RST", "RST", "-j", "DROP"],
                ["iptables", "-t", "mangle", "-D", "PREROUTING", "-p", "tcp", "--dport", rawsocket_port, "--tcp-flags", "RST", "RST", "-j", "DROP"],
            ]:
                try:
                    subprocess.run(args, capture_output=True, text=True, timeout=5)
                except Exception:
                    pass
        dial_peer = _rawsocket_dial_peer_from_config(config_path)
        if dial_peer:
            peer_ip, peer_port = dial_peer
            for args in [
                ["iptables", "-t", "raw", "-D", "OUTPUT", "-p", "tcp", "-d", peer_ip, "--dport", peer_port, "-j", "NOTRACK"],
                ["iptables", "-t", "raw", "-D", "PREROUTING", "-p", "tcp", "-s", peer_ip, "--sport", peer_port, "-j", "NOTRACK"],
                ["iptables", "-t", "mangle", "-D", "OUTPUT", "-p", "tcp", "-d", peer_ip, "--dport", peer_port, "--tcp-flags", "RST", "RST", "-j", "DROP"],
                ["iptables", "-t", "mangle", "-D", "PREROUTING", "-p", "tcp", "-s", peer_ip, "--sport", peer_port, "--tcp-flags", "RST", "RST", "-j", "DROP"],
            ]:
                try:
                    subprocess.run(args, capture_output=True, text=True, timeout=5)
                except Exception:
                    pass

        tun_cfg = cfg.get("tun", {})
        if not tun_cfg.get("enabled", False):
            return True 
        
        tun_name = tun_cfg.get("name", "netrix0").strip()
        if not tun_name:
            tun_name = "netrix0"
        
        routes = tun_cfg.get("routes", [])
        for route in routes:
            try:
                result = subprocess.run(
                    ["ip", "route", "del", route, "dev", tun_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            except Exception:
                pass 
        
        local_ip = tun_cfg.get("local", "")
        if local_ip:
            try:
                result = subprocess.run(
                    ["ip", "addr", "del", local_ip, "dev", tun_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            except Exception:
                pass
        
        try:
            subprocess.run(
                ["ip", "link", "set", "dev", tun_name, "down"],
                capture_output=True,
                text=True,
                timeout=5
            )
        except Exception:
            pass
        
        try:
            result = subprocess.run(
                ["iptables-save", "-t", "mangle"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if f"-o {tun_name}" in line and "TCPMSS" in line and "--set-mss" in line:
                        pass  
        except Exception:
            pass 

        if tun_cfg.get("forward_l2tp", False):
            safe_name = ""
            for c in tun_name:
                if ('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9') or c == '_':
                    safe_name += c
                else:
                    safe_name += '_'
            
            safe_name = safe_name.strip()
            if not safe_name:
                safe_name = "netrix0"

            hash_input = f"l2tp:{safe_name}"
            hash_bytes = hashlib.sha256(hash_input.encode()).digest()
            suffix = hash_bytes.hex()[:6]
            
            if len(safe_name) > 10:
                safe_name = safe_name[:10]
            
            pre_chain = f"NX_L2TP_PRE_{safe_name}_{suffix}"
            post_chain = f"NX_L2TP_POST_{safe_name}_{suffix}"
            
            for chain in [pre_chain, post_chain]:
                for from_chain in ["PREROUTING", "POSTROUTING"]:

                    for _ in range(5):
                        result = subprocess.run(
                            ["iptables", "-t", "nat", "-D", from_chain, "-j", chain],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode != 0:
                            break
            
            for chain in [pre_chain, post_chain]:
                subprocess.run(
                    ["iptables", "-t", "nat", "-F", chain],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                subprocess.run(
                    ["iptables", "-t", "nat", "-X", chain],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
        
        return True
    except Exception as e:

        if "Permission denied" in str(e) or "Operation not permitted" in str(e):
            print(f"  ⚠️  cleanup warning: {e}")
        return True

def delete_service_for_tunnel(config_path: Path) -> bool:
    """حذف systemd service برای تانل"""
    service_name = f"netrix-{config_path.stem}"
    service_path = Path(f"/etc/systemd/system/{service_name}.service")
    
    try:
        try:
            subprocess.run(
                ["systemctl", "stop", service_name],
                check=False,
                timeout=5,
                capture_output=True
            )
        except subprocess.TimeoutExpired:
            subprocess.run(["systemctl", "kill", "--signal=SIGKILL", service_name], timeout=3, check=False)
        
        try:
            subprocess.run(
                ["systemctl", "disable", service_name],
                check=False,
                timeout=5,
                capture_output=True
            )
        except subprocess.TimeoutExpired:
            pass  
        
        if service_path.exists():
            service_path.unlink()
        
        try:
            subprocess.run(
                ["systemctl", "daemon-reload"],
                check=False,
                timeout=5,
                capture_output=True
            )
        except subprocess.TimeoutExpired:
            pass  
        
        return True
    except Exception:
        return False

# ========== Menus ==========
def start_configure_menu():
    """Create/configure a new tunnel."""
    while True:
        clear()
        _brand_box("TUNNEL WIZARD", "", None, accent=FG_CYAN)
        print()
        _menu_line("1", "Iran Server", "Create or update the server-side tunnel profile", accent=FG_GREEN)
        _menu_line("2", "Kharej Client", "Create or update the Kharej-side client profile", accent=FG_BLUE)
        print()
        _menu_line("0", "Back", accent=FG_WHITE)
        print()
        try:
            choice = input(_input_prompt("Choose a side")).strip()
        except KeyboardInterrupt:
            exit_script()

        if choice == "0":
            return
        elif choice == "1":
            try:
                create_server_tunnel()
                return
            except UserCancelled:
                exit_script()
        elif choice == "2":
            try:
                create_client_tunnel()
                return
            except UserCancelled:
                exit_script()
        else:
            c_err("Invalid choice.")
            pause()

def create_server_tunnel():
    """ساخت تانل سرور (Iran)"""
    try:

        if not ensure_netrix_available():
            clear()
            print(f"{BOLD}{FG_RED}╔══════════════════════════════════════════════════════════╗{RESET}")
            print(f"                            {BOLD}Core Not Installed{RESET}                  ")
            print(f"{BOLD}{FG_RED}╚══════════════════════════════════════════════════════════╝{RESET}")
            print()
            c_err("Netrix core is not installed!")
            print(f"\n  {FG_YELLOW}You need to install the core first.{RESET}")
            print(f"  {FG_CYAN}Go to: Main Menu → Option 6 (Install/Update Core){RESET}\n")
            if ask_yesno(f"  {BOLD}Do you want to install the core now?{RESET}", default=True):
                install_netrix_core()
                if ensure_netrix_available():
                    c_ok("Core installed successfully! Continuing...")
                else:
                    c_err("Core installation failed!")
                    pause()
                    return
            else:
                pause()
                return
        
        _wizard_intro("IRAN SERVER", "")
        
        transport = ask_transport(include_l3=True)
        if transport == "l3":
            create_server_l3_tunnel()
            return
        direct_mode = ask_connection_mode_for_transport(transport, server_side=True)
        
        reality_sni = ""
        reality_fingerprint = ""
        if transport == "realitymux" and direct_mode:
            print(f"\n  {BOLD}🎭 REALITY Configuration:{RESET}")
                                                            
            print(f"\n  {BOLD}SNI Target:{RESET}")
            print(f"  {FG_CYAN}1){RESET} {FG_WHITE}cloudflare.com{RESET} (Recommended - most common)")
            print(f"  {FG_CYAN}2){RESET} {FG_WHITE}google.com{RESET}")
            print(f"  {FG_CYAN}3){RESET} {FG_WHITE}microsoft.com{RESET}")
            print(f"  {FG_CYAN}4){RESET} {FG_WHITE}apple.com{RESET}")
            print(f"  {FG_CYAN}5){RESET} {FG_YELLOW}random{RESET} (Changes per connection - maximum stealth)")
            print(f"  {FG_CYAN}6){RESET} {FG_YELLOW}Custom{RESET}")
            sni_choice = ask_int(f"  {BOLD}Select SNI target:{RESET}", min_=1, max_=6, default=5) 
            sni_options = {1: "cloudflare.com", 2: "google.com", 3: "microsoft.com", 4: "apple.com", 5: "random"}
            if sni_choice == 6:
                reality_sni = ask_nonempty(f"  {BOLD}Enter custom SNI:{RESET}")
            else:
                reality_sni = sni_options[sni_choice]
            
            print(f"\n  {BOLD}TLS Fingerprint:{RESET}")
            print(f"  {FG_WHITE}Select which browser's TLS fingerprint to mimic:{RESET}")
            print(f"  {FG_CYAN}1){RESET} {FG_WHITE}Chrome{RESET} (Recommended - most common)")
            print(f"  {FG_CYAN}2){RESET} {FG_WHITE}Firefox{RESET}")
            print(f"  {FG_CYAN}3){RESET} {FG_WHITE}Safari{RESET}")
            print(f"  {FG_CYAN}4){RESET} {FG_WHITE}Edge{RESET}")
            print(f"  {FG_CYAN}5){RESET} {FG_WHITE}iOS{RESET}")
            print(f"  {FG_CYAN}6){RESET} {FG_WHITE}Android{RESET}")
            print(f"  {FG_CYAN}7){RESET} {FG_YELLOW}random{RESET} (Changes per connection - maximum stealth)")
            fingerprint_choice = ask_int(f"  {BOLD}Select fingerprint:{RESET}", min_=1, max_=7, default=7)
            fingerprint_options = {1: "chrome", 2: "firefox", 3: "safari", 4: "edge", 5: "ios", 6: "android", 7: "random"}
            reality_fingerprint = fingerprint_options[fingerprint_choice]
            
            c_ok(f"  ✅ REALITY configured: SNI={reality_sni}, Fingerprint={reality_fingerprint}")
        elif transport == "realitymux" and not direct_mode:
            print(f"\n  {BOLD}🎭 REALITY Configuration:{RESET}")
            print(f"  {FG_CYAN}Mode:{RESET} {FG_WHITE}Server will listen and accept REALITY connections{RESET}")
            print(f"  {FG_WHITE}Note: Server accepts any SNI from clients (no configuration needed){RESET}")
            print(f"  {FG_WHITE}Clients will configure their own SNI and fingerprint settings{RESET}")
            c_ok(f"  ✅ REALITY server will accept connections with any SNI")
        
        print(f"\n  {BOLD}{FG_CYAN}Server Configuration:{RESET}")
        
        use_ipv6 = False
        if is_ipv6_available():
            print(f"  {FG_CYAN}IPv6 available{RESET}")
            pass
            use_ipv6 = ask_yesno(f"  {BOLD}Enable IPv6 support?{RESET}", default=False)
        else:
            print(f"  {FG_YELLOW}IPv6 unavailable{RESET}")
        
        listen_addr = ""
        connect_addr = ""
        edge_ip = ""
        tport = 0
        connection_pool = 8  
        mux_con = 8 
        
        if direct_mode:
            print(f"\n  {BOLD}{FG_CYAN}Connection Settings:{RESET}")
            pass
            pass
            kharej_ip = ask_nonempty(f"  {BOLD}Kharej Client IP or Domain:{RESET}")
            tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            if ':' in kharej_ip and not kharej_ip.startswith('['):
                connect_addr = f"[{kharej_ip}]:{tport}"
                print(f"  {FG_CYAN}IPv6 format:{RESET} {FG_WHITE}{connect_addr}{RESET}")
            else:
                connect_addr = f"{kharej_ip}:{tport}"
            edge_ip = ""
            if transport in ("wsmux", "wssmux"):
                edge_ip = ask_edge_ip_optional("Cloudflare")
                if edge_ip:
                    c_ok(f"  ✅ Edge IP set: {FG_CYAN}{edge_ip}{RESET} (connect to this IP, Host/SNI from {connect_addr})")
        else:
            tport = ask_free_port("Tunnel Port")
            bind_ip = "0.0.0.0"
            if use_ipv6:
                listen_addr = f"[::]:{tport}"
            else:
                listen_addr = f"{bind_ip}:{tport}"
        
        print(f"\n  {BOLD}{FG_CYAN}Security Settings:{RESET}")
        psk = ask_nonempty(f"  {BOLD}Pre-shared Key (PSK):{RESET}")
        
        encryption_config = configure_encryption()
        encryption_enabled = encryption_config["enabled"]
        encryption_algorithm = encryption_config["algorithm"]
        encryption_key = encryption_config["key"]
        
        stealth_config = configure_stealth()
        stealth_padding = stealth_config["padding_enabled"]
        stealth_padding_min = stealth_config["padding_min"]
        stealth_padding_max = stealth_config["padding_max"]
        stealth_jitter = stealth_config["jitter_enabled"]
        stealth_jitter_min = stealth_config["jitter_min_ms"]
        stealth_jitter_max = stealth_config["jitter_max_ms"]
        
        anti_dpi_delay_ms = configure_anti_dpi()
        
        print(f"\n  {BOLD}{FG_CYAN}Performance Profiles:{RESET}")
        print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}balanced{RESET}")
        print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}aggressive{RESET}")
        print(f"  {FG_CYAN}[3]{RESET} {FG_WHITE}latency{RESET}")
        print(f"  {FG_CYAN}[4]{RESET} {FG_WHITE}cpu-efficient{RESET}")
        profile_choice = ask_int(f"\n  {BOLD}Select profile:{RESET}", min_=1, max_=4, default=1)
        profiles = {1: "balanced", 2: "aggressive", 3: "latency", 4: "cpu-efficient"}
        profile = profiles[profile_choice]
        
        stream_queue_size = None
        if direct_mode:
            print(f"\n  {BOLD}{FG_CYAN}Connection Pool Settings:{RESET}")
            smux_default = get_default_smux_config(profile)
            default_mux_con = smux_default.get("mux_con", 8)
            connection_pool = ask_int(f"  {BOLD}Connection Pool:{RESET} {FG_WHITE}(recommended: 8-16){RESET}", min_=1, max_=64, default=8)
            mux_con = ask_int(f"  {BOLD}Mux Con:{RESET} {FG_WHITE}(recommended: {default_mux_con} for {profile} profile){RESET}", min_=1, max_=32, default=default_mux_con)
            retry_interval = ask_int(f"  {BOLD}Retry Interval:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=60, default=3)
            dial_timeout = ask_int(f"  {BOLD}Dial Timeout:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=60, default=10)
            aggressive_pool = ask_yesno(f"  {BOLD}Aggressive Pool?{RESET} {FG_WHITE}(faster reconnect){RESET}", default=False)
        else:
            print(f"\n  {BOLD}{FG_CYAN}Server Queue Settings:{RESET}")
            print(f"  {FG_WHITE}(Iran reverse only — local TCP accept queue; engine default 2048 if omitted){RESET}")
            stream_queue_size = ask_int(f"  {BOLD}Stream Queue Size:{RESET} {FG_WHITE}(default: 2048){RESET}", min_=128, max_=65536, default=2048)
        
        maps = []
        print(f"\n  {BOLD}{FG_CYAN}Port Mappings:{RESET} {FG_WHITE}(Press Enter to skip){RESET}")
        print(f"\n  {BOLD}{FG_CYAN}Supported Formats:{RESET}")
        print(f"  {FG_RED}Single Port:{RESET} {FG_WHITE}500{RESET}")
        print(f"  {FG_RED}Port Range:{RESET} {FG_WHITE}500-567{RESET}")
        print(f"  {FG_RED}Multiple Ports:{RESET} {FG_WHITE}500,555,666{RESET}")
        print(f"  {FG_RED}Bind to IP:Port:{RESET} {FG_WHITE}192.168.1.1:666{RESET}")
        print(f"  {FG_RED}Redirect Port:{RESET} {FG_WHITE}4000=5000{RESET}")
        print(f"  {FG_RED}Range Redirect to Port:{RESET} {FG_WHITE}443-600:5201{RESET}")
        print(f"  {FG_RED}Range Redirect to IP:Port:{RESET} {FG_WHITE}443-600=192.168.1.1:5201{RESET}")
        print(f"  {FG_RED}Full Specification (Bind IP:Port=Target IP:Port):{RESET} {FG_WHITE}127.0.0.2:443=192.168.1.1:5201{RESET}")
        print(f"  {FG_RED}Mixed (Multiple formats):{RESET} {FG_WHITE}500,443-600:5201,192.168.1.1:666=8080{RESET}")
        
        try:
            tcp_input = input(_input_prompt("TCP Ports")).strip()
        except KeyboardInterrupt:
            exit_script()
        
        if tcp_input:
            try:
                tcp_maps = parse_advanced_ports(tcp_input, "tcp")
                maps.extend(tcp_maps)
                if tcp_maps:
                    c_ok(f"  ✅ Added {FG_GREEN}{len(tcp_maps)}{RESET} TCP mapping(s)")
            except ValueError as e:
                c_err(f"  ⚠️  Invalid: {e}")
        
        try:
            udp_input = input(_input_prompt("UDP Ports")).strip()
        except KeyboardInterrupt:
            exit_script()
        
        if udp_input:
            try:
                udp_maps = parse_advanced_ports(udp_input, "udp")
                maps.extend(udp_maps)
                if udp_maps:
                    c_ok(f"  ✅ Added {FG_GREEN}{len(udp_maps)}{RESET} UDP mapping(s)")
            except ValueError as e:
                c_err(f"  ⚠️  Invalid: {e}")
        
        if maps:
            original_count = len(maps)
            maps = compact_maps(maps)
            if len(maps) < original_count:
                c_ok(f"  ✅ Compacted to {FG_GREEN}{len(maps)}{RESET} mapping(s) (from {original_count})")
        
        cert_file = None
        key_file = None
        if transport in ("tlsmux", "wssmux", "realitymux") and not direct_mode:
            print(f"\n  {BOLD}🔐 TLS/REALITY Certificate (Reverse – server listens):{RESET}")
            print(f"  {FG_GREEN}1){RESET} Get new certificate (Let's Encrypt) {FG_WHITE}[Default – recommended]{RESET}")
            print(f"  {FG_BLUE}2){RESET} Use existing certificate (provide file paths)")
            print(f"  {FG_YELLOW}3){RESET} Self-signed (test only, auto-generated)")
            cert_choice = ask_int("\nSelect certificate type", min_=1, max_=3, default=1)
            
            if cert_choice == 1:
                while True:
                    try:
                        domain = input(f"\n  {BOLD}{FG_GREEN}Enter your domain:{RESET} {FG_WHITE}(e.g., example.com or sub.example.com){RESET} ").strip()
                    except KeyboardInterrupt:
                        exit_script()
                    if not domain:
                        c_err("  Domain is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            exit_script()
                        continue
                    
                    try:
                        email = input(_input_prompt("Email" )).strip()
                    except KeyboardInterrupt:
                        exit_script()
                    if not email:
                        c_err("  Email is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            exit_script()
                        continue
                    
                    cert_file, key_file = get_certificate_with_acme(domain, email, tport)
                    if not cert_file or not key_file:
                        c_err("  Failed to get real certificate!")
                        print(f"\n  {BOLD}{FG_YELLOW}Options:{RESET}")
                        print(f"  {FG_GREEN}1){RESET} Retry certificate acquisition")
                        print(f"  {FG_RED}2){RESET} Cancel and exit")
                        try:
                            retry_choice = input(f"\n  {BOLD}Select option:{RESET} ").strip()
                        except KeyboardInterrupt:
                            exit_script()
                        if retry_choice != "1":
                            exit_script()
                    else:
                        c_ok(f"  ✅ Real certificate obtained: {FG_GREEN}{cert_file}{RESET}")
                        break 
            
            elif cert_choice == 2:
                while True:
                    try:
                        cert_path = input(f"\n  {BOLD}{FG_GREEN}Enter certificate file path:{RESET} {FG_WHITE}(e.g., /root/cert.crt){RESET} ").strip()
                    except KeyboardInterrupt:
                        exit_script()
                    if not cert_path:
                        c_err("  Certificate file path is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            exit_script()
                        continue
                    
                    cert_path_obj = Path(cert_path)
                    if not cert_path_obj.exists():
                        c_err(f"  Certificate file not found: {FG_RED}{cert_path}{RESET}")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            exit_script()
                        continue
                    
                    try:
                        key_path = input(_input_prompt("Private key file path" )).strip()
                    except KeyboardInterrupt:
                        exit_script()
                    if not key_path:
                        c_err("  Private key file path is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            exit_script()
                        continue
                    
                    key_path_obj = Path(key_path)
                    if not key_path_obj.exists():
                        c_err(f"  Private key file not found: {FG_RED}{key_path}{RESET}")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            exit_script()
                        continue
                    
                    try:
                        with open(cert_path_obj, 'r') as f:
                            cert_content = f.read()
                            if "BEGIN CERTIFICATE" not in cert_content:
                                c_err("  Invalid certificate file format!")
                                if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                    exit_script()
                                continue
                        
                        with open(key_path_obj, 'r') as f:
                            key_content = f.read()
                            if "BEGIN" not in key_content or "PRIVATE KEY" not in key_content:
                                c_err("  Invalid private key file format!")
                                if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                    exit_script()
                                continue
                        
                        cert_file = str(cert_path_obj)
                        key_file = str(key_path_obj)
                        c_ok(f"  ✅ Certificate files validated: {FG_GREEN}{cert_file}{RESET}")
                        break
                    except UserCancelled:
                        exit_script()
                    except Exception as e:
                        c_err(f"Error reading certificate files: {e}")
                        if not ask_yesno("Try again?", default=True):
                            exit_script()
        
        tls_insecure_skip_verify = False
        if direct_mode and transport in ("tlsmux", "wssmux", "realitymux"):
            print(f"\n  {BOLD}🔐 Kharej Client Certificate (TLS/REALITY):{RESET}")
            print(f"  {FG_GREEN}1){RESET} Server (valid certificate – Kharej uses Let's Encrypt or real cert)")
            print(f"  {FG_YELLOW}2){RESET} Test (self-signed – Kharej uses self-signed, Iran accepts it)")
            cert_accept = ask_int(f"  {BOLD}Select:{RESET}", min_=1, max_=2, default=1)
            if cert_accept == 2:
                tls_insecure_skip_verify = True
                c_ok("  ✅ Server will accept outside side's self-signed certificate")
            else:
                tls_insecure_skip_verify = False
                c_ok("  ✅ Server will require valid certificate (secure default)")
        
        _section("ADVANCED")
        verbose = ask_yesno(f"  {BOLD}Verbose logging{RESET}", default=False)
        heartbeat = ask_int(f"  {BOLD}Heartbeat Interval:{RESET}", min_=1, max_=300, default=DEFAULT_HEARTBEAT)

        _section("PERFORMANCE")
        if ask_yesno(f"  {BOLD}Custom compression{RESET}", default=False):
            compression_config = configure_compression()
        else:
            compression_config = {
                "enabled": True,
                "algorithm": "lz4",
                "level": 0,
                "min_size": 1024,
                "max_size": 65536
            }

        if ask_yesno(f"  {BOLD}Custom buffer pools{RESET}", default=False):
            buffer_pool_config = configure_buffer_pools()
        else:
            buffer_pool_config = {
                "buffer_pool_size": DEFAULT_BUFFER_POOL_SIZE,
                "large_buffer_pool_size": DEFAULT_LARGE_BUFFER_POOL_SIZE,
                "udp_frame_pool_size": DEFAULT_UDP_FRAME_POOL_SIZE,
                "udp_data_slice_size": DEFAULT_UDP_SLICE_SIZE
            }

        _section("TUN")
        tun_enabled = ask_yesno(f"  {BOLD}Enable TUN mode{RESET}", default=False)

        tun_config = None
        if tun_enabled:
            tun_name = ask_nonempty(f"  {BOLD}Interface Name:{RESET}", default="netrix0")
            tun_local = ask_nonempty(f"  {BOLD}Local IP (CIDR):{RESET}", default="10.200.0.1/30")
            tun_mtu = ask_int(f"  {BOLD}MTU:{RESET}", min_=576, max_=9000, default=1400)
            tun_routes = []
            while True:
                try:
                    route = input(_input_prompt("Route [empty=done]")).strip()
                except KeyboardInterrupt:
                    exit_script()
                if not route:
                    break
                tun_routes.append(route)
                c_ok(f"Route added: {route}")
            tun_streams = ask_int(f"  {BOLD}TUN Streams:{RESET}", min_=1, max_=64, default=4)
            forward_l2tp = ask_yesno(f"  {BOLD}Auto-forward L2TP/IPsec ports{RESET}", default=True)
            l2tp_dest_ip = ""
            if forward_l2tp:
                try:
                    l2tp_dest_ip = input(_input_prompt("DNAT Destination IP [optional]")).strip()
                except KeyboardInterrupt:
                    exit_script()
            tun_config = {
                "enabled": True,
                "name": tun_name,
                "local": tun_local,
                "mtu": tun_mtu,
                "routes": tun_routes,
                "streams": tun_streams,
                "forward_l2tp": forward_l2tp,
                "l2tp_ports": [500,4500,1701],
                "l2tp_dest_ip": l2tp_dest_ip,
            }
            c_ok(f"TUN: {tun_name} ({tun_local})")

        _section("PROXY PROTOCOL")
        proxy_protocol_enabled = ask_yesno(f"  {BOLD}Enable PROXY protocol{RESET}", default=False)
        proxy_protocol_version = "v1"
        proxy_protocol_ports = []
        if proxy_protocol_enabled:
            print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}v1{RESET}")
            print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}v2{RESET}")
            version_choice = ask_int(f"  {BOLD}Version{RESET}", min_=1, max_=2, default=1)
            proxy_protocol_version = "v1" if version_choice == 1 else "v2"
            try:
                ports_input = input(_input_prompt("Ports [empty=all]")).strip()
            except KeyboardInterrupt:
                exit_script()
            if ports_input:
                proxy_protocol_ports = [p.strip() for p in ports_input.split(",") if p.strip()]
                c_ok(f"PROXY Protocol on {len(proxy_protocol_ports)} port(s)")
            else:
                c_ok("PROXY Protocol on all ports")
        else:
            c_ok("PROXY Protocol disabled")
        rawsocket_interface = ""
        rawsocket_local_ip = ""
        rawsocket_router_mac = ""
        rawsocket_local_flags = []
        rawsocket_remote_flags = []
        if transport in ("rawsocket", "rawmux"):
            detected = detect_rawsocket_pcap_defaults()
            rawsocket_interface = detected.get("interface") or ""
            rawsocket_local_ip = detected.get("local_ip") or ""
            rawsocket_router_mac = detected.get("router_mac") or ""
            rawsocket_local_flags = detected.get("local_flags") or []
            rawsocket_remote_flags = detected.get("remote_flags") or []
            parts = []
            if rawsocket_interface:
                parts.append(f"interface={rawsocket_interface}")
            if rawsocket_local_ip:
                parts.append(f"local_ip={rawsocket_local_ip}")
            if rawsocket_router_mac:
                parts.append(f"router_mac={rawsocket_router_mac}")
            if parts:
                print(f"\n  {FG_GREEN}✅ rawsocket/pcap: auto-detected → {FG_WHITE}{', '.join(parts)}{RESET} (written to config)")
            else:
                print(f"\n  {FG_GREEN}✅ rawsocket/pcap: defaults (netrix will auto-detect at runtime){RESET}")
        
        cfg = {
            "tport": tport,
            "listen": listen_addr,
            "connect": connect_addr,
            "direct": direct_mode,
            "connection_pool": connection_pool,
            "mux_con": mux_con,
            "transport": transport,
            "psk": psk,
            "profile": profile,
            "maps": maps,
            "verbose": verbose,
            "heartbeat": heartbeat, 
            "compression_config": compression_config,
            "buffer_pool_config": buffer_pool_config,
            "encryption_enabled": encryption_enabled,
            "encryption_algorithm": encryption_algorithm,
            "encryption_key": encryption_key,
            "stealth_padding": stealth_padding,
            "stealth_padding_min": stealth_padding_min,
            "stealth_padding_max": stealth_padding_max,
            "stealth_jitter": stealth_jitter,
            "stealth_jitter_min": stealth_jitter_min,
            "stealth_jitter_max": stealth_jitter_max,
            "anti_dpi_delay_ms": anti_dpi_delay_ms,
            "tun_config": tun_config,
            "proxy_protocol_enabled": proxy_protocol_enabled,
            "proxy_protocol_version": proxy_protocol_version,
            "proxy_protocol_ports": proxy_protocol_ports,
            "tls_insecure_skip_verify": tls_insecure_skip_verify
        }
        if direct_mode:
            cfg["retry_interval"] = retry_interval
            cfg["dial_timeout"] = dial_timeout
            cfg["aggressive_pool"] = aggressive_pool
            if edge_ip:
                cfg["edge_ip"] = edge_ip
        elif stream_queue_size:
            cfg["stream_queue_size"] = stream_queue_size
        
        if cert_file and key_file:
            cfg["cert_file"] = cert_file
            cfg["key_file"] = key_file
            print(f"  {FG_GREEN}✅ Certificate files added to config: cert={cert_file}, key={key_file}{RESET}")
        elif transport in ("tlsmux", "wssmux", "realitymux") and not direct_mode:
            print(f"  {FG_YELLOW}⚠️  No certificate files (option 3 – self-signed will be used){RESET}")
        elif transport in ("tlsmux", "wssmux", "realitymux") and direct_mode:
            print(f"  {FG_CYAN}Direct mode: server dials to client{RESET}")
        
        if transport == "realitymux" and reality_sni and reality_fingerprint:
            cfg["reality_sni"] = reality_sni
            cfg["reality_fingerprint"] = reality_fingerprint
        if transport in ("rawsocket", "rawmux"):
            cfg["rawsocket_interface"] = rawsocket_interface
            cfg["rawsocket_local_ip"] = rawsocket_local_ip
            cfg["rawsocket_router_mac"] = rawsocket_router_mac
            cfg["rawsocket_local_flags"] = rawsocket_local_flags
            cfg["rawsocket_remote_flags"] = rawsocket_remote_flags
        
        config_path = create_server_config_file(tport, cfg)
        
        print()
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        c_ok(f"  ✅ Configuration saved: {FG_WHITE}{config_path}{RESET}")
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        
        print()
        if ask_yesno(f"  {BOLD}{FG_CYAN}Start tunnel now?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
            if run_tunnel(config_path):
                c_ok(f"  ✅ Tunnel started successfully!")
            else:
                c_err("  ❌ Failed to start tunnel!")
        
        pause()
    except UserCancelled:
        exit_script()

def create_client_tunnel():
    """ساخت تانل کلاینت (Outside)"""
    try:
        if not ensure_netrix_available():
            clear()
            print(f"{BOLD}{FG_RED}╔══════════════════════════════════════════════════════════╗{RESET}")
            print(f"                            {BOLD}Core Not Installed{RESET}                  ")
            print(f"{BOLD}{FG_RED}╚══════════════════════════════════════════════════════════╝{RESET}")
            print()
            c_err("Netrix core is not installed!")
            print(f"\n  {FG_YELLOW}You need to install the core first.{RESET}")
            print(f"  {FG_CYAN}Go to: Main Menu → Option 6 (Install/Update Core){RESET}\n")
            if ask_yesno(f"  {BOLD}Do you want to install the core now?{RESET}", default=True):
                install_netrix_core()
                if ensure_netrix_available():
                    c_ok("Core installed successfully! Continuing...")
                else:
                    c_err("Core installation failed!")
                    pause()
                    return
            else:
                pause()
                return
        
        _wizard_intro("KHAREJ CLIENT", "")
        
        transport = ask_transport(include_l3=True)
        if transport == "l3":
            create_client_l3_tunnel()
            return
        direct_mode = ask_connection_mode_for_transport(transport, server_side=False)
        
        reality_sni = ""
        reality_fingerprint = ""
        if transport == "realitymux" and not direct_mode:
            print(f"\n  {BOLD}🎭 REALITY Configuration:{RESET}")
                                                            
            print(f"\n  {BOLD}SNI Target:{RESET}")
            print(f"  {FG_CYAN}1){RESET} {FG_WHITE}cloudflare.com{RESET} (Recommended - most common)")
            print(f"  {FG_CYAN}2){RESET} {FG_WHITE}google.com{RESET}")
            print(f"  {FG_CYAN}3){RESET} {FG_WHITE}microsoft.com{RESET}")
            print(f"  {FG_CYAN}4){RESET} {FG_WHITE}apple.com{RESET}")
            print(f"  {FG_CYAN}5){RESET} {FG_YELLOW}random{RESET} (Changes per connection - maximum stealth)")
            print(f"  {FG_CYAN}6){RESET} {FG_YELLOW}Custom{RESET}")
            sni_choice = ask_int(f"  {BOLD}Select SNI target:{RESET}", min_=1, max_=6, default=5) 
            sni_options = {1: "cloudflare.com", 2: "google.com", 3: "microsoft.com", 4: "apple.com", 5: "random"}
            if sni_choice == 6:
                reality_sni = ask_nonempty(f"  {BOLD}Enter custom SNI:{RESET}")
            else:
                reality_sni = sni_options[sni_choice]
            
            print(f"\n  {BOLD}TLS Fingerprint:{RESET}")
            print(f"  {FG_WHITE}Select which browser's TLS fingerprint to mimic:{RESET}")
            print(f"  {FG_CYAN}1){RESET} {FG_WHITE}Chrome{RESET} (Recommended - most common)")
            print(f"  {FG_CYAN}2){RESET} {FG_WHITE}Firefox{RESET}")
            print(f"  {FG_CYAN}3){RESET} {FG_WHITE}Safari{RESET}")
            print(f"  {FG_CYAN}4){RESET} {FG_WHITE}Edge{RESET}")
            print(f"  {FG_CYAN}5){RESET} {FG_WHITE}iOS{RESET}")
            print(f"  {FG_CYAN}6){RESET} {FG_WHITE}Android{RESET}")
            print(f"  {FG_CYAN}7){RESET} {FG_YELLOW}random{RESET} (Changes per connection - maximum stealth)")
            fingerprint_choice = ask_int(f"  {BOLD}Select fingerprint:{RESET}", min_=1, max_=7, default=7) 
            fingerprint_options = {1: "chrome", 2: "firefox", 3: "safari", 4: "edge", 5: "ios", 6: "android", 7: "random"}
            reality_fingerprint = fingerprint_options[fingerprint_choice]
            
            c_ok(f"  ✅ REALITY configured: SNI={reality_sni}, Fingerprint={reality_fingerprint}")
        elif transport == "realitymux" and direct_mode:
            print(f"\n  {BOLD}🎭 REALITY Configuration:{RESET}")
            c_ok(f"  ✅ REALITY client will accept connections with any SNI")
        
        tls_insecure_skip_verify = False
        cert_file = None
        key_file = None
        
        if transport in ("tlsmux", "wssmux", "realitymux"):
            if not direct_mode:
                print(f"\n  {BOLD}🔐 Server Certificate Type (Reverse – Kharej connects):{RESET}")
                print(f"  {FG_GREEN}1){RESET} Server (real certificate – Let's Encrypt or valid cert) {FG_WHITE}[Default]{RESET}")
                print(f"  {FG_YELLOW}2){RESET} Test (self-signed certificate)")
                cert_type = ask_int(f"  {BOLD}Select:{RESET}", min_=1, max_=2, default=1)
                
                if cert_type == 2:
                    tls_insecure_skip_verify = True
                    c_warn("  ⚠️  tls_insecure_skip_verify will be set to true (for self-signed certificate)")
                else:
                    tls_insecure_skip_verify = False
                    c_ok("  ✅ tls_insecure_skip_verify will be set to false (for real certificate)")
            else:
                print(f"\n  {BOLD}🔐 TLS/REALITY Certificate (Direct – Kharej listens):{RESET}")
                print(f"  {FG_GREEN}1){RESET} Get new certificate (Let's Encrypt) {FG_WHITE}[Default – recommended]{RESET}")
                print(f"  {FG_BLUE}2){RESET} Use existing certificate (provide file paths)")
                print(f"  {FG_YELLOW}3){RESET} Self-signed (no cert config – فقط اگر روی سرور ایران «قبول self-signed» زدی)")
                cert_choice = ask_int("\nSelect certificate type", min_=1, max_=3, default=1)
                
                if cert_choice == 1:
                    while True:
                        try:
                            domain = input(f"\n  {BOLD}{FG_GREEN}Enter your domain:{RESET} {FG_WHITE}(e.g., example.com or sub.example.com){RESET} ").strip()
                        except KeyboardInterrupt:
                            exit_script()
                        if not domain:
                            c_err("  Domain is required!")
                            if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                exit_script()
                            continue
                        
                        try:
                            email = input(_input_prompt("Email" )).strip()
                        except KeyboardInterrupt:
                            exit_script()
                        if not email:
                            c_err("  Email is required!")
                            if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                exit_script()
                            continue
                        
                        cert_domain = domain
                        cert_email = email
                        cert_choice_stored = 1
                        break
                
                elif cert_choice == 2:
                    while True:
                        try:
                            cert_path = input(f"\n  {BOLD}{FG_GREEN}Enter certificate file path:{RESET} {FG_WHITE}(e.g., /root/cert.crt){RESET} ").strip()
                        except KeyboardInterrupt:
                            exit_script()
                        if not cert_path:
                            c_err("  Certificate file path is required!")
                            if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                exit_script()
                            continue
                        
                        cert_path_obj = Path(cert_path)
                        if not cert_path_obj.exists():
                            c_err(f"  Certificate file not found: {FG_RED}{cert_path}{RESET}")
                            if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                exit_script()
                            continue
                        
                        try:
                            key_path = input(_input_prompt("Private key file path" )).strip()
                        except KeyboardInterrupt:
                            exit_script()
                        if not key_path:
                            c_err("  Private key file path is required!")
                            if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                exit_script()
                            continue
                        
                        key_path_obj = Path(key_path)
                        if not key_path_obj.exists():
                            c_err(f"  Private key file not found: {FG_RED}{key_path}{RESET}")
                            if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                exit_script()
                            continue
                        
                        try:
                            with open(cert_path_obj, 'r') as f:
                                cert_content = f.read()
                                if "BEGIN CERTIFICATE" not in cert_content:
                                    c_err("  Invalid certificate file format!")
                                    if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                        exit_script()
                                    continue
                            
                            with open(key_path_obj, 'r') as f:
                                key_content = f.read()
                                if "BEGIN" not in key_content or "PRIVATE KEY" not in key_content:
                                    c_err("  Invalid private key file format!")
                                    if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                        exit_script()
                                    continue
                            
                            cert_file = str(cert_path_obj)
                            key_file = str(key_path_obj)
                            c_ok(f"  ✅ Certificate files validated: {FG_GREEN}{cert_file}{RESET}")
                            break
                        except UserCancelled:
                            exit_script()
                        except Exception as e:
                            c_err(f"Error reading certificate files: {e}")
                            if not ask_yesno("Try again?", default=True):
                                exit_script()
                else:
                    c_ok("  ✅ Self-signed certificate will be auto-generated (ensure Iran server has «accept self-signed» enabled)")
        
        server_addr = ""
        listen_addr = ""
        tport = 0
        
        use_ipv6 = False
        if is_ipv6_available():
            print(f"  {FG_CYAN}IPv6 available{RESET}")
            use_ipv6 = ask_yesno(f"  {BOLD}Enable IPv6 support{RESET}", default=False)
        else:
            print(f"  {FG_YELLOW}IPv6 unavailable{RESET}")
        
        if direct_mode:
            print(f"\n  {BOLD}{FG_CYAN}Connection Settings:{RESET}")
            tport = ask_free_port("Tunnel Port")
            
            bind_ip = "0.0.0.0"
            if use_ipv6:
                listen_addr = f"[::]:{tport}"
            else:
                listen_addr = f"{bind_ip}:{tport}"
            
            if transport in ("tlsmux", "wssmux", "realitymux") and 'cert_choice_stored' in locals() and cert_choice_stored == 1:
                cert_file, key_file = get_certificate_with_acme(cert_domain, cert_email, tport)
                if not cert_file or not key_file:
                    c_err("  Failed to get real certificate!")
                    print(f"\n  {BOLD}{FG_YELLOW}Options:{RESET}")
                    print(f"  {FG_GREEN}1){RESET} Continue with self-signed certificate (auto-generated)")
                    print(f"  {FG_RED}2){RESET} Cancel and exit")
                    try:
                        retry_choice = input(f"\n  {BOLD}Select option:{RESET} ").strip()
                    except KeyboardInterrupt:
                        exit_script()
                    if retry_choice != "1":
                        exit_script()
                    else:
                        cert_file = None
                        key_file = None
                        c_ok("  ✅ Will use self-signed certificate (auto-generated)")
                else:
                    c_ok(f"  ✅ Real certificate obtained: {FG_GREEN}{cert_file}{RESET}")
        else:
            print(f"\n  {BOLD}{FG_CYAN}Connection Settings:{RESET}")
            pass
            pass
            if transport in ("wssmux", "tlsmux", "realitymux"):
                pass
            server_ip = ask_nonempty(f"  {BOLD}Iran Server IP:{RESET}")
            tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            
            if ':' in server_ip and not server_ip.startswith('[') and '.' not in server_ip:
                server_addr = f"[{server_ip}]:{tport}"
                print(f"  {FG_CYAN}IPv6 format:{RESET} {FG_WHITE}{server_addr}{RESET}")
            else:
                server_addr = f"{server_ip}:{tport}"
        
        print(f"\n  {BOLD}{FG_CYAN}Security Settings:{RESET}")
        pass
        psk = ask_nonempty(f"  {BOLD}Pre-shared Key (PSK):{RESET}")
        
        encryption_config = configure_encryption()
        encryption_enabled = encryption_config["enabled"]
        encryption_algorithm = encryption_config["algorithm"]
        encryption_key = encryption_config["key"]
        
        stealth_config = configure_stealth()
        stealth_padding = stealth_config["padding_enabled"]
        stealth_padding_min = stealth_config["padding_min"]
        stealth_padding_max = stealth_config["padding_max"]
        stealth_jitter = stealth_config["jitter_enabled"]
        stealth_jitter_min = stealth_config["jitter_min_ms"]
        stealth_jitter_max = stealth_config["jitter_max_ms"]
        
        anti_dpi_delay_ms = configure_anti_dpi()
        
        print(f"\n  {BOLD}{FG_CYAN}Performance Profiles:{RESET}")
        print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}balanced{RESET}")
        print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}aggressive{RESET}")
        print(f"  {FG_CYAN}[3]{RESET} {FG_WHITE}latency{RESET}")
        print(f"  {FG_CYAN}[4]{RESET} {FG_WHITE}cpu-efficient{RESET}")
        profile_choice = ask_int(f"\n  {BOLD}Select profile:{RESET}", min_=1, max_=4, default=1)
        profiles = {1: "balanced", 2: "aggressive", 3: "latency", 4: "cpu-efficient"}
        profile = profiles[profile_choice]

        paths = []
        connection_pool = 8
        mux_con = 8
        retry_interval = 3
        dial_timeout = 10
        aggressive_pool = False
        
        if not direct_mode:
            print(f"\n  {BOLD}{FG_CYAN}Connection Pool Settings:{RESET}")
            smux_default = get_default_smux_config(profile)
            default_mux_con = smux_default.get("mux_con", 8)
            connection_pool = ask_int(f"  {BOLD}Connection Pool:{RESET} {FG_WHITE}(recommended: 8-16){RESET}", min_=1, max_=64, default=8)
            mux_con = ask_int(f"  {BOLD}Mux Con:{RESET} {FG_WHITE}(recommended: {default_mux_con} for {profile} profile){RESET}", min_=1, max_=32, default=default_mux_con)
            retry_interval = ask_int(f"  {BOLD}Retry Interval:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=60, default=3)
            dial_timeout = ask_int(f"  {BOLD}Dial Timeout:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=60, default=10)
            aggressive_pool = ask_yesno(f"  {BOLD}Aggressive Pool?{RESET} {FG_WHITE}(faster reconnect){RESET}", default=False)
            
            path_dict = {
                "addr": server_addr,
                "transport": transport,
                "connection_pool": connection_pool,
                "retry_interval": retry_interval,
                "dial_timeout": dial_timeout,
                "aggressive_pool": aggressive_pool
            }
            if transport in ("wsmux", "wssmux"):
                _ep = ask_edge_ip_optional("Cloudflare")
                if _ep:
                    path_dict["edge_ip"] = _ep
                    c_ok(f"  ✅ Edge IP set: {FG_CYAN}{_ep}{RESET}")
            if transport == "realitymux" and reality_sni and reality_fingerprint:
                path_dict["reality_sni"] = reality_sni
                path_dict["reality_fingerprint"] = reality_fingerprint
            
            paths.append(path_dict)
            
            print(f"\n  {FG_GREEN}✅ Primary server configured:{RESET} {FG_CYAN}{transport}://{server_addr}{RESET} {FG_WHITE}({connection_pool} connections){RESET}")
            
        else:
            print(f"\n  {FG_GREEN}✅ Direct mode configured:{RESET} {FG_WHITE}Listening on {listen_addr}{RESET}")
            print(f"\n  {FG_YELLOW}💡 Tip:{RESET} You can add backup servers (additional Iran servers) for redundancy.")
            print(f"     {FG_WHITE}If the primary server fails, client will automatically switch to backup server.{RESET}")
            while True:
                if not ask_yesno(f"\n  {BOLD}{FG_CYAN}Add another Iran server (backup)?{RESET}", default=False):
                    break
                
                print(f"\n  {BOLD}{FG_CYAN}Backup Server #{len(paths) + 1}:{RESET} {FG_WHITE}(Additional Iran Server){RESET}")
                
                print(f"\n  {BOLD}Transport Types:{RESET}")
                print(f"  {FG_CYAN}1){RESET} {FG_WHITE}tcpmux{RESET} (TCP with smux)")
                print(f"  {FG_CYAN}2){RESET} {FG_WHITE}tlsmux{RESET} (TLS with smux - lighter than WS/WSS)")
                print(f"  {FG_CYAN}3){RESET} {FG_WHITE}kcpmux{RESET} (KCP with smux)")
                print(f"  {FG_CYAN}4){RESET} {FG_WHITE}wsmux{RESET} (WebSocket with smux)")
                print(f"  {FG_CYAN}5){RESET} {FG_WHITE}wssmux{RESET} (WebSocket Secure with smux)")
                print(f"  {FG_CYAN}6){RESET} {FG_WHITE}realitymux{RESET} (REALITY TLS camouflage - anti-DPI)")
                print(f"  {FG_CYAN}7){RESET} {FG_WHITE}rawsocket{RESET} (KCP+FEC - high performance)")
                new_transport_choice = ask_int(f"\n  {BOLD}Select transport:{RESET}", min_=1, max_=7, default=1)
                transports_backup = {1: "tcpmux", 2: "tlsmux", 3: "kcpmux", 4: "wsmux", 5: "wssmux", 6: "realitymux", 7: "rawsocket"}
                new_transport = transports_backup[new_transport_choice]
                
                new_reality_sni = None
                new_reality_fingerprint = None
                if new_transport == "realitymux":
                    print(f"\n  {BOLD}{FG_CYAN}REALITY Configuration:{RESET} {FG_WHITE}(TLS Camouflage){RESET}")
                    print(f"  {FG_WHITE}REALITY mimics real browser TLS fingerprints to bypass DPI.{RESET}")
                    print(f"\n  {BOLD}SNI Target:{RESET}")
                    print(f"  {FG_CYAN}1){RESET} {FG_WHITE}cloudflare.com{RESET} {FG_WHITE}(default - recommended){RESET}")
                    print(f"  {FG_CYAN}2){RESET} {FG_WHITE}google.com{RESET}")
                    print(f"  {FG_CYAN}3){RESET} {FG_WHITE}microsoft.com{RESET}")
                    print(f"  {FG_CYAN}4){RESET} {FG_WHITE}apple.com{RESET}")
                    print(f"  {FG_CYAN}5){RESET} {FG_WHITE}Custom{RESET}")
                    sni_choice = ask_int(f"  {BOLD}Select SNI:{RESET}", min_=1, max_=5, default=1)
                    sni_options = {1: "cloudflare.com", 2: "google.com", 3: "microsoft.com", 4: "apple.com"}
                    if sni_choice == 5:
                        new_reality_sni = ask_nonempty(f"  {BOLD}Custom SNI:{RESET}")
                    else:
                        new_reality_sni = sni_options[sni_choice]
                    
                    print(f"\n  {BOLD}TLS Fingerprint:{RESET}")
                    print(f"  {FG_CYAN}1){RESET} {FG_WHITE}chrome{RESET} {FG_WHITE}(default - most common){RESET}")
                    print(f"  {FG_CYAN}2){RESET} {FG_WHITE}firefox{RESET}")
                    print(f"  {FG_CYAN}3){RESET} {FG_WHITE}safari{RESET}")
                    print(f"  {FG_CYAN}4){RESET} {FG_WHITE}edge{RESET}")
                    print(f"  {FG_CYAN}5){RESET} {FG_WHITE}ios{RESET}")
                    print(f"  {FG_CYAN}6){RESET} {FG_WHITE}android{RESET}")
                    fingerprint_choice = ask_int(f"  {BOLD}Select fingerprint:{RESET}", min_=1, max_=6, default=1)
                    fingerprint_options = {1: "chrome", 2: "firefox", 3: "safari", 4: "edge", 5: "ios", 6: "android"}
                    new_reality_fingerprint = fingerprint_options[fingerprint_choice]
                
                if new_transport == "wssmux":
                    pass
                    print(f"  {FG_YELLOW}⚠️  Note: For Let's Encrypt, you must use domain (not IP address){RESET}")
                    new_server_domain = ask_nonempty(f"  {BOLD}Server Domain:{RESET}")
                    new_tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
                    new_server_addr = f"{new_server_domain}:{new_tport}"
                elif new_transport == "tlsmux":
                    print(f"  {FG_WHITE}IPv4 example: 1.2.3.4 | IPv6 example: 2001:db8::1{RESET}")
                    print(f"  {FG_WHITE}Domain example: example.com or sub.example.com (optional){RESET}")
                    print(f"  {FG_YELLOW}⚠️  Note: You can use IP or domain for tlsmux{RESET}")
                    new_server_input = ask_nonempty(f"  {BOLD}Iran Server IP or Domain:{RESET}")
                    new_tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
                    
                    if ':' in new_server_input and not new_server_input.startswith('[') and not '.' in new_server_input.replace(':', ''):
                        new_server_addr = f"[{new_server_input}]:{new_tport}"
                    else:
                        new_server_addr = f"{new_server_input}:{new_tport}"
                elif new_transport == "realitymux":
                    print(f"  {FG_WHITE}IPv4 example: 1.2.3.4 | IPv6 example: 2001:db8::1{RESET}")
                    print(f"  {FG_WHITE}Domain example: example.com or sub.example.com (optional){RESET}")
                    print(f"  {FG_YELLOW}⚠️  Note: You can use IP or domain for realitymux{RESET}")
                    new_server_input = ask_nonempty(f"  {BOLD}Iran Server IP or Domain:{RESET}")
                    new_tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
                    
                    if ':' in new_server_input and not new_server_input.startswith('[') and not '.' in new_server_input.replace(':', ''):
                        new_server_addr = f"[{new_server_input}]:{new_tport}"
                    else:
                        new_server_addr = f"{new_server_input}:{new_tport}"
                else:
                    print(f"  {FG_WHITE}IPv4 example: 1.2.3.4 | IPv6 example: 2001:db8::1{RESET}")
                    new_server_ip = ask_nonempty(f"  {BOLD}Iran Server IP:{RESET}")
                    new_tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
                    
                    if ':' in new_server_ip and not new_server_ip.startswith('['):
                        new_server_addr = f"[{new_server_ip}]:{new_tport}"
                    else:
                        new_server_addr = f"{new_server_ip}:{new_tport}"
                
                new_connection_pool = ask_int(f"  {BOLD}Connection Pool:{RESET} {FG_WHITE}(recommended: 8-16){RESET}", min_=1, max_=100, default=8)
                new_retry_interval = ask_int(f"  {BOLD}Retry Interval:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=60, default=3)
                new_dial_timeout = ask_int(f"  {BOLD}Dial Timeout:{RESET} {FG_WHITE}(seconds){RESET}", min_=1, max_=60, default=10)
                new_aggressive_pool = ask_yesno(f"  {BOLD}Aggressive Pool?{RESET} {FG_WHITE}(faster reconnect){RESET}", default=False)

                new_path_dict = {
                    "addr": new_server_addr,
                    "transport": new_transport,
                    "connection_pool": new_connection_pool,
                    "retry_interval": new_retry_interval,
                    "dial_timeout": new_dial_timeout,
                    "aggressive_pool": new_aggressive_pool
                }
                if new_transport in ("wsmux", "wssmux"):
                    _ep = ask_edge_ip_optional("Cloudflare")
                    if _ep:
                        new_path_dict["edge_ip"] = _ep
                        c_ok(f"  ✅ Edge IP set: {FG_CYAN}{_ep}{RESET}")
                if new_transport == "realitymux" and new_reality_sni and new_reality_fingerprint:
                    new_path_dict["reality_sni"] = new_reality_sni
                    new_path_dict["reality_fingerprint"] = new_reality_fingerprint
                
                paths.append(new_path_dict)
                
                print(f"  {FG_GREEN}✅ Backup server added:{RESET} {FG_CYAN}{new_transport}://{new_server_addr}{RESET} {FG_WHITE}({new_connection_pool} connections){RESET}")
        

        _section("ADVANCED")
        verbose = ask_yesno(f"  {BOLD}Verbose logging{RESET}", default=False)
        heartbeat = ask_int(f"  {BOLD}Heartbeat Interval:{RESET}", min_=1, max_=300, default=DEFAULT_HEARTBEAT)

        _section("PERFORMANCE")
        if ask_yesno(f"  {BOLD}Custom compression{RESET}", default=False):
            compression_config = configure_compression()
        else:
            compression_config = {
                "enabled": True,
                "algorithm": "lz4",
                "level": 0,
                "min_size": 1024,
                "max_size": 65536
            }

        if ask_yesno(f"  {BOLD}Custom buffer pools{RESET}", default=False):
            buffer_pool_config = configure_buffer_pools()
        else:
            buffer_pool_config = {
                "buffer_pool_size": DEFAULT_BUFFER_POOL_SIZE,
                "large_buffer_pool_size": DEFAULT_LARGE_BUFFER_POOL_SIZE,
                "udp_frame_pool_size": DEFAULT_UDP_FRAME_POOL_SIZE,
                "udp_data_slice_size": DEFAULT_UDP_SLICE_SIZE
            }

        _section("TUN")
        tun_enabled = ask_yesno(f"  {BOLD}Enable TUN mode{RESET}", default=False)

        tun_config = None
        if tun_enabled:
            tun_name = ask_nonempty(f"  {BOLD}Interface Name:{RESET}", default="netrix0")
            tun_local = ask_nonempty(f"  {BOLD}Local IP (CIDR):{RESET}", default="10.200.0.2/30")
            tun_mtu = ask_int(f"  {BOLD}MTU:{RESET}", min_=576, max_=9000, default=1400)
            tun_routes = []
            while True:
                try:
                    route = input(_input_prompt("Route [empty=done]")).strip()
                except KeyboardInterrupt:
                    exit_script()
                if not route:
                    break
                tun_routes.append(route)
                c_ok(f"Route added: {route}")
            tun_streams = ask_int(f"  {BOLD}TUN Streams:{RESET}", min_=1, max_=64, default=4)
            tun_config = {
                "enabled": True,
                "name": tun_name,
                "local": tun_local,
                "mtu": tun_mtu,
                "routes": tun_routes,
                "streams": tun_streams
            }
            c_ok(f"TUN: {tun_name} ({tun_local})")

        _section("PROXY PROTOCOL")
        proxy_protocol_enabled = ask_yesno(f"  {BOLD}Enable PROXY protocol{RESET}", default=False)
        proxy_protocol_version = "v1"
        if proxy_protocol_enabled:
            print(f"  {FG_CYAN}[1]{RESET} {FG_WHITE}v1{RESET}")
            print(f"  {FG_CYAN}[2]{RESET} {FG_WHITE}v2{RESET}")
            version_choice = ask_int(f"  {BOLD}Version{RESET}", min_=1, max_=2, default=1)
            proxy_protocol_version = "v1" if version_choice == 1 else "v2"
            c_ok(f"PROXY Protocol: {proxy_protocol_version}")
        else:
            c_ok("PROXY Protocol disabled")
        rawsocket_interface = ""
        rawsocket_local_ip = ""
        rawsocket_router_mac = ""
        rawsocket_local_flags = []
        rawsocket_remote_flags = []
        if transport in ("rawsocket", "rawmux"):
            detected = detect_rawsocket_pcap_defaults()
            rawsocket_interface = detected.get("interface") or ""
            rawsocket_local_ip = detected.get("local_ip") or ""
            rawsocket_router_mac = detected.get("router_mac") or ""
            rawsocket_local_flags = detected.get("local_flags") or []
            rawsocket_remote_flags = detected.get("remote_flags") or []
            parts = []
            if rawsocket_interface:
                parts.append(f"interface={rawsocket_interface}")
            if rawsocket_local_ip:
                parts.append(f"local_ip={rawsocket_local_ip}")
            if rawsocket_router_mac:
                parts.append(f"router_mac={rawsocket_router_mac}")
            if parts:
                print(f"\n  {FG_GREEN}✅ rawsocket/pcap: auto-detected → {FG_WHITE}{', '.join(parts)}{RESET} (written to config)")
            else:
                print(f"\n  {FG_GREEN}✅ rawsocket/pcap: defaults (netrix will auto-detect at runtime){RESET}")
        
        cfg = {
            "psk": psk,
            "profile": profile,
            "mux_con": mux_con,
            "paths": paths,
            "direct": direct_mode,
            "listen": listen_addr,
            "transport": transport,
            "reality_sni": reality_sni,
            "reality_fingerprint": reality_fingerprint,
            "tls_insecure_skip_verify": tls_insecure_skip_verify,
            "verbose": verbose,
            "heartbeat": heartbeat,
            "compression_config": compression_config,
            "buffer_pool_config": buffer_pool_config,
            "encryption_enabled": encryption_enabled,
            "encryption_algorithm": encryption_algorithm,
            "encryption_key": encryption_key,
            "stealth_padding": stealth_padding,
            "stealth_padding_min": stealth_padding_min,
            "stealth_padding_max": stealth_padding_max,
            "stealth_jitter": stealth_jitter,
            "stealth_jitter_min": stealth_jitter_min,
            "stealth_jitter_max": stealth_jitter_max,
            "anti_dpi_delay_ms": anti_dpi_delay_ms,
            "tun_config": tun_config,
            "proxy_protocol_enabled": proxy_protocol_enabled,
            "proxy_protocol_version": proxy_protocol_version,
            "proxy_protocol_ports": [],
        }
        
        if cert_file and key_file:
            cfg["cert_file"] = cert_file
            cfg["key_file"] = key_file
            print(f"  {FG_GREEN}✅ Certificate files added to config: cert={cert_file}, key={key_file}{RESET}")
        elif transport in ("tlsmux", "wssmux", "realitymux") and direct_mode:
            print(f"  {FG_YELLOW}⚠️  Option 3 selected – self-signed will be used. Ensure Iran server has «accept self-signed» enabled.{RESET}")
        if transport in ("rawsocket", "rawmux"):
            cfg["rawsocket_interface"] = rawsocket_interface
            cfg["rawsocket_local_ip"] = rawsocket_local_ip
            cfg["rawsocket_router_mac"] = rawsocket_router_mac
            cfg["rawsocket_local_flags"] = rawsocket_local_flags
            cfg["rawsocket_remote_flags"] = rawsocket_remote_flags
        
        config_path = create_client_config_file(cfg)
        
        print()
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        c_ok(f"  ✅ Configuration saved: {FG_WHITE}{config_path}{RESET}")
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        
        print()
        if ask_yesno(f"  {BOLD}{FG_CYAN}Start tunnel now?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
            if run_tunnel(config_path):
                c_ok(f"  ✅ Tunnel started successfully!")
            else:
                c_err("  ❌ Failed to start tunnel!")
        
        pause()
    except UserCancelled:
        exit_script()

def status_menu():
    """Tunnel status dashboard."""
    while True:
        clear()
        try:
            items = list_tunnels()
        except KeyboardInterrupt:
            exit_script()

        summary_lines = [
            f"{FG_WHITE}Tracked configs:{RESET} {FG_CYAN}{len(items)}{RESET}",
            f"{FG_WHITE}Active services:{RESET} {FG_GREEN}{sum(1 for it in items if it.get('alive'))}{RESET}",
            f"{FG_WHITE}Stopped services:{RESET} {FG_RED}{sum(1 for it in items if not it.get('alive'))}{RESET}",
        ]
        _brand_box("Tunnel Status", "", summary_lines, accent=FG_BLUE)
        print()

        if not items:
            c_warn("No tunnels found.")
            pause()
            return

        for i, it in enumerate(items, 1):
            alive = it.get("alive")
            icon = f"{FG_GREEN}●{RESET}" if alive else f"{FG_RED}●{RESET}"
            state = f"{FG_GREEN}ACTIVE{RESET}" if alive else f"{FG_RED}STOPPED{RESET}"
            print(f"  {BOLD}{FG_CYAN}[{i}]{RESET} {icon} {BOLD}{state}{RESET}  {FG_WHITE}{it['summary']}{RESET}")
            print(f"      {DIM}{FG_WHITE}Config:{RESET} {FG_CYAN}{it['config_path'].name}{RESET}")

        print()
        _menu_line("0", "Back", "Return to the previous menu", accent=FG_WHITE)
        print()
        try:
            choice = input(_input_prompt("Select tunnel")).strip()
        except KeyboardInterrupt:
            exit_script()

        if choice == "0":
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                it = items[idx]
                config_path = it.get("config_path")
                if not config_path:
                    c_err("Invalid selection.")
                    pause()
                    continue
                view_tunnel_details(config_path, it)
            else:
                c_err("Invalid selection.")
                pause()
        except ValueError:
            c_err("Invalid input. Please enter a number.")
            pause()

def view_tunnel_details(config_path: Path, tunnel: Dict[str,Any]):
    """Display details and logs for a selected tunnel."""
    while True:
        clear()
        alive = tunnel.get("alive")
        cfg = tunnel.get('cfg', {})
        mode = cfg.get('mode', 'unknown')
        summary_lines = [
            f"{FG_WHITE}Status:{RESET} " + (f"{FG_GREEN}ACTIVE{RESET}" if alive else f"{FG_RED}STOPPED{RESET}"),
            f"{FG_WHITE}Mode:{RESET} {FG_CYAN}{mode}{RESET}    {FG_WHITE}Transport:{RESET} {FG_MAGENTA}{cfg.get('transport', 'unknown')}{RESET}",
            f"{FG_WHITE}Config:{RESET} {FG_CYAN}{config_path}{RESET}",
        ]
        _brand_box("Tunnel Details", "", summary_lines, accent=FG_MAGENTA)
        print()

        if mode == 'server':
            print(f"  {FG_WHITE}Listen:{RESET} {FG_GREEN}{cfg.get('listen', 'unknown')}{RESET}")
        else:
            paths = cfg.get('paths', [])
            if paths:
                print(f"  {FG_WHITE}Configured paths:{RESET} {FG_GREEN}{len(paths)}{RESET}")
        print()
        _menu_line("1", "Service Logs", "Read the persistent systemd journal entries", accent=FG_BLUE)
        _menu_line("2", "Live Logs", "Attach to the live log stream", accent=FG_MAGENTA)
        _menu_line("3", "Health Check", "Run the built-in connectivity and health probes", accent=FG_GREEN)
        print()
        _menu_line("0", "Back", "Return to the status list", accent=FG_WHITE)
        print()
        try:
            choice = input(_input_prompt("Choose an action")).strip()
        except KeyboardInterrupt:
            exit_script()

        if choice == "0":
            break
        elif choice == "1":
            view_service_logs(config_path)
        elif choice == "2":
            view_live_logs(config_path)
        elif choice == "3":
            check_tunnel_health(config_path)
        else:
            c_err("Invalid choice.")
            pause()

def view_service_logs(config_path: Path):
    """نمایش لاگ systemd service"""
    service_name = f"netrix-{config_path.stem}"
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{FG_CYAN}║{RESET}                     {BOLD}Service Logs{RESET}                         {BOLD}{FG_CYAN}║{RESET}")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  {BOLD}Service:{RESET} {service_name}")
    print()
    
    try:
        result = subprocess.run(
            ["journalctl", "-u", service_name, "-n", "50", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            c_err(f"Error reading logs: {result.stderr}")
    except subprocess.TimeoutExpired:
        c_err("Timeout reading logs (service may be slow)")
    except Exception as e:
        c_err(f"Error: {e}")
    
    pause()

def view_live_logs(config_path: Path):
    """نمایش لاگ لحظه‌ای (live log)"""
    service_name = f"netrix-{config_path.stem}"
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{FG_CYAN}║{RESET}                        {BOLD}Live Logs{RESET}                         {BOLD}{FG_CYAN}║{RESET}")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  {BOLD}Service:{RESET} {service_name}")
    print(f"  {FG_YELLOW}Press Ctrl+C to stop...{RESET}")
    print()
    
    try:
        subprocess.run(["journalctl", "-u", service_name, "-f"], check=False)
    except KeyboardInterrupt:
        exit_script()
    except Exception as e:
        c_err(f"  ❌ Error: {FG_RED}{e}{RESET}")
        pause()

def get_tunnel_health_port(cfg: Optional[Dict[str, Any]]) -> int:
    """Resolve the effective health port across transports and config layouts."""
    if not cfg:
        return 19080
    transport = str(cfg.get("transport") or "").strip().lower()
    tun_cfg = cfg.get("tun") or {}
    if transport == "l3":
        return int(tun_cfg.get("health_port", cfg.get("health_port", 1234)) or 1234)
    return int(cfg.get("health_port", tun_cfg.get("health_port", 19080)) or 19080)


def check_tunnel_health(config_path: Path):
    """بررسی وضعیت health check endpoint — هماهنگ با ساختار پاسخ هسته (/health و /health/detailed)"""
    service_name = f"netrix-{config_path.stem}"
    pid = get_service_pid(config_path)
    
    cfg = parse_yaml_config(config_path)
    health_port = get_tunnel_health_port(cfg)
    
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{FG_CYAN}║{RESET}                     {BOLD}Health Check{RESET}                         {BOLD}{FG_CYAN}║{RESET}")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    if not pid:
        c_err("  ❌ Tunnel is not running")
        pause()
        return
    
    print(f"  {BOLD}Service:{RESET} {service_name}")
    print(f"  {BOLD}PID:{RESET} {pid}")
    print(f"  {BOLD}Health Port:{RESET} {health_port}")
    print()
    
    base = f"http://localhost:{health_port}"
    health_urls = [
        (f"{base}/health", "Simple Health Check"),
        (f"{base}/health/detailed", "Detailed Health Check"),
    ]
    
    for url, name in health_urls:
        print(f"  {BOLD}{FG_CYAN}{name}:{RESET}")
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Netrix-Script/1.0")
            with urllib.request.urlopen(req, timeout=3) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
                
                if status_code == 200:
                    if name == "Simple Health Check":
                        print(f"    {FG_GREEN}✅ Status: OK{RESET}")
                        _print_simple_health(body)
                    else:
                        _print_detailed_health(body)
                else:
                    print(f"    {FG_RED}❌ Status: {status_code}{RESET}")
                    print(f"    {FG_WHITE}Response: {body.strip()}{RESET}")
        except urllib.error.HTTPError as e:
            print(f"    {FG_RED}❌ HTTP Error: {e.code}{RESET}")
            if e.code == 503:
                print(f"    {FG_YELLOW}Service is unavailable (may be shutting down or no sessions){RESET}")
        except urllib.error.URLError as e:
            print(f"    {FG_RED}❌ Connection Error: {e.reason}{RESET}")
            print(f"    {FG_YELLOW}⚠️  Health server may not be running on port {health_port}{RESET}")
        except Exception as e:
            print(f"    {FG_RED}❌ Error: {e}{RESET}")
        print()
    
    pause()

def tunnel_health_check(config_path: Path, tunnel: Dict[str,Any] | None = None):
    return check_tunnel_health(config_path)

def _print_simple_health(body: str):
    """Parse and print /health (simple) without dumping raw JSON."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(f"    {FG_WHITE}Response: {body.strip()}{RESET}")
        return

    def _fmt_unix_ns(ns_val) -> str:
        try:
            ns = int(ns_val)
        except Exception:
            return ""
        if ns <= 0:
            return ""
        now_ns = time.time_ns()
        age_ns = max(0, now_ns - ns)
        age_s = age_ns / 1_000_000_000.0
        try:
            dt = datetime.datetime.fromtimestamp(ns / 1_000_000_000.0)
            wall = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            wall = str(ns)
        return f"{wall}  ({age_s:.1f}s ago)"

    active = bool(data.get("active", False))
    ready = bool(data.get("ready", False))
    peer_transport_up = bool(data.get("peer_transport_up", False))
    peer_data_verified = bool(data.get("peer_data_verified", False))

    local = data.get("local", "")
    remote = data.get("remote", "")
    mtu = data.get("mtu", 0)
    streams = data.get("streams", 0)
    active_l3_peers = data.get("active_l3_peers", 0)

    print(f"    {BOLD}Active:{RESET} {FG_GREEN if active else FG_YELLOW}{'YES' if active else 'NO'}{RESET}")
    print(f"    {BOLD}Ready:{RESET} {FG_GREEN if ready else FG_YELLOW}{'YES' if ready else 'NO'}{RESET}")
    if peer_transport_up or peer_data_verified:
        print(f"    {BOLD}Peer Transport:{RESET} {FG_GREEN if peer_transport_up else FG_YELLOW}{'UP' if peer_transport_up else 'DOWN'}{RESET}")
        print(f"    {BOLD}Peer Data Verified:{RESET} {FG_GREEN if peer_data_verified else FG_YELLOW}{'YES' if peer_data_verified else 'NO'}{RESET}")
    if local or remote:
        print(f"    {BOLD}Local:{RESET}  {FG_CYAN}{local}{RESET}")
        print(f"    {BOLD}Remote:{RESET} {FG_CYAN}{remote}{RESET}")
    if mtu:
        print(f"    {BOLD}MTU:{RESET} {FG_CYAN}{mtu}{RESET}")
    print(f"    {BOLD}Streams:{RESET} {FG_CYAN}{streams}{RESET}  {FG_WHITE}(active_l3_peers={active_l3_peers}){RESET}")



def _print_detailed_health(body: str):
    """پارس و نمایش پاسخ /health/detailed — سازگار با ساختار JSON هسته"""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(f"    {FG_WHITE}Response: {body[:200]}{RESET}")
        return
    
    status = data.get("status", "unknown")
    stats = data.get("stats") or {}
    
    sessions = data.get("sessions") if "sessions" in data else stats.get("sessions_active", 0)
    streams = data.get("streams") if "streams" in data else (data.get("streams_data") if "streams_data" in data else stats.get("streams_active", 0))
    rtt_ms = stats.get("rtt_current_ms", data.get("rtt_ms", 0))
    
    rtt_val = float(rtt_ms) if rtt_ms is not None else 0.0
    status_color = FG_GREEN if status == "healthy" else (FG_YELLOW if status in ("warning", "degraded", "connected", "no_streams", "disconnected") else FG_RED)
    print(f"    {BOLD}Status:{RESET} {status_color}{status.upper()}{RESET}")
    print(f"    {BOLD}Sessions:{RESET} {FG_CYAN}{sessions}{RESET}")
    print(f"    {BOLD}Streams:{RESET} {FG_CYAN}{streams}{RESET}")
    print(f"    {BOLD}RTT:{RESET} {FG_CYAN}{rtt_val:.1f} ms{RESET}")

    if "ready" in data:
        ready = bool(data.get("ready"))
        print(f"    {BOLD}Ready:{RESET} {FG_GREEN if ready else FG_YELLOW}{'YES' if ready else 'NO'}{RESET}")
    if "peer_transport_up" in data:
        ptu = bool(data.get("peer_transport_up"))
        print(f"    {BOLD}Peer Transport:{RESET} {FG_GREEN if ptu else FG_YELLOW}{'UP' if ptu else 'DOWN'}{RESET}")
    if "peer_data_verified" in data:
        pdv = bool(data.get("peer_data_verified"))
        print(f"    {BOLD}Peer Data Verified:{RESET} {FG_GREEN if pdv else FG_YELLOW}{'YES' if pdv else 'NO'}{RESET}")
    
    tcp_in = stats.get("tcp_bytes_in", 0) or 0
    tcp_out = stats.get("tcp_bytes_out", 0) or 0
    udp_in = stats.get("udp_bytes_in", 0) or 0
    udp_out = stats.get("udp_bytes_out", 0) or 0
    
    if "tcp_in" in data and isinstance(data.get("tcp_in"), dict) and "formatted" in data["tcp_in"]:
        print(f"    {BOLD}TCP In:{RESET} {FG_CYAN}{data['tcp_in']['formatted']}{RESET}")
        print(f"    {BOLD}TCP Out:{RESET} {FG_CYAN}{data['tcp_out']['formatted']}{RESET}")
        print(f"    {BOLD}UDP In:{RESET} {FG_CYAN}{data['udp_in']['formatted']}{RESET}")
        print(f"    {BOLD}UDP Out:{RESET} {FG_CYAN}{data['udp_out']['formatted']}{RESET}")
    elif tcp_in or tcp_out or udp_in or udp_out:
        print(f"    {BOLD}TCP In:{RESET}  {FG_CYAN}{format_bytes(tcp_in)}{RESET}")
        print(f"    {BOLD}TCP Out:{RESET} {FG_CYAN}{format_bytes(tcp_out)}{RESET}")
        print(f"    {BOLD}UDP In:{RESET}  {FG_CYAN}{format_bytes(udp_in)}{RESET}")
        print(f"    {BOLD}UDP Out:{RESET} {FG_CYAN}{format_bytes(udp_out)}{RESET}")
        total = tcp_in + tcp_out + udp_in + udp_out
        if total:
            print(f"    {BOLD}Total:{RESET}   {FG_GREEN}{format_bytes(total)}{RESET}")
    
    if data.get("warning"):
        print(f"    {FG_YELLOW}⚠️  Warning: {data['warning']}{RESET}")

def stop_tunnel_menu():
    """Stop an active tunnel."""
    clear()
    items = list_tunnels()
    active_items = [it for it in items if it.get("alive")]
    _brand_box("Stop Tunnel", "", [
        f"{FG_WHITE}Active tunnels:{RESET} {FG_GREEN}{len(active_items)}{RESET}",
        f"{FG_WHITE}Safety:{RESET} {FG_YELLOW}Only running services are listed here{RESET}",
    ], accent=FG_YELLOW)
    print()

    if not items:
        c_warn("No tunnels found.")
        pause()
        return
    if not active_items:
        c_warn("No active tunnels to stop.")
        pause()
        return

    for i, it in enumerate(active_items, 1):
        _menu_line(str(i), it['summary'], "Running now", accent=FG_YELLOW)

    print()
    _menu_line("0", "Back", "Return without making changes", accent=FG_WHITE)
    print()
    try:
        choice = input(_input_prompt("Select tunnel to stop")).strip()
    except KeyboardInterrupt:
        exit_script()

    if choice == "0":
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(active_items):
            it = active_items[idx]
            config_path = it.get("config_path")
            print(f"\n  {FG_CYAN}Stopping service...{RESET}", end='', flush=True)
            if stop_tunnel(config_path):
                print(f" {FG_GREEN}✅{RESET}")
                print(f"  {FG_CYAN}Cleaning iptables rules...{RESET}", end='', flush=True)
                if cleanup_iptables_rules(config_path):
                    print(f" {FG_GREEN}✅{RESET}")
                else:
                    print(f" {FG_YELLOW}⚠️{RESET}")
                c_ok("Tunnel stopped successfully.")
            else:
                print(f" {FG_RED}❌{RESET}")
                c_err("Failed to stop tunnel.")
        else:
            c_err("Invalid selection.")
    except ValueError:
        c_err("Invalid input. Please enter a number.")
    except Exception as e:
        c_err(f"Error: {e}")
    pause()

def restart_tunnel_menu():
    """Restart a tunnel service."""
    clear()
    items = list_tunnels()
    _brand_box("Restart Tunnel", "", [
        f"{FG_WHITE}Known tunnels:{RESET} {FG_CYAN}{len(items)}{RESET}",
        f"{FG_WHITE}Tip:{RESET} {FG_WHITE}Use restart after changing configs or routing rules{RESET}",
    ], accent=FG_MAGENTA)
    print()

    if not items:
        c_warn("No tunnels found.")
        pause()
        return

    for i, it in enumerate(items, 1):
        state = "running" if it.get("alive") else "stopped"
        _menu_line(str(i), it['summary'], f"Current state: {state}", accent=FG_MAGENTA)

    print()
    _menu_line("0", "Back", "Return without restarting anything", accent=FG_WHITE)
    print()
    try:
        choice = input(_input_prompt("Select tunnel to restart")).strip()
    except KeyboardInterrupt:
        exit_script()

    if choice == "0":
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            it = items[idx]
            config_path = it.get("config_path")
            print(f"\n  {FG_CYAN}Restarting service...{RESET}", end='', flush=True)
            if restart_tunnel(config_path):
                print(f" {FG_GREEN}✅{RESET}")
                c_ok("Tunnel restarted successfully.")
            else:
                print(f" {FG_RED}❌{RESET}")
                c_err("Failed to restart tunnel.")
        else:
            c_err("Invalid selection.")
    except ValueError:
        c_err("Invalid input. Please enter a number.")
    except Exception as e:
        c_err(f"Error: {e}")
    pause()

def delete_tunnel_menu():
    """Delete a tunnel config and service."""
    clear()
    items = list_tunnels()
    _brand_box("Delete Tunnel", "", [
        f"{FG_WHITE}Known tunnels:{RESET} {FG_CYAN}{len(items)}{RESET}",
        f"{FG_WHITE}Warning:{RESET} {FG_RED}Deletion also removes the saved YAML config{RESET}",
    ], accent=FG_RED)
    print()

    if not items:
        c_warn("No tunnels found.")
        pause()
        return

    for i, it in enumerate(items, 1):
        desc = f"Config: {it['config_path'].name}"
        _menu_line(str(i), it['summary'], desc, accent=FG_RED)

    print()
    _menu_line("0", "Back", "Return without deleting anything", accent=FG_WHITE)
    print()
    try:
        choice = input(_input_prompt("Select tunnel to delete")).strip()
    except KeyboardInterrupt:
        exit_script()

    if choice == "0":
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            it = items[idx]
            config_path = it.get("config_path")
            if not ask_yesno(f"  {BOLD}{FG_RED}Delete {FG_YELLOW}{config_path.name}{FG_RED} permanently?{RESET}", default=False):
                return

            print(f"\n  {FG_CYAN}Removing selected tunnel...{RESET}")
            if it.get("alive"):
                print(f"  {FG_CYAN}Stopping service...{RESET}", end='', flush=True)
                if stop_tunnel(config_path):
                    print(f" {FG_GREEN}✅{RESET}")
                else:
                    print(f" {FG_YELLOW}⚠️{RESET}")
            print(f"  {FG_CYAN}Cleaning rules...{RESET}", end='', flush=True)
            if cleanup_iptables_rules(config_path):
                print(f" {FG_GREEN}✅{RESET}")
            else:
                print(f" {FG_YELLOW}⚠️{RESET}")
            print(f"  {FG_CYAN}Removing service unit...{RESET}", end='', flush=True)
            if delete_service_for_tunnel(config_path):
                print(f" {FG_GREEN}✅{RESET}")
            else:
                print(f" {FG_YELLOW}⚠️{RESET}")
            print(f"  {FG_CYAN}Deleting config file...{RESET}", end='', flush=True)
            try:
                config_path.unlink()
                print(f" {FG_GREEN}✅{RESET}")
                c_ok(f"Tunnel deleted: {config_path.name}")
            except Exception as e:
                print(f" {FG_RED}❌{RESET}")
                c_err(f"Failed to delete config file: {e}")
        else:
            c_err("Invalid selection.")
    except ValueError:
        c_err("Invalid input. Please enter a number.")
    except Exception as e:
        c_err(f"Error: {e}")
    pause()

def core_management_menu():
    """Manage Netrix core installation and updates."""
    while True:
        clear()
        binary_exists = Path(NETRIX_BINARY).exists()
        version_info = "Unknown"
        if binary_exists:
            try:
                result = subprocess.run([NETRIX_BINARY, "-version"], capture_output=True, text=True, timeout=5)
                version_info = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "Unknown"
            except Exception:
                version_info = "Unknown"

        lines = [
            f"{FG_WHITE}Binary:{RESET} {FG_CYAN}{NETRIX_BINARY}{RESET}",
            f"{FG_WHITE}Status:{RESET} " + (f"{FG_GREEN}Installed{RESET}" if binary_exists else f"{FG_RED}Not installed{RESET}"),
            f"{FG_WHITE}Version:{RESET} {FG_GREEN}{version_info}{RESET}" if binary_exists else f"{FG_WHITE}Version:{RESET} {FG_YELLOW}Unavailable{RESET}",
            f"{FG_WHITE}GitHub:{RESET} {FG_CYAN}{_repo_from_release()}{RESET}",
        ]
        _brand_box("Core Management", "", lines, accent=FG_CYAN)
        print()
        _menu_line("1", "Install Netrix Core", accent=FG_CYAN)
        if binary_exists:
            _menu_line("2", "Update Netrix Core", accent=FG_CYAN)
            _menu_line("3", "Delete Netrix Core", accent=FG_CYAN)
        print()
        _menu_line("0", "Back", accent=FG_WHITE)
        print()
        try:
            choice = input(_input_prompt("Choose an action")).strip()
        except KeyboardInterrupt:
            exit_script()

        if choice == "0":
            return
        elif choice == "1":
            install_netrix_core()
        elif choice == "2" and binary_exists:
            update_netrix_core()
        elif choice == "3" and binary_exists:
            delete_netrix_core()
        else:
            c_err("Invalid choice.")
            pause()

def install_netrix_core():
    """نصب هسته Netrix"""
    try:
        _wizard_intro("INSTALL NETRIX CORE", "")
        
        if Path(NETRIX_BINARY).exists():
            c_warn("  Netrix Core is already installed!")
            if not ask_yesno(f"  {BOLD}Do you want to reinstall?{RESET}", default=False):
                return
        
        print(f"  {FG_CYAN}Detecting system architecture...{RESET}")
        arch = platform.machine().lower()
        
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv7l": "arm",
            "armv6l": "arm"
        }
        
        go_arch = arch_map.get(arch, "amd64")
        print(f"  {BOLD}Architecture:{RESET} {FG_GREEN}{arch} {FG_WHITE}({go_arch}){RESET}")
        
        download_url = NETRIX_RELEASE_URLS.get(go_arch)
        if not download_url:
            c_err(f"  ❌ Unsupported architecture: {go_arch}")
            c_warn(f"  Supported: amd64 (x86_64), arm64 (aarch64)")
            pause()
            return
        
        print(f"\n  {BOLD}{FG_CYAN}Download URL:{RESET} {FG_GREEN}{download_url}{RESET}")
        
        print(f"\n  {FG_CYAN}Downloading Netrix Core from:{RESET} {FG_GREEN}{download_url}{RESET}")
        temp_file = Path("/tmp/netrix.tar.gz")
        temp_dir = Path("/tmp/netrix_extract")
        
        try:
            print(f"  {FG_CYAN}⏳ Downloading...{RESET}")
            req = urllib.request.Request(download_url)
            req.add_header("User-Agent", "Netrix-Installer/1.0")
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
            
            file_size = temp_file.stat().st_size
            if file_size < 1024:
                raise Exception("Downloaded file is too small, may be corrupted")
            
            c_ok(f"  ✅ Download completed {FG_WHITE}({file_size / 1024 / 1024:.2f} MB){RESET}")
        except urllib.error.URLError as e:
            c_err(f"  ❌ Failed to download: {FG_RED}Network error - {str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            pause()
            return
        except Exception as e:
            c_err(f"  ❌ Failed to download: {FG_RED}{str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            pause()
            return
        
        print(f"\n  {FG_CYAN}Extracting archive...{RESET}")
        try:
            import tarfile
            
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(temp_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            c_ok(f"  ✅ Archive extracted")
            
            netrix_file = None
            for file in temp_dir.rglob("netrix"):
                if file.is_file():
                    netrix_file = file
                    break
            
            if not netrix_file:
                raise Exception("netrix binary not found in archive")
            
        except Exception as e:
            c_err(f"  ❌ Failed to extract: {FG_RED}{str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            pause()
            return

        print(f"\n  {FG_CYAN}Installing Netrix Core to {NETRIX_BINARY}...{RESET}")
        try:
            binary_dir = Path(NETRIX_BINARY).parent
            binary_dir.mkdir(parents=True, exist_ok=True)
            
            if Path(NETRIX_BINARY).exists():
                backup_file = Path(f"{NETRIX_BINARY}.backup")
                shutil.copy(NETRIX_BINARY, backup_file)
                print(f"  {FG_YELLOW}Old version backed up to: {backup_file}{RESET}")
            
            shutil.copy(netrix_file, NETRIX_BINARY)
            
            os.chmod(NETRIX_BINARY, 0o755)
            
            temp_file.unlink()
            shutil.rmtree(temp_dir)
            
            c_ok(f"  ✅ Netrix Core installed successfully!")
            c_ok(f"  ✅ Binary location: {FG_GREEN}{NETRIX_BINARY}{RESET}")
            try:
                try:
                    with urllib.request.urlopen("https://api.ipify.org", timeout=3) as response:
                        public_ip = response.read().decode().strip()
                        c_ok(f"  ✅ Server Public IP: {FG_GREEN}{public_ip}{RESET}")
                except:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    c_ok(f"  ✅ Server Local IP: {FG_GREEN}{local_ip}{RESET}")
            except Exception:
                pass  
            
        except Exception as e:
            c_err(f"  ❌ Failed to install: {FG_RED}{str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            pause()
            return
        
        print(f"\n  {FG_CYAN}Verifying installation...{RESET}")
        try:
            result = subprocess.run([NETRIX_BINARY, "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  {BOLD}Version Info:{RESET}")
                print(f"  {FG_GREEN}{result.stdout}{RESET}")
                c_ok("  ✅ Installation verified successfully!")
            else:
                c_warn("  ⚠️  Could not verify version, but installation completed.")
        except Exception as e:
            c_warn(f"  ⚠️  Could not verify installation: {str(e)}")
        
        pause()
    except UserCancelled:
        exit_script()

def install_netrix_core_auto():
    """نصب/Reinstall خودکار هسته Netrix بدون سوال (برای update)"""
    try:
        print(f"  {FG_CYAN}Detecting system architecture...{RESET}")
        arch = platform.machine().lower()
        
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv7l": "arm",
            "armv6l": "arm"
        }
        
        go_arch = arch_map.get(arch, "amd64")
        print(f"  {BOLD}Architecture:{RESET} {FG_GREEN}{arch} {FG_WHITE}({go_arch}){RESET}")
        
        download_url = NETRIX_RELEASE_URLS.get(go_arch)
        if not download_url:
            c_err(f"  ❌ Unsupported architecture: {go_arch}")
            c_warn(f"  Supported: amd64 (x86_64), arm64 (aarch64)")
            return False
        
        print(f"\n  {BOLD}{FG_CYAN}Download URL:{RESET} {FG_GREEN}{download_url}{RESET}")
        
        print(f"\n  {FG_CYAN}Downloading Netrix Core...{RESET}")
        temp_file = Path("/tmp/netrix.tar.gz")
        temp_dir = Path("/tmp/netrix_extract")
        
        try:
            print(f"  {FG_CYAN}⏳ Downloading...{RESET}")
            req = urllib.request.Request(download_url)
            req.add_header("User-Agent", "Netrix-Installer/1.0")
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
            
            file_size = temp_file.stat().st_size
            if file_size < 1024:
                raise Exception("Downloaded file is too small, may be corrupted")
            
            c_ok(f"  ✅ Download completed {FG_WHITE}({file_size / 1024 / 1024:.2f} MB){RESET}")
        except urllib.error.URLError as e:
            c_err(f"  ❌ Failed to download: {FG_RED}Network error - {str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            return False
        except Exception as e:
            c_err(f"  ❌ Failed to download: {FG_RED}{str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            return False
        
        print(f"\n  {FG_CYAN}Extracting archive...{RESET}")
        try:
            import tarfile
            
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(temp_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            c_ok(f"  ✅ Archive extracted")
            
            netrix_file = None
            for file in temp_dir.rglob("netrix"):
                if file.is_file():
                    netrix_file = file
                    break
            
            if not netrix_file:
                raise Exception("netrix binary not found in archive")
            
        except Exception as e:
            c_err(f"  ❌ Failed to extract: {FG_RED}{str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return False

        print(f"\n  {FG_CYAN}Installing Netrix Core to {NETRIX_BINARY}...{RESET}")
        try:
            binary_dir = Path(NETRIX_BINARY).parent
            binary_dir.mkdir(parents=True, exist_ok=True)
            
            if Path(NETRIX_BINARY).exists():
                backup_file = Path(f"{NETRIX_BINARY}.backup")
                shutil.copy(NETRIX_BINARY, backup_file)
                print(f"  {FG_YELLOW}Old version backed up to: {backup_file}{RESET}")
            
            shutil.copy(netrix_file, NETRIX_BINARY)
            
            os.chmod(NETRIX_BINARY, 0o755)
            
            temp_file.unlink()
            shutil.rmtree(temp_dir)
            
            c_ok(f"  ✅ Netrix Core installed successfully!")
            c_ok(f"  ✅ Binary location: {FG_GREEN}{NETRIX_BINARY}{RESET}")
            
            try:
                try:
                    with urllib.request.urlopen("https://api.ipify.org", timeout=3) as response:
                        public_ip = response.read().decode().strip()
                        c_ok(f"  ✅ Server Public IP: {FG_GREEN}{public_ip}{RESET}")
                except:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    c_ok(f"  ✅ Server Local IP: {FG_GREEN}{local_ip}{RESET}")
            except Exception:
                pass
            
        except Exception as e:
            c_err(f"  ❌ Failed to install: {FG_RED}{str(e)}{RESET}")
            if temp_file.exists():
                temp_file.unlink()
            return False
        
        print(f"\n  {FG_CYAN}Verifying installation...{RESET}")
        try:
            result = subprocess.run([NETRIX_BINARY, "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  {BOLD}Version Info:{RESET}")
                print(f"  {FG_GREEN}{result.stdout}{RESET}")
                c_ok("  ✅ Installation verified successfully!")
                return True
            else:
                c_warn("  ⚠️  Could not verify version, but installation completed.")
                return True
        except Exception as e:
            c_warn(f"  ⚠️  Could not verify installation: {str(e)}")
            return True
        
    except Exception as e:
        c_err(f"  ❌ Installation failed: {FG_RED}{str(e)}{RESET}")
        return False

def update_netrix_core():
    """آپدیت هسته Netrix"""
    try:
        _wizard_intro("UPDATE NETRIX CORE", "")
        
        if not Path(NETRIX_BINARY).exists():
            c_err("  Netrix Core is not installed!")
            c_warn("  Please install Netrix Core first.")
            pause()
            return
        
        print(f"  {BOLD}Current Version:{RESET}")
        try:
            result = subprocess.run([NETRIX_BINARY, "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  {FG_GREEN}{result.stdout}{RESET}")
            else:
                print(f"  {FG_YELLOW}Could not determine current version{RESET}")
        except:
            print(f"  {FG_YELLOW}Could not determine current version{RESET}")
        
        print(f"\n  {FG_YELLOW}⚠️  This will replace the current Netrix Core installation.{RESET}")
        print(f"  {FG_YELLOW}⚠️  All active tunnels will be temporarily stopped.{RESET}")
        if not ask_yesno(f"  {BOLD}Continue with update?{RESET}", default=False):
            return
        
        print(f"\n  {FG_CYAN}Stopping all active tunnels...{RESET}")
        items = list_tunnels()
        stopped_tunnels = []
        stopped_count = 0
        for item in items:
            if item.get("alive"):
                config_path = item.get("config_path")
                if config_path:
                    stopped_tunnels.append(config_path)
                    print(f"  {FG_CYAN}Stopping {config_path.name}...{RESET}", end='', flush=True)
                    if stop_tunnel(config_path):
                        print(f" {FG_GREEN}✅{RESET}")
                        stopped_count += 1
                    else:
                        print(f" {FG_YELLOW}⚠️{RESET} (continuing anyway)")
        
        if stopped_count > 0:
            c_ok(f"  ✅ Stopped {stopped_count} tunnel(s)")
        else:
            print(f"  {FG_WHITE}No active tunnels to stop.{RESET}")
        
        print(f"\n  {FG_CYAN}Installing updated core...{RESET}")
        install_netrix_core_auto()
        
        if stopped_count > 0:
            print(f"\n  {FG_CYAN}Restarting previously active tunnels...{RESET}")
            restarted_count = 0
            failed_tunnels = []
            for config_path in stopped_tunnels:
                service_name = f"netrix-{config_path.stem}"
                service_path = Path(f"/etc/systemd/system/{service_name}.service")
                
                if not service_path.exists():
                    print(f"  {FG_YELLOW}⚠️  Service for {config_path.name} not found, recreating...{RESET}")
                    if not create_systemd_service_for_tunnel(config_path):
                        print(f"  {FG_RED}❌ Failed to create service for {config_path.name}{RESET}")
                        failed_tunnels.append(config_path.name)
                        continue
                    try:
                        subprocess.run(["systemctl", "enable", service_name], check=False, timeout=5, capture_output=True)
                    except:
                        pass
                
                print(f"  {FG_CYAN}Restarting {config_path.name}...{RESET}", end='', flush=True)
                if restart_tunnel(config_path):
                    print(f" {FG_GREEN}✅{RESET}")
                    restarted_count += 1
                else:
                    print(f" {FG_YELLOW}⚠️{RESET}")
                    failed_tunnels.append(config_path.name)
            
            if restarted_count > 0:
                c_ok(f"  ✅ Restarted {restarted_count} tunnel(s)")
            if failed_tunnels:
                c_warn(f"  ⚠️  Failed to restart {len(failed_tunnels)} tunnel(s): {', '.join(failed_tunnels)}")
                c_warn("  ⚠️  You may need to manually restart them or check service status")
            if restarted_count == 0 and stopped_count > 0:
                c_warn("  ⚠️  No tunnels were restarted (check logs and service status)")
        
    except UserCancelled:
        exit_script()

def delete_netrix_core():
    """حذف هسته Netrix"""
    try:
        _wizard_intro("DELETE NETRIX CORE", "")
        
        if not Path(NETRIX_BINARY).exists():
            c_err("  Netrix Core is not installed!")
            pause()
            return
        
        print(f"  {BOLD}Binary Path:{RESET} {FG_RED}{NETRIX_BINARY}{RESET}")
        
        try:
            result = subprocess.run([NETRIX_BINARY, "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  {BOLD}Current Version:{RESET} {FG_YELLOW}{result.stdout.strip()}{RESET}")
        except:
            pass
        
        print(f"\n  {FG_RED}⚠️  WARNING: This will permanently delete Netrix Core binary!{RESET}")
        print(f"  {FG_YELLOW}⚠️  All tunnels will be stopped and cannot be restarted.{RESET}")
        print(f"  {FG_YELLOW}⚠️  You will need to reinstall Netrix Core to use tunnels again.{RESET}")
        
        items = list_tunnels()
        active_count = sum(1 for item in items if item.get("alive"))
        if active_count > 0:
            print(f"\n  {BOLD}Active Tunnels:{RESET} {FG_YELLOW}{active_count}{RESET} tunnel(s) will be stopped")
        
        if not ask_yesno(f"\n  {BOLD}{FG_RED}Are you absolutely sure you want to delete Netrix Core?{RESET}", default=False):
            return
        
        print(f"\n  {FG_CYAN}Stopping all active tunnels...{RESET}")
        stopped_count = 0
        for item in items:
            if item.get("alive"):
                config_path = item.get("config_path")
                if config_path:
                    print(f"  {FG_CYAN}Stopping {config_path.name}...{RESET}", end='', flush=True)
                    if stop_tunnel(config_path):
                        print(f" {FG_GREEN}✅{RESET}")
                        stopped_count += 1
                    else:
                        print(f" {FG_YELLOW}⚠️{RESET} (continuing anyway)")
        
        if stopped_count > 0:
            c_ok(f"  ✅ Stopped {stopped_count} tunnel(s)")
        else:
            print(f"  {FG_WHITE}No active tunnels to stop.{RESET}")
        
        print(f"\n  {FG_CYAN}Deleting Netrix Core binary...{RESET}", end='', flush=True)
        try:
            Path(NETRIX_BINARY).unlink()
            print(f" {FG_GREEN}✅{RESET}")
            c_ok(f"\n  ✅ Netrix Core deleted successfully!")
            c_warn("  ⚠️  All tunnels are now stopped. Install Netrix Core to use tunnels again.")
        except Exception as e:
            print(f" {FG_RED}❌{RESET}")
            c_err(f"  ❌ Failed to delete: {FG_RED}{str(e)}{RESET}")
        
        pause()
    except UserCancelled:
        exit_script()

# ========== System Optimizer ==========
def system_optimizer_menu():
    """Apply Netrix-oriented system tuning."""
    try:
        clear()
        _brand_box("System Optimizer", "", [
            f"{FG_WHITE}Includes:{RESET} sysctl tuning, limits tuning, memory and socket tuning",
            f"{FG_WHITE}Recommended for:{RESET} busy servers, rawsocket/KCP setups, and high traffic workloads",
            f"{FG_WHITE}Caution:{RESET} {FG_YELLOW}This modifies kernel and shell limit settings{RESET}",
        ], accent=FG_GREEN)
        print()
        if not ask_yesno(f"  {BOLD}Continue with system optimization?{RESET}", default=False):
            return

        print(f"\n  {FG_CYAN}Starting optimization workflow...{RESET}\n")
        print(f"  {FG_CYAN}1/2:{RESET} {BOLD}Applying sysctl profile{RESET}")
        sysctl_optimizations()

        print(f"\n  {FG_CYAN}2/2:{RESET} {BOLD}Applying limits profile{RESET}")
        limits_optimizations()

        print(f"\n  {FG_GREEN}✅ System optimization completed successfully.{RESET}")
        print(f"  {FG_YELLOW}Note:{RESET} A reboot may still be required for every change to take full effect.")
        print()
        ask_reboot()
    except UserCancelled:
        exit_script()

def sysctl_optimizations():
    """Apply production-oriented sysctl tuning for Netrix tunnels."""
    try:
        available_cc = _read_proc_text("/proc/sys/net/ipv4/tcp_available_congestion_control").split()
        tcp_cc = "bbr" if "bbr" in available_cc else "cubic"
        settings = [
            ("# Netrix performance profile - managed by net.py", ""),
            ("# Core RX/TX queues for L3 raw/UDP/ICMP, rawsocket and high traffic TCP", ""),
            ("net.core.netdev_max_backlog", "250000"),
            ("net.core.netdev_budget", "1200"),
            ("net.core.netdev_budget_usecs", "8000"),
            ("net.core.somaxconn", "65535"),
            ("net.core.rmem_default", "16777216"),
            ("net.core.rmem_max", "134217728"),
            ("net.core.wmem_default", "16777216"),
            ("net.core.wmem_max", "134217728"),
            ("net.core.optmem_max", "4194304"),
            ("net.core.default_qdisc", "fq"),
            ("net.core.rps_sock_flow_entries", "262144"),
            ("", ""),
            ("# TCP: high BDP paths, speedtest-like parallel flows and stable MSS/PMTU behavior", ""),
            ("net.ipv4.tcp_congestion_control", tcp_cc),
            ("net.ipv4.tcp_moderate_rcvbuf", "1"),
            ("net.ipv4.tcp_mtu_probing", "1"),
            ("net.ipv4.tcp_sack", "1"),
            ("net.ipv4.tcp_dsack", "1"),
            ("net.ipv4.tcp_ecn", "0"),
            ("net.ipv4.tcp_ecn_fallback", "1"),
            ("net.ipv4.tcp_rmem", "4096 87380 134217728"),
            ("net.ipv4.tcp_wmem", "4096 65536 134217728"),
            ("net.ipv4.tcp_slow_start_after_idle", "0"),
            ("net.ipv4.tcp_window_scaling", "1"),
            ("net.ipv4.tcp_no_metrics_save", "1"),
            ("net.ipv4.tcp_syncookies", "1"),
            ("net.ipv4.tcp_tw_reuse", "1"),
            ("net.ipv4.tcp_max_syn_backlog", "65535"),
            ("net.ipv4.tcp_max_tw_buckets", "2000000"),
            ("net.ipv4.tcp_fin_timeout", "15"),
            ("net.ipv4.tcp_keepalive_time", "900"),
            ("net.ipv4.tcp_keepalive_intvl", "30"),
            ("net.ipv4.tcp_keepalive_probes", "5"),
            ("", ""),
            ("# UDP/raw capture: reduce burst drops for L3 UDP/ICMP and iperf-like loads", ""),
            ("net.ipv4.udp_mem", "262144 1048576 33554432"),
            ("net.ipv4.udp_rmem_min", "262144"),
            ("net.ipv4.udp_wmem_min", "262144"),
            ("net.ipv4.udp_l3mdev_accept", "1"),
            ("", ""),
            ("# Routing/TUN: exit-node forwarding and asymmetric paths", ""),
            ("net.ipv4.ip_forward", "1"),
            ("net.ipv4.conf.all.forwarding", "1"),
            ("net.ipv4.conf.default.forwarding", "1"),
            ("net.ipv4.ip_local_port_range", "10240 65535"),
            ("net.ipv4.ip_nonlocal_bind", "1"),
            ("net.ipv4.conf.all.rp_filter", "0"),
            ("net.ipv4.conf.default.rp_filter", "0"),
            ("net.ipv4.conf.all.accept_redirects", "0"),
            ("net.ipv4.conf.default.accept_redirects", "0"),
            ("net.ipv4.conf.all.send_redirects", "0"),
            ("net.ipv4.conf.default.send_redirects", "0"),
            ("net.ipv4.conf.all.accept_source_route", "0"),
            ("net.ipv4.conf.default.accept_source_route", "0"),
            ("net.ipv4.conf.all.log_martians", "0"),
            ("net.ipv4.conf.default.log_martians", "0"),
            ("", ""),
            ("# Neighbor and file limits for many flows", ""),
            ("net.ipv4.neigh.default.gc_thresh1", "1024"),
            ("net.ipv4.neigh.default.gc_thresh2", "4096"),
            ("net.ipv4.neigh.default.gc_thresh3", "32768"),
            ("net.unix.max_dgram_qlen", "512"),
            ("fs.file-max", "67108864"),
            ("fs.nr_open", "4194304"),
            ("", ""),
            ("# VM: keep swapping low without starving packet buffers", ""),
            ("vm.swappiness", "10"),
            ("vm.min_free_kbytes", "65536"),
            ("vm.vfs_cache_pressure", "100"),
            ("vm.max_map_count", "262144"),
        ]

        sysctl_file = NETRIX_SYSCTL_FILE
        sysctl_file.parent.mkdir(parents=True, exist_ok=True)
        if sysctl_file.exists():
            backup_file = sysctl_file.with_suffix(sysctl_file.suffix + ".bak")
            shutil.copy(sysctl_file, backup_file)
            c_ok(f"  ✅ Backup created: {backup_file}")

        lines = []
        apply_items = []
        for key, value in settings:
            if key.startswith("#"):
                lines.append(key)
            elif key == "":
                lines.append("")
            else:
                lines.append(f"{key} = {value}")
                apply_items.append((key, value))
        sysctl_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        c_ok(f"  ✅ Sysctl profile written: {sysctl_file}")

        print(f"  {FG_CYAN}Applying sysctl settings one by one...{RESET}")
        applied = 0
        failed = []
        for key, value in apply_items:
            result = subprocess.run(
                ["sysctl", "-w", f"{key}={value}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                applied += 1
            else:
                failed.append((key, (result.stderr or result.stdout or "").strip()))
        c_ok(f"  ✅ Applied {applied}/{len(apply_items)} sysctl settings")
        if failed:
            c_warn(f"  ⚠️  {len(failed)} setting(s) were not supported by this kernel and were skipped at runtime")
            for key, err in failed[:5]:
                c_warn(f"     - {key}: {err[:120] if err else 'unsupported'}")
    except Exception as e:
        c_err(f"  ❌ Failed to optimize sysctl: {FG_RED}{str(e)}{RESET}")
        raise

def limits_optimizations():
    """Apply file/process limits without rewriting the user's shell profile."""
    try:
        print(f"  {FG_CYAN}Writing limits.d profile...{RESET}")
        limits_file = NETRIX_LIMITS_FILE
        limits_file.parent.mkdir(parents=True, exist_ok=True)
        if limits_file.exists():
            backup_file = limits_file.with_suffix(limits_file.suffix + ".bak")
            shutil.copy(limits_file, backup_file)
            c_ok(f"  ✅ Backup created: {backup_file}")

        limits_text = """# Netrix limits profile - managed by net.py
# Allows many simultaneous sockets/flows without touching unrelated /etc/profile lines.
* soft nofile 1048576
* hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
root soft nproc 1048576
root hard nproc 1048576
* soft memlock unlimited
* hard memlock unlimited
root soft memlock unlimited
root hard memlock unlimited
"""
        limits_file.write_text(limits_text, encoding="utf-8")
        c_ok(f"  ✅ Limits profile written: {limits_file}")

        print(f"  {FG_CYAN}Writing shell ulimit helper...{RESET}")
        profile_limits_file = NETRIX_PROFILE_LIMITS_FILE
        profile_limits_file.parent.mkdir(parents=True, exist_ok=True)
        profile_text = """# Netrix shell limits - managed by net.py
# Best-effort only; systemd services should use their unit LimitNOFILE too.
ulimit -n 1048576 2>/dev/null || true
ulimit -u 1048576 2>/dev/null || true
ulimit -l unlimited 2>/dev/null || true
"""
        profile_limits_file.write_text(profile_text, encoding="utf-8")
        try:
            profile_limits_file.chmod(0o644)
        except Exception:
            pass
        c_ok(f"  ✅ Shell helper written: {profile_limits_file}")
        c_warn("  ⚠️  Limits apply after a new login/session or reboot")
    except Exception as e:
        c_err(f"  ❌ Failed to optimize limits: {FG_RED}{str(e)}{RESET}")
        raise

def ask_reboot():
    """سوال برای reboot"""
    try:
        print()
        if ask_yesno(f"  {BOLD}{FG_YELLOW}Do you want to reboot the system now?{RESET}", default=False):
            print(f"\n  {FG_CYAN}Rebooting system in 5 seconds...{RESET}")
            print(f"  {FG_YELLOW}Press Ctrl+C to cancel{RESET}")
            
            try:
                for i in range(5, 0, -1):
                    print(f"  {FG_CYAN}{i}...{RESET}", end='\r', flush=True)
                    time.sleep(1)
                print()
                
                c_ok("  ✅ Rebooting now...")
                subprocess.run(["reboot"], check=False)
            except KeyboardInterrupt:
                exit_script()
        else:
            print(f"\n  {FG_WHITE}Reboot skipped. Remember to reboot later for full effect.{RESET}")
            
    except KeyboardInterrupt:
        exit_script()
    except Exception as e:
        c_err(f"  ❌ Failed to reboot: {FG_RED}{str(e)}{RESET}")

def main_menu():
    """Main control center."""
    while True:
        clear()
        core_installed = os.path.exists(NETRIX_BINARY)
        _brand_box("", "", _brand_meta(core_installed), accent=FG_CYAN)
        print()
        _menu_line("1", "Create Tunnel", "Launch the guided tunnel wizard", accent=FG_GREEN)
        _menu_line("2", "Status", "Inspect running services, configs, and health", accent=FG_BLUE)
        _menu_line("3", "Stop", "Stop an active tunnel and cleanup its rules", accent=FG_YELLOW)
        _menu_line("4", "Restart", "Restart a tunnel after changes or failures", accent=FG_MAGENTA)
        _menu_line("5", "Delete", "Remove a tunnel config and systemd service", accent=FG_RED)
        _menu_line("6", "Install / Update Core", "Manage the Netrix binary from GitHub releases", accent=FG_CYAN)
        _menu_line("7", "System Optimizer", "Tune the host for high-throughput transport workloads", accent=FG_GREEN)
        print()
        _menu_line("0", "Exit", "Leave the script", accent=FG_WHITE)
        print()

        try:
            ch = input(_input_prompt("Choose an action")).strip()
        except KeyboardInterrupt:
            exit_script()

        if ch == "1":
            start_configure_menu()
        elif ch == "2":
            status_menu()
        elif ch == "3":
            stop_tunnel_menu()
        elif ch == "4":
            restart_tunnel_menu()
        elif ch == "5":
            delete_tunnel_menu()
        elif ch == "6":
            core_management_menu()
        elif ch == "7":
            system_optimizer_menu()
        elif ch == "0":
            return
        else:
            c_err("Invalid choice.")
            pause()

def main():
    require_root()
    
    main_menu()

if __name__ == "__main__":
    main()


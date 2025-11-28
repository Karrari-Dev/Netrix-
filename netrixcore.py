#!/usr/bin/env python3
import os, sys, time, subprocess, shutil, socket, signal, urllib.request, platform, json, stat
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML library not found. Install with: pip install pyyaml")
    sys.exit(1)


ROOT_DIR = Path("/root")
NETRIX_BINARY = "/usr/local/bin/netrix"
NETRIX_RELEASE_URLS = {
    "amd64": "https://github.com/Karrari-Dev/Netrix-/releases/download/v1.0.0/netrix-amd64.tar.gz",
    "arm64": "https://github.com/Karrari-Dev/Netrix-/releases/download/v1.0.0/netrix-arm64.tar.gz"
}

FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ========== Utils ==========

class UserCancelled(Exception):
    """Exception raised when user cancels an operation (Ctrl+C)"""
    pass

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

def pause(msg="\nPress Enter to continue..."):
    try: input(msg)
    except KeyboardInterrupt: pass

def which(cmd):
    p = shutil.which(cmd)
    return p if p else None

def is_port_in_use(port: int, protocol: str = "tcp", host: str = "0.0.0.0") -> bool:
    """بررسی استفاده بودن پورت"""
    sock_type = socket.SOCK_STREAM if protocol.lower() == "tcp" else socket.SOCK_DGRAM
    with socket.socket(socket.AF_INET, sock_type) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError:
            return True
    return False

def ask_int(prompt, min_=1, max_=65535, default=None):
    while True:
        try:
            raw = input(f"{prompt}{' ['+str(default)+']' if default is not None else ''}: ").strip()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
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
    while True:
        try:
            raw = input(f"{prompt}{' ['+default+']' if default else ''}: ").strip()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
        except (UnicodeDecodeError, UnicodeEncodeError):
            print(f"  {FG_RED}⚠️  Invalid input encoding. Please use English/ASCII characters.{RESET}")
            continue
        if raw == "" and default is not None:
            return default
        if raw:
            return raw
        print(f"  {FG_RED}⚠️  This field cannot be empty.{RESET}")

def ask_yesno(prompt, default=True):
    default_str = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(f"{prompt} [{default_str}]: ").strip().lower()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
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

def configure_buffer_pools() -> dict:
    """تنظیم Buffer Pool sizes برای performance tuning"""
    config = {}
    
    print(f"\n  {BOLD}{FG_YELLOW}Buffer Pool Configuration:{RESET}")
    print(f"  {FG_WHITE}Note: Press Enter or enter 0 to use default value (will be written as 0 in file){RESET}")
    print(f"  {FG_WHITE}Default values: buffer_pool=128KB, large_buffer=128KB, udp_frame=64KB+256, udp_slice=1500{RESET}")
    print(f"  {FG_WHITE}You can edit these values later in the YAML file{RESET}\n")
    
    buffer_pool_size = ask_int(
        f"  {BOLD}Buffer Pool Size:{RESET} {FG_WHITE}(bytes, default: 131072 = 128KB, 0 = use default){RESET}",
        min_=0,
        default=0
    )
    config["buffer_pool_size"] = buffer_pool_size
    
    large_buffer_pool_size = ask_int(
        f"  {BOLD}Large Buffer Pool Size:{RESET} {FG_WHITE}(bytes, default: 131072 = 128KB, 0 = use default){RESET}",
        min_=0,
        default=0
    )
    config["large_buffer_pool_size"] = large_buffer_pool_size
    
    udp_frame_pool_size = ask_int(
        f"  {BOLD}UDP Frame Pool Size:{RESET} {FG_WHITE}(bytes, default: 65856 = 64KB+256, 0 = use default){RESET}",
        min_=0,
        default=0
    )
    config["udp_frame_pool_size"] = udp_frame_pool_size
    
    udp_data_slice_size = ask_int(
        f"  {BOLD}UDP Data Slice Size:{RESET} {FG_WHITE}(bytes, default: 1500 = MTU, 0 = use default){RESET}",
        min_=0,
        default=0
    )
    config["udp_data_slice_size"] = udp_data_slice_size
    
    c_ok(f"  ✅ Buffer Pool configuration saved")
    if all(v == 0 for v in config.values()):
        print(f"  {FG_WHITE}All values set to 0 (default) - core will use default values{RESET}")
    
    return config

# ========== Config File Management ==========
def get_config_path(tport: int) -> Path:
    """مسیر فایل کانفیگ YAML در /root"""
    return ROOT_DIR / f"server{tport}.yaml"

def get_default_smux_config(profile: str = "balanced") -> dict:
    """تنظیمات پیش‌فرض SMUX بر اساس profile"""
    profiles = {
        "balanced": {
            "keepalive": 8,
            "max_recv": 8388608,
            "max_stream": 8388608,
            "frame_size": 32768
        },
        "aggressive": {
            "keepalive": 5,
            "max_recv": 16777216,
            "max_stream": 16777216,
            "frame_size": 32768
        },
        "latency": {
            "keepalive": 3,
            "max_recv": 4194304,
            "max_stream": 4194304,
            "frame_size": 32768
        },
        "cpu-efficient": {
            "keepalive": 10,
            "max_recv": 8388608,
            "max_stream": 8388608,
            "frame_size": 32768
        }
    }
    return profiles.get(profile.lower(), profiles["balanced"])

def get_default_kcp_config(profile: str = "balanced") -> dict:
    """تنظیمات پیش‌فرض KCP بر اساس profile"""
    profiles = {
        "balanced": {
            "nodelay": 1,
            "interval": 10,
            "resend": 2,
            "nc": 1,
            "sndwnd": 768,
            "rcvwnd": 768,
            "mtu": 1400
        },
        "aggressive": {
            "nodelay": 1,
            "interval": 8,
            "resend": 2,
            "nc": 1,
            "sndwnd": 1024,
            "rcvwnd": 1024,
            "mtu": 1400
        },
        "latency": {
            "nodelay": 1,
            "interval": 8,
            "resend": 2,
            "nc": 1,
            "sndwnd": 768,
            "rcvwnd": 768,
            "mtu": 1350
        },
        "cpu-efficient": {
            "nodelay": 0,
            "interval": 20,
            "resend": 2,
            "nc": 1,
            "sndwnd": 512,
            "rcvwnd": 512,
            "mtu": 1400
        }
    }
    return profiles.get(profile.lower(), profiles["balanced"])

def get_default_advanced_config(transport: str) -> dict:
    """تنظیمات پیش‌فرض Advanced بر اساس transport - تمام فلگ‌های قابل تنظیم"""
    base_config = {
        "tcp_nodelay": True,
        "tcp_keepalive": 15,
        "tcp_read_buffer": 4194304,  # 4MB
        "tcp_write_buffer": 4194304,  # 4MB
        "cleanup_interval": 3,
        "session_timeout": 30,
        "connection_timeout": 60,
        "stream_timeout": 120,
        "max_connections": 2000,
        "max_udp_flows": 1000,
        "udp_flow_timeout": 300,
        "verbose": False
    }
    

    if transport in ("kcpmux", "kcp"):
        base_config.update({
            "udp_read_buffer": 4194304,  # 4MB
            "udp_write_buffer": 4194304   # 4MB
        })
    elif transport in ("wsmux", "wssmux"):
        base_config.update({
            "websocket_read_buffer": 262144,  # 256KB
            "websocket_write_buffer": 262144,  # 256KB
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
    
    # 5. صدور certificate (issue)
    print(f"\n  {FG_CYAN}🎫 Step 5/5:{RESET} {BOLD}Issuing certificate for {FG_GREEN}{domain}{RESET}...")
    print(f"     {FG_YELLOW}⚠️  Note:{RESET} acme.sh will use port {FG_CYAN}80{RESET} for verification {FG_WHITE}(not {port}){RESET}")
    print(f"     {FG_YELLOW}⚠️  Make sure port 80 is not in use, or we can temporarily stop nginx{RESET}")
    
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
            c_warn(f"  ⚠️  Port {FG_YELLOW}80{RESET} is in use {FG_WHITE}(likely nginx){RESET}")
            if ask_yesno(f"  {BOLD}Stop nginx temporarily for certificate verification?{RESET}", default=True):
                print(f"  {FG_CYAN}Stopping nginx...{RESET}")
                subprocess.run(["systemctl", "stop", "nginx"], check=False)
                nginx_stopped = True
                c_ok(f"  ✅ nginx stopped temporarily")
    except Exception:
        pass
    
    if not port_80_in_use or nginx_stopped:
        try:
            input(f"  {BOLD}{FG_CYAN}Press Enter when ready to continue...{RESET}")
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            if nginx_stopped:
                print(f"  {FG_CYAN}Restarting nginx...{RESET}")
                subprocess.run(["systemctl", "start", "nginx"], check=False)
            return None, None
    else:
        c_err("  ❌ Cannot proceed without stopping services on port 80")
        return None, None
    
    result = subprocess.run(
        [str(acme_sh), "--issue", "-d", domain, "--standalone"],
        capture_output=True,
        text=True
    )
    
    if nginx_stopped:
        print(f"\n  {FG_CYAN}Restarting nginx...{RESET}")
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

def create_server_config_file(tport: int, cfg: dict) -> Path:
    """ساخت فایل کانفیگ YAML برای سرور"""
    config_path = get_config_path(tport)
    
    transport = cfg.get('transport', 'tcpmux')
    profile = cfg.get('profile', 'balanced')
    
    yaml_data = {
        "mode": "server",
        "listen": cfg.get('listen', f"0.0.0.0:{tport}"),
        "transport": transport,
        "psk": cfg.get('psk', '')
    }
    
    yaml_data["profile"] = profile
    
    smux_default = get_default_smux_config(profile)
    yaml_data["smux"] = {
        "keepalive": smux_default["keepalive"],
        "max_recv": smux_default["max_recv"],
        "max_stream": smux_default["max_stream"],
        "frame_size": smux_default["frame_size"]
    }
    
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
    
    advanced_default = get_default_advanced_config(transport)
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
    
    yaml_data["verbose"] = cfg.get("verbose", False)
    
    if cfg.get("cert_file") and cfg.get("key_file"):
        yaml_data["cert_file"] = cfg["cert_file"]
        yaml_data["key_file"] = cfg["key_file"]
    
    if "max_sessions" in cfg:
        yaml_data["max_sessions"] = cfg['max_sessions']
    
    if "heartbeat" in cfg:
        yaml_data["heartbeat"] = cfg['heartbeat']
    
    if cfg.get('maps'):
        yaml_data["maps"] = []
        for m in cfg['maps']:
            yaml_data["maps"].append({
                "type": m['type'],
                "bind": m['bind'],
                "target": m['target']
            })
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass
    
    return config_path

def create_client_config_file(cfg: dict) -> Path:
    """ساخت فایل کانفیگ YAML برای کلاینت"""
    paths = cfg.get('paths', [])
    if paths:
        first_addr = paths[0].get('addr', 'unknown').replace(':', '_').replace('.', '_')
        config_path = ROOT_DIR / f"client_{first_addr}.yaml"
    else:
        config_path = ROOT_DIR / f"client_{int(time.time())}.yaml"
    
    profile = cfg.get('profile', 'balanced')
    
    yaml_data = {
        "mode": "client",
        "psk": cfg.get('psk', '')
    }
    
    yaml_data["profile"] = profile
    
    if paths:
        yaml_data["paths"] = []
        for path in paths:
            path_transport = path.get('transport', 'tcpmux')
            path_data = {
                "transport": path_transport,
                "addr": path.get('addr', '')
            }
            if 'connection_pool' in path:
                path_data["connection_pool"] = path['connection_pool']
            else:
                path_data["connection_pool"] = 4
            if path.get('retry_interval'):
                path_data["retry_interval"] = path['retry_interval']
            if path.get('dial_timeout'):
                path_data["dial_timeout"] = path['dial_timeout']
            if path.get('aggressive_pool'):
                path_data["aggressive_pool"] = path['aggressive_pool']
            yaml_data["paths"].append(path_data)
        
        main_transport = paths[0].get('transport', 'tcpmux')
    else:
        main_transport = 'tcpmux'
    
    smux_default = get_default_smux_config(profile)
    yaml_data["smux"] = {
        "keepalive": smux_default["keepalive"],
        "max_recv": smux_default["max_recv"],
        "max_stream": smux_default["max_stream"],
        "frame_size": smux_default["frame_size"]
    }
    
    if any(p.get('transport') == 'kcpmux' for p in paths):
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
    
    advanced_default = get_default_advanced_config(main_transport)
    yaml_data["advanced"] = {}
    for key, value in advanced_default.items():
        if key != "verbose":
            yaml_data["advanced"][key] = value
    
    yaml_data["verbose"] = cfg.get("verbose", False)
    
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
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
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
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        pass
    return None

def list_tunnels() -> List[Dict[str,Any]]:
    """لیست تمام تانل‌ها از فایل‌های YAML"""
    items = []
    
    for config_file in ROOT_DIR.glob("server*.yaml"):
        try:
            cfg = parse_yaml_config(config_file)
            if not cfg or cfg.get('mode') != 'server':
                continue
            
            listen = cfg.get('listen', '')
            tport = listen.split(':')[-1] if ':' in listen else ''
            transport = cfg.get('transport', 'tcpmux')
            
            status = get_service_status(config_file)
            alive = (status == "active")
            pid = get_service_pid(config_file) if alive else None
            
            items.append({
                "config_path": config_file,
                "mode": "server",
                "tport": tport,
                "transport": transport,
                "summary": f"server port={tport} transport={transport}",
                "pid": pid,
                "alive": alive,
                "cfg": cfg
            })
        except Exception:
            continue
    
    for config_file in ROOT_DIR.glob("client*.yaml"):
        try:
            cfg = parse_yaml_config(config_file)
            if not cfg or cfg.get('mode') != 'client':
                continue
            
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
                "summary": summary,
                "pid": pid,
                "alive": alive,
                "cfg": cfg
            })
        except Exception:
            continue
    
    return items

def run_tunnel(config_path: Path):
    """اجرای تانل از طریق systemd service"""
    if not create_systemd_service_for_tunnel(config_path):
        return False
    
    service_name = f"netrix-{config_path.stem}"
    try:
        subprocess.run(["systemctl", "enable", service_name], check=False)
        try:
            result = subprocess.run(
                ["systemctl", "start", service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True
            else:
                c_err(f"Failed to start service: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            c_err("Failed to start service: timeout (service may be hanging)")
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
            timeout=10
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        c_warn(f"  ⚠️  Service stop timeout (forcing kill)...")
        try:
            subprocess.run(["systemctl", "kill", "--signal=SIGKILL", service_name], timeout=5, check=False)
            return True
        except:
            return False
    except Exception:
        return False

# ========== System Service ==========
def create_systemd_service_for_tunnel(config_path: Path) -> bool:
    """ساخت systemd service برای یک تانل خاص"""
    netrix_bin = ensure_netrix_available()
    if not netrix_bin:
        return False
    
    service_name = f"netrix-{config_path.stem}"
    service_path = Path(f"/etc/systemd/system/{service_name}.service")
    
    service_content = f"""[Unit]
Description=Netrix Tunnel - {config_path.name}
After=network.target

[Service]
Type=simple
ExecStart={netrix_bin} -config {config_path}
Restart=always
RestartSec=3
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
    """منوی ساخت/پیکربندی تانل"""
    while True:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                                {BOLD}Create Tunnel{RESET}                  ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        print(f"  {BOLD}{FG_GREEN}1){RESET} Iran Server")
        print(f"  {BOLD}{FG_BLUE}2){RESET} Kharej Client")
        print(f"  {FG_WHITE}0){RESET} Back")
        print()
        
        try:
            choice = input("> ").strip()
        except KeyboardInterrupt:
            print("\n")
            return
        
        if choice == "0":
            return
        elif choice == "1":
            try:
                create_server_tunnel()
                return
            except UserCancelled:
                continue
        elif choice == "2":
            try:
                create_client_tunnel()
                return
            except UserCancelled:
                continue
        else:
            c_err("Invalid choice.")
            pause()

def create_server_tunnel():
    """ساخت تانل سرور (Iran)"""
    try:
        # بررسی نصب بودن هسته
        if not ensure_netrix_available():
            clear()
            print(f"{BOLD}{FG_RED}╔══════════════════════════════════════════════════════════╗{RESET}")
            print(f"                            {BOLD}Core Not Installed{RESET}                  ")
            print(f"{BOLD}{FG_RED}╚══════════════════════════════════════════════════════════╝{RESET}")
            print()
            c_err("Netrix core is not installed!")
            print(f"\n  {FG_YELLOW}Please install the core first from:{RESET}")
            print(f"  {FG_CYAN}Main Menu → Option 6 (Core Management) → Install/Update Core{RESET}\n")
            pause()
            return
        
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                          {BOLD}Create Iran Server Tunnel{RESET}             ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        print(f"  {BOLD}{FG_CYAN}Transport Types:{RESET}")
        print(f"  {FG_CYAN}1){RESET} {FG_GREEN}tcpmux{RESET} (TCP with smux)")
        print(f"  {FG_CYAN}2){RESET} {FG_GREEN}kcpmux{RESET} (KCP with smux)")
        print(f"  {FG_CYAN}3){RESET} {FG_GREEN}wsmux{RESET} (WebSocket with smux)")
        print(f"  {FG_CYAN}4){RESET} {FG_GREEN}wssmux{RESET} (WebSocket Secure with smux)")
        transport_choice = ask_int(f"\n  {BOLD}Select transport:{RESET}", min_=1, max_=4, default=1)
        transports = {1: "tcpmux", 2: "kcpmux", 3: "wsmux", 4: "wssmux"}
        transport = transports[transport_choice]
        
        print(f"\n  {BOLD}{FG_CYAN}Server Configuration:{RESET}")
        while True:
            tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            if is_port_in_use(tport):
                c_warn(f"  ⚠️  Port {FG_YELLOW}{tport}{RESET} is already in use!")
                if not ask_yesno(f"  {BOLD}Continue anyway?{RESET}", default=False):
                    continue
            break
        
        print(f"\n  {BOLD}{FG_CYAN}Security Settings:{RESET}")
        psk = ask_nonempty(f"  {BOLD}Pre-shared Key (PSK):{RESET}")
        
        print(f"\n  {BOLD}{FG_CYAN}Performance Profiles:{RESET}")
        print(f"  {FG_BLUE}1){RESET} {FG_GREEN}balanced{RESET} {FG_WHITE}(default - best overall){RESET}")
        print(f"  {FG_BLUE}2){RESET} {FG_GREEN}aggressive{RESET} {FG_WHITE}(high throughput, more CPU){RESET}")
        print(f"  {FG_BLUE}3){RESET} {FG_GREEN}latency{RESET} {FG_WHITE}(low latency priority){RESET}")
        print(f"  {FG_BLUE}4){RESET} {FG_GREEN}cpu-efficient{RESET} {FG_WHITE}(low CPU usage){RESET}")
        profile_choice = ask_int(f"\n  {BOLD}Select profile:{RESET}", min_=1, max_=4, default=1)
        profiles = {1: "balanced", 2: "aggressive", 3: "latency", 4: "cpu-efficient"}
        profile = profiles[profile_choice]
        
        cert_file = None
        key_file = None
        if transport == "wssmux":
            print(f"\n  {BOLD}🔐 TLS Certificate Configuration:{RESET}")
            print(f"  {FG_GREEN}1){RESET} Get new certificate (Let's Encrypt)")
            print(f"  {FG_BLUE}2){RESET} Use existing certificate (provide file paths)")
            print(f"  {FG_YELLOW}3){RESET} Use test certificate (self-signed, auto-generated)")
            cert_choice = ask_int("\nSelect certificate type", min_=1, max_=3, default=3)
            
            if cert_choice == 1:
                while True:
                    try:
                        domain = input(f"\n  {BOLD}{FG_GREEN}Enter your domain:{RESET} {FG_WHITE}(e.g., sub.pingless.site){RESET} ").strip()
                    except KeyboardInterrupt:
                        print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                        raise UserCancelled()
                    if not domain:
                        c_err("  Domain is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            raise UserCancelled()
                        continue
                    
                    try:
                        email = input(f"  {BOLD}{FG_GREEN}Enter your email:{RESET} {FG_WHITE}(for Let's Encrypt){RESET} ").strip()
                    except KeyboardInterrupt:
                        print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                        raise UserCancelled()
                    if not email:
                        c_err("  Email is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            raise UserCancelled()
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
                            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                            raise UserCancelled()
                        if retry_choice != "1":
                            raise UserCancelled()
                    else:
                        c_ok(f"  ✅ Real certificate obtained: {FG_GREEN}{cert_file}{RESET}")
                        break 
            
            elif cert_choice == 2:
                while True:
                    try:
                        cert_path = input(f"\n  {BOLD}{FG_GREEN}Enter certificate file path:{RESET} {FG_WHITE}(e.g., /root/cert.crt){RESET} ").strip()
                    except KeyboardInterrupt:
                        print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                        raise UserCancelled()
                    if not cert_path:
                        c_err("  Certificate file path is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            raise UserCancelled()
                        continue
                    
                    cert_path_obj = Path(cert_path)
                    if not cert_path_obj.exists():
                        c_err(f"  Certificate file not found: {FG_RED}{cert_path}{RESET}")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            raise UserCancelled()
                        continue
                    
                    try:
                        key_path = input(f"  {BOLD}{FG_GREEN}Enter private key file path:{RESET} {FG_WHITE}(e.g., /root/private.key){RESET} ").strip()
                    except KeyboardInterrupt:
                        print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                        raise UserCancelled()
                    if not key_path:
                        c_err("  Private key file path is required!")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            raise UserCancelled()
                        continue
                    
                    key_path_obj = Path(key_path)
                    if not key_path_obj.exists():
                        c_err(f"  Private key file not found: {FG_RED}{key_path}{RESET}")
                        if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                            raise UserCancelled()
                        continue
                    
                    try:
                        with open(cert_path_obj, 'r') as f:
                            cert_content = f.read()
                            if "BEGIN CERTIFICATE" not in cert_content:
                                c_err("  Invalid certificate file format!")
                                if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                    raise UserCancelled()
                                continue
                        
                        with open(key_path_obj, 'r') as f:
                            key_content = f.read()
                            if "BEGIN" not in key_content or "PRIVATE KEY" not in key_content:
                                c_err("  Invalid private key file format!")
                                if not ask_yesno(f"  {BOLD}Try again?{RESET}", default=True):
                                    raise UserCancelled()
                                continue
                        
                        cert_file = str(cert_path_obj)
                        key_file = str(key_path_obj)
                        c_ok(f"  ✅ Certificate files validated: {FG_GREEN}{cert_file}{RESET}")
                        break
                    except UserCancelled:
                        raise
                    except Exception as e:
                        c_err(f"Error reading certificate files: {e}")
                        if not ask_yesno("Try again?", default=True):
                            raise UserCancelled()
        
        print(f"\n  {BOLD}{FG_CYAN}Advanced Options:{RESET}")
        verbose = ask_yesno(f"  {BOLD}Enable verbose logging (for debugging)?{RESET}", default=False)
        
        print(f"\n  {BOLD}{FG_CYAN}Server Limits:{RESET}")
        max_sessions = ask_int(f"  {BOLD}Max Sessions:{RESET} {FG_WHITE}(0 = unlimited, recommended: 0 or 1000+){RESET}", min_=0, max_=100000, default=0)
        
        heartbeat = ask_int(f"  {BOLD}Heartbeat Interval:{RESET} {FG_WHITE}(seconds, 0 = use default 10s){RESET}", min_=0, max_=300, default=0)
        
        print(f"\n  {BOLD}{FG_CYAN}Performance Tuning:{RESET} {FG_YELLOW}(Advanced - Optional){RESET}")
        if ask_yesno(f"  {BOLD}Configure Buffer Pool sizes?{RESET} {FG_WHITE}(for performance tuning){RESET}", default=False):
            buffer_pool_config = configure_buffer_pools()
        else:
            buffer_pool_config = {
                "buffer_pool_size": 0,
                "large_buffer_pool_size": 0,
                "udp_frame_pool_size": 0,
                "udp_data_slice_size": 0
            }
        
        maps = []
        print(f"\n  {BOLD}{FG_CYAN}Port Mappings:{RESET} {FG_YELLOW}(optional - leave empty to skip){RESET}")
        print(f"  {FG_WHITE}Format:{RESET} Multiple ports with comma {FG_GREEN}(2066,9988,6665){RESET} or Range {FG_GREEN}(2066-2070){RESET}")
        print(f"  {FG_WHITE}Note:{RESET} Bind and Target ports will be the same {FG_CYAN}(0.0.0.0:2066 -> 127.0.0.1:2066){RESET}")
        
        # TCP Ports
        try:
            tcp_input = input(f"\n  {BOLD}{FG_GREEN}TCP Ports:{RESET} {FG_WHITE}(e.g., 2066,9988 or 2066-2070){RESET} ").strip()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
        if tcp_input:
            try:
                tcp_ports = parse_ports(tcp_input)
                for port in tcp_ports:
                    bind_addr = f"0.0.0.0:{port}"
                    target_addr = f"127.0.0.1:{port}"
                    maps.append({"type": "tcp", "bind": bind_addr, "target": target_addr})
                if tcp_ports:
                    c_ok(f"  ✅ Added {FG_GREEN}{len(tcp_ports)}{RESET} TCP mapping(s)")
            except ValueError as e:
                c_err(f"  ⚠️  Invalid TCP ports: {FG_RED}{e}{RESET}")
        
        # UDP Ports
        try:
            udp_input = input(f"  {BOLD}{FG_GREEN}UDP Ports:{RESET} {FG_WHITE}(e.g., 2066,9988 or 2066-2070){RESET} ").strip()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
        if udp_input:
            try:
                udp_ports = parse_ports(udp_input)
                for port in udp_ports:
                    bind_addr = f"0.0.0.0:{port}"
                    target_addr = f"127.0.0.1:{port}"
                    maps.append({"type": "udp", "bind": bind_addr, "target": target_addr})
                if udp_ports:
                    c_ok(f"  ✅ Added {FG_GREEN}{len(udp_ports)}{RESET} UDP mapping(s)")
            except ValueError as e:
                c_err(f"  ⚠️  Invalid UDP ports: {FG_RED}{e}{RESET}")
        
        # ساخت کانفیگ
        cfg = {
            "tport": tport,
            "listen": f"0.0.0.0:{tport}",
            "transport": transport,
            "psk": psk,
            "profile": profile,
            "maps": maps,
            "verbose": verbose,
            "max_sessions": max_sessions,  
            "heartbeat": heartbeat, 
            "buffer_pool_config": buffer_pool_config  
        }
        
        if cert_file and key_file:
            cfg["cert_file"] = cert_file
            cfg["key_file"] = key_file
        
        config_path = create_server_config_file(tport, cfg)
        
        c_ok(f"Configuration saved: {config_path}")
        
        print()
        if ask_yesno(f"  {BOLD}{FG_GREEN}Start tunnel now?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
            if run_tunnel(config_path):
                c_ok(f"  ✅ Tunnel started successfully!")
                c_ok(f"  ✅ Systemd service created and enabled {FG_WHITE}(auto-restart on crash/reboot){RESET}")
            else:
                c_err("  ❌ Failed to start tunnel!")
        
        pause()
    except UserCancelled:
        return

def create_client_tunnel():
    """ساخت تانل کلاینت (Kharej)"""
    try:
        # بررسی نصب بودن هسته
        if not ensure_netrix_available():
            clear()
            print(f"{BOLD}{FG_RED}╔══════════════════════════════════════════════════════════╗{RESET}")
            print(f"                            {BOLD}Core Not Installed{RESET}                  ")
            print(f"{BOLD}{FG_RED}╚══════════════════════════════════════════════════════════╝{RESET}")
            print()
            c_err("Netrix core is not installed!")
            print(f"\n  {FG_YELLOW}Please install the core first from:{RESET}")
            print(f"  {FG_CYAN}Main Menu → Option 6 (Core Management) → Install/Update Core{RESET}\n")
            pause()
            return
        
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                         {BOLD}Create Kharej Client Tunnel{RESET}             ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        print(f"  {BOLD}{FG_CYAN}Transport Types:{RESET}")
        print(f"  {FG_CYAN}1){RESET} {FG_GREEN}tcpmux{RESET} (TCP with smux)")
        print(f"  {FG_CYAN}2){RESET} {FG_GREEN}kcpmux{RESET} (KCP with smux)")
        print(f"  {FG_CYAN}3){RESET} {FG_GREEN}wsmux{RESET} (WebSocket with smux)")
        print(f"  {FG_CYAN}4){RESET} {FG_GREEN}wssmux{RESET} (WebSocket Secure with smux)")
        transport_choice = ask_int(f"\n  {BOLD}Select transport:{RESET}", min_=1, max_=4, default=1)
        transports = {1: "tcpmux", 2: "kcpmux", 3: "wsmux", 4: "wssmux"}
        transport = transports[transport_choice]
        
        print(f"\n  {BOLD}{FG_CYAN}Server Connection:{RESET}")
        server_ip = ask_nonempty(f"  {BOLD}Iran Server IP:{RESET}")
        
        tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
        server_addr = f"{server_ip}:{tport}"
        
        print(f"\n  {BOLD}{FG_CYAN}Security Settings:{RESET}")
        psk = ask_nonempty(f"  {BOLD}Pre-shared Key (PSK):{RESET}")
        
        print(f"\n  {BOLD}{FG_CYAN}Performance Profiles:{RESET}")
        print(f"  {FG_BLUE}1){RESET} {FG_GREEN}balanced{RESET} {FG_WHITE}(default - best overall){RESET}")
        print(f"  {FG_BLUE}2){RESET} {FG_GREEN}aggressive{RESET} {FG_WHITE}(high throughput, more CPU){RESET}")
        print(f"  {FG_BLUE}3){RESET} {FG_GREEN}latency{RESET} {FG_WHITE}(low latency priority){RESET}")
        print(f"  {FG_BLUE}4){RESET} {FG_GREEN}cpu-efficient{RESET} {FG_WHITE}(low CPU usage){RESET}")
        profile_choice = ask_int(f"\n  {BOLD}Select profile:{RESET}", min_=1, max_=4, default=1)
        profiles = {1: "balanced", 2: "aggressive", 3: "latency", 4: "cpu-efficient"}
        profile = profiles[profile_choice]
        

        paths = []
        
        print(f"\n  {BOLD}{FG_CYAN}Connection Settings:{RESET}")
        connection_pool = ask_int(f"  {BOLD}Connection Pool:{RESET} {FG_WHITE}(recommended: 4-8){RESET}", min_=1, max_=100, default=4)
        
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
        
        paths.append(path_dict)
        
        print(f"\n  {FG_GREEN}✅ Primary server configured:{RESET} {FG_CYAN}{transport}://{server_addr}{RESET} {FG_WHITE}({connection_pool} connections){RESET}")
        
        print(f"\n  {FG_YELLOW}💡 Tip:{RESET} You can add backup servers (additional Iran servers) for redundancy.")
        print(f"     {FG_WHITE}If the primary server fails, client will automatically switch to backup server.{RESET}")
        while True:
            if not ask_yesno(f"\n  {BOLD}{FG_CYAN}Add another Iran server (backup)?{RESET}", default=False):
                break
            
            print(f"\n  {BOLD}{FG_CYAN}Backup Server #{len(paths) + 1}:{RESET} {FG_WHITE}(Additional Iran Server){RESET}")
            
            new_server_ip = ask_nonempty(f"  {BOLD}Iran Server IP:{RESET} {FG_WHITE}(e.g., 1.2.3.4){RESET}")
            
            new_tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            new_server_addr = f"{new_server_ip}:{new_tport}"
            
            print(f"\n  {BOLD}Transport Types:{RESET}")
            print(f"  {FG_CYAN}1){RESET} {FG_GREEN}tcpmux{RESET} (TCP with smux)")
            print(f"  {FG_CYAN}2){RESET} {FG_GREEN}kcpmux{RESET} (KCP with smux)")
            print(f"  {FG_CYAN}3){RESET} {FG_GREEN}wsmux{RESET} (WebSocket with smux)")
            print(f"  {FG_CYAN}4){RESET} {FG_GREEN}wssmux{RESET} (WebSocket Secure with smux)")
            new_transport_choice = ask_int(f"\n  {BOLD}Select transport:{RESET}", min_=1, max_=4, default=1)
            new_transport = transports[new_transport_choice]
            
            new_connection_pool = ask_int(f"  {BOLD}Connection Pool:{RESET} {FG_WHITE}(recommended: 4-8){RESET}", min_=1, max_=100, default=4)
            
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
            
            paths.append(new_path_dict)
            
            print(f"  {FG_GREEN}✅ Backup server added:{RESET} {FG_CYAN}{new_transport}://{new_server_addr}{RESET} {FG_WHITE}({new_connection_pool} connections){RESET}")
        

        print(f"\n  {BOLD}{FG_CYAN}Advanced Options:{RESET}")
        verbose = ask_yesno(f"  {BOLD}Enable verbose logging (for debugging)?{RESET}", default=False)
        

        heartbeat = ask_int(f"  {BOLD}Heartbeat Interval:{RESET} {FG_WHITE}(seconds, 0 = use default 10s){RESET}", min_=0, max_=300, default=0)
        
        print(f"\n  {BOLD}{FG_CYAN}Performance Tuning:{RESET} {FG_YELLOW}(Advanced - Optional){RESET}")
        if ask_yesno(f"  {BOLD}Configure Buffer Pool sizes?{RESET} {FG_WHITE}(for performance tuning){RESET}", default=False):
            buffer_pool_config = configure_buffer_pools()
        else:
            buffer_pool_config = {
                "buffer_pool_size": 0,
                "large_buffer_pool_size": 0,
                "udp_frame_pool_size": 0,
                "udp_data_slice_size": 0
            }
        
        cfg = {
            "psk": psk,
            "profile": profile,
            "paths": paths,
            "verbose": verbose,
            "heartbeat": heartbeat,
            "buffer_pool_config": buffer_pool_config
        }
        
        config_path = create_client_config_file(cfg)
        
        c_ok(f"  ✅ Configuration saved: {FG_GREEN}{config_path}{RESET}")
        
        print()
        if ask_yesno(f"  {BOLD}{FG_GREEN}Start tunnel now?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
            if run_tunnel(config_path):
                c_ok(f"  ✅ Tunnel started successfully!")
                c_ok(f"  ✅ Systemd service created and enabled {FG_WHITE}(auto-restart on crash/reboot){RESET}")
            else:
                c_err("  ❌ Failed to start tunnel!")
        
        pause()
    except UserCancelled:
        return

def status_menu():
    """منوی استاتوس"""
    while True:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                                     {BOLD}Status{RESET}                      ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        items = list_tunnels()
        if not items:
            print(f"  {FG_YELLOW}No tunnels found.{RESET}")
            pause()
            return
        
        for i, it in enumerate(items, 1):
            alive = it.get("alive")
            emo = f"{FG_GREEN}✅ Active{RESET}" if alive else f"{FG_RED}❌ Stopped{RESET}"
            print(f"  {BOLD}{FG_CYAN}{i}){RESET} {emo} {it['summary']}")
            print(f"     {FG_WHITE}Config:{RESET} {it['config_path'].name}")
            if i < len(items):
                print(f"     {FG_CYAN}{'─' * 55}{RESET}")
        
        print(f"\n  {FG_WHITE}0){RESET} Back")
        print()
        try:
            choice = input(f"  {BOLD}{FG_CYAN}Select tunnel:{RESET} {FG_WHITE}(or 0 to go back){RESET} ").strip()
        except KeyboardInterrupt:
            print("\n")
            return
        
        if choice == "0":
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                it = items[idx]
                config_path = it.get("config_path")
                if not config_path:
                    c_err("  ❌ Invalid selection.")
                    pause()
                    continue
                
                view_tunnel_details(config_path, it)
            else:
                c_err("  ❌ Invalid selection.")
                pause()
        except ValueError:
            c_err("  ❌ Invalid input. Please enter a number.")
            pause()

def view_tunnel_details(config_path: Path, tunnel: Dict[str,Any]):
    """نمایش جزئیات و لاگ تانل"""
    while True:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                                {BOLD}Tunnel Details{RESET}              ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        alive = tunnel.get("alive")
        status = f"{FG_GREEN}✅ Active{RESET}" if alive else f"{FG_RED}❌ Stopped{RESET}"
        print(f"  {BOLD}Status:{RESET} {status}")
        print(f"  {BOLD}Config:{RESET} {config_path}")
        cfg = tunnel.get('cfg', {})
        print(f"  {BOLD}Mode:{RESET} {cfg.get('mode', 'unknown')}")
        
        if cfg.get('mode') == 'server':
            print(f"  {BOLD}Listen:{RESET} {FG_GREEN}{cfg.get('listen', 'unknown')}{RESET}")
            print(f"  {BOLD}Transport:{RESET} {FG_CYAN}{cfg.get('transport', 'unknown')}{RESET}")
        else:
            paths = cfg.get('paths', [])
            if paths:
                print(f"  {BOLD}Paths:{RESET} {FG_GREEN}{len(paths)}{RESET} server path(s)")
        
        print()
        print(f"  {BOLD}{FG_BLUE}1){RESET} View Service Logs")
        print(f"  {BOLD}{FG_MAGENTA}2){RESET} View Live Logs")
        print(f"  {BOLD}{FG_GREEN}3){RESET} Health Check")
        print(f"  {BOLD}{FG_CYAN}4){RESET} Reload Config (Hot Reload)")
        print(f"  {FG_WHITE}0){RESET} Back")
        print()
        
        try:
            choice = input(f"  {BOLD}{FG_CYAN}> {RESET}").strip()
        except KeyboardInterrupt:
            print("\n")
            break
        
        if choice == "0":
            break
        elif choice == "1":
            view_service_logs(config_path)
        elif choice == "2":
            view_live_logs(config_path)
        elif choice == "3":
            check_tunnel_health(config_path)
        elif choice == "4":
            reload_tunnel_config(config_path)
        else:
            c_err("  ❌ Invalid choice. Please select 0, 1, 2, 3, or 4.")
            pause()

def view_service_logs(config_path: Path):
    """نمایش لاگ systemd service"""
    service_name = f"netrix-{config_path.stem}"
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"                                  {BOLD}Service Logs{RESET}                ")
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
    print(f"                                  {BOLD}Live Logs{RESET}                 ")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  {BOLD}Service:{RESET} {service_name}")
    print(f"  {FG_YELLOW}Press Ctrl+C to stop...{RESET}")
    print()
    
    try:
        subprocess.run(["journalctl", "-u", service_name, "-f"], check=False)
    except KeyboardInterrupt:
        print(f"\n  {FG_YELLOW}Live log stopped.{RESET}")
    except Exception as e:
        c_err(f"  ❌ Error: {FG_RED}{e}{RESET}")
        pause()

def check_tunnel_health(config_path: Path):
    """بررسی وضعیت health check endpoint"""
    service_name = f"netrix-{config_path.stem}"
    pid = get_service_pid(config_path)
    
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"                                {BOLD}Health Check{RESET}                 ")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    if not pid:
        c_err("  ❌ Tunnel is not running")
        pause()
        return
    
    print(f"  {BOLD}Service:{RESET} {service_name}")
    print(f"  {BOLD}PID:{RESET} {pid}")
    print()
    
    health_urls = [
        ("http://localhost:8080/health", "Simple Health Check"),
        ("http://localhost:8080/health/detailed", "Detailed Health Check")
    ]
    
    for url, name in health_urls:
        print(f"  {BOLD}{FG_CYAN}{name}:{RESET}")
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Netrix-Script/1.0")
            with urllib.request.urlopen(req, timeout=3) as response:
                status_code = response.getcode()
                body = response.read().decode('utf-8')
                
                if status_code == 200:
                    if name == "Simple Health Check":
                        print(f"    {FG_GREEN}✅ Status: OK{RESET}")
                        print(f"    {FG_WHITE}Response: {body.strip()}{RESET}")
                    else:
                        try:
                            data = json.loads(body)
                            status = data.get("status", "unknown")
                            sessions = data.get("sessions", 0)
                            streams = data.get("streams", 0)
                            rtt_ms = data.get("rtt_ms", 0)
                            
                            status_color = FG_GREEN if status == "healthy" else FG_YELLOW
                            print(f"    {BOLD}Status:{RESET} {status_color}{status.upper()}{RESET}")
                            print(f"    {BOLD}Sessions:{RESET} {FG_CYAN}{sessions}{RESET}")
                            print(f"    {BOLD}Streams:{RESET} {FG_CYAN}{streams}{RESET}")
                            print(f"    {BOLD}RTT:{RESET} {FG_CYAN}{rtt_ms} ms{RESET}")
                            
                            if "tcp_in_mb" in data:
                                print(f"    {BOLD}TCP In:{RESET} {FG_CYAN}{data['tcp_in_mb']:.2f} MB{RESET}")
                                print(f"    {BOLD}TCP Out:{RESET} {FG_CYAN}{data['tcp_out_mb']:.2f} MB{RESET}")
                                print(f"    {BOLD}UDP In:{RESET} {FG_CYAN}{data['udp_in_mb']:.2f} MB{RESET}")
                                print(f"    {BOLD}UDP Out:{RESET} {FG_CYAN}{data['udp_out_mb']:.2f} MB{RESET}")
                            
                            if "warning" in data:
                                print(f"    {FG_YELLOW}⚠️  Warning: {data['warning']}{RESET}")
                        except Exception:
                            print(f"    {FG_WHITE}Response: {body[:200]}{RESET}")
                else:
                    print(f"    {FG_RED}❌ Status: {status_code}{RESET}")
                    print(f"    {FG_WHITE}Response: {body.strip()}{RESET}")
        except urllib.error.HTTPError as e:
            print(f"    {FG_RED}❌ HTTP Error: {e.code}{RESET}")
            if e.code == 503:
                print(f"    {FG_YELLOW}Service is unavailable (may be shutting down or no sessions){RESET}")
        except urllib.error.URLError as e:
            print(f"    {FG_RED}❌ Connection Error: {e.reason}{RESET}")
            print(f"    {FG_YELLOW}⚠️  Health check server may not be running on port 8080{RESET}")
        except Exception as e:
            print(f"    {FG_RED}❌ Error: {e}{RESET}")
        print()
    
    pause()

def reload_tunnel_config(config_path: Path):
    """Reload کردن config بدون restart (Hot Reload)"""
    service_name = f"netrix-{config_path.stem}"
    pid = get_service_pid(config_path)
    
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"                               {BOLD}Config Hot Reload{RESET}              ")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    if not pid:
        c_err("  ❌ Tunnel is not running")
        c_warn("  ⚠️  Cannot reload config for stopped tunnel")
        pause()
        return
    
    print(f"  {BOLD}Service:{RESET} {service_name}")
    print(f"  {BOLD}PID:{RESET} {pid}")
    print(f"  {BOLD}Config:{RESET} {config_path}")
    print()
    
    print(f"  {FG_YELLOW}⚠️  Note:{RESET} Hot reload will reload:")
    print(f"     • Verbose logging")
    print(f"     • Heartbeat interval")
    print(f"     • Advanced settings")
    print(f"     • SMUX/KCP settings (for new connections)")
    print(f"     • MaxSessions (for new connections)")
    print()
    print(f"  {FG_YELLOW}⚠️  Changes to mode, listen, transport, maps, paths, PSK,")
    print(f"     cert_file, or key_file require a full restart.")
    print()
    
    if not ask_yesno(f"  {BOLD}Reload config now?{RESET}", default=True):
        return
    
    print(f"\n  {FG_CYAN}Sending reload signal...{RESET}", end='', flush=True)
    try:
        result = subprocess.run(
            ["kill", "-HUP", str(pid)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f" {FG_GREEN}✅{RESET}")
            c_ok("  ✅ Config reload signal sent successfully")
            print(f"  {FG_WHITE}Check service logs to verify reload status{RESET}")
        else:
            print(f" {FG_RED}❌{RESET}")
            c_err(f"  ❌ Failed to send reload signal: {result.stderr}")
    except subprocess.TimeoutExpired:
        print(f" {FG_YELLOW}⚠️{RESET}")
        c_err(f"  ❌ Failed to send reload signal: timeout")
    except Exception as e:
        print(f" {FG_RED}❌{RESET}")
        c_err(f"  ❌ Error: {FG_RED}{e}{RESET}")
    
    pause()

def stop_tunnel_menu():
    """منوی توقف تانل"""
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"                                  {BOLD}Stop Tunnel{RESET}                 ")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    items = list_tunnels()
    if not items:
        print(f"  {FG_YELLOW}No tunnels found.{RESET}")
        pause()
        return
    
    active_items = [it for it in items if it.get("alive")]
    if not active_items:
        print(f"  {FG_YELLOW}No active tunnels to stop.{RESET}")
        pause()
        return
    
    for i, it in enumerate(active_items, 1):
        print(f"  {BOLD}{FG_YELLOW}{i}){RESET} {it['summary']}")
    
    print(f"\n  {FG_WHITE}0){RESET} Back")
    print()
    try:
        choice = input(f"  {BOLD}{FG_YELLOW}Select tunnel to stop:{RESET} ").strip()
    except KeyboardInterrupt:
        print("\n")
        return
    
    if choice == "0":
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(active_items):
            it = active_items[idx]
            config_path = it.get("config_path")
            print(f"\n  {FG_CYAN}Stopping tunnel...{RESET}", end='', flush=True)
            if stop_tunnel(config_path):
                print(f" {FG_GREEN}✅{RESET}")
                c_ok(f"  ✅ Tunnel stopped successfully.")
            else:
                print(f" {FG_RED}❌{RESET}")
                c_err("  ❌ Failed to stop tunnel.")
        else:
            c_err("  ❌ Invalid selection.")
    except ValueError:
        c_err("  ❌ Invalid input. Please enter a number.")
    except Exception as e:
        c_err(f"  ❌ Error: {FG_RED}{e}{RESET}")
    
    pause()

def restart_tunnel_menu():
    """منوی ریستارت تانل"""
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"                                 {BOLD}Restart Tunnel{RESET}                ")
    print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    items = list_tunnels()
    if not items:
        print(f"  {FG_YELLOW}No tunnels found.{RESET}")
        pause()
        return
    
    for i, it in enumerate(items, 1):
        print(f"  {BOLD}{FG_MAGENTA}{i}){RESET} {it['summary']}")
    
    print(f"\n  {FG_WHITE}0){RESET} Back")
    print()
    try:
        choice = input(f"  {BOLD}{FG_MAGENTA}Select tunnel to restart:{RESET} ").strip()
    except KeyboardInterrupt:
        print("\n")
        return
    
    if choice == "0":
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            it = items[idx]
            config_path = it.get("config_path")
            
            service_name = f"netrix-{config_path.stem}"
            print(f"\n  {FG_CYAN}Restarting tunnel...{RESET}", end='', flush=True)
            try:
                result = subprocess.run(
                    ["systemctl", "restart", service_name],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.returncode == 0:
                    print(f" {FG_GREEN}✅{RESET}")
                    c_ok(f"  ✅ Tunnel restarted successfully.")
                else:
                    print(f" {FG_RED}❌{RESET}")
                    c_err(f"  ❌ Failed to restart tunnel: {FG_RED}{result.stderr}{RESET}")
            except subprocess.TimeoutExpired:
                print(f" {FG_YELLOW}⚠️{RESET}")
                c_err(f"  ❌ Failed to restart tunnel: timeout (service may be hanging)")
            except Exception as e:
                print(f" {FG_RED}❌{RESET}")
                c_err(f"  ❌ Failed to restart tunnel: {FG_RED}{e}{RESET}")
        else:
            c_err("  ❌ Invalid selection.")
    except ValueError:
        c_err("  ❌ Invalid input. Please enter a number.")
    except Exception as e:
        c_err(f"  ❌ Error: {FG_RED}{e}{RESET}")
    
    pause()

def delete_tunnel_menu():
    """منوی حذف تانل"""
    clear()
    print(f"{BOLD}{FG_RED}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"                                 {BOLD}Delete Tunnel{RESET}                 ")
    print(f"{BOLD}{FG_RED}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    items = list_tunnels()
    if not items:
        print(f"  {FG_YELLOW}No tunnels found.{RESET}")
        pause()
        return
    
    for i, it in enumerate(items, 1):
        print(f"  {BOLD}{FG_RED}{i}){RESET} {it['summary']}")
        print(f"     {FG_WHITE}Config:{RESET} {it['config_path'].name}")
    
    print(f"\n  {FG_WHITE}0){RESET} Back")
    print()
    try:
        choice = input(f"  {BOLD}{FG_RED}Select tunnel to delete:{RESET} ").strip()
    except KeyboardInterrupt:
        print("\n")
        return
    
    if choice == "0":
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            it = items[idx]
            config_path = it.get("config_path")
            
            if not ask_yesno(f"  {BOLD}{FG_RED}Are you sure you want to delete {FG_YELLOW}{config_path.name}{RESET}?{RESET}", default=False):
                return
            
            print(f"\n  {FG_CYAN}Deleting tunnel...{RESET}")
            
            if it.get("alive"):
                print(f"  {FG_CYAN}Stopping service...{RESET}", end='', flush=True)
                if stop_tunnel(config_path):
                    print(f" {FG_GREEN}✅{RESET}")
                else:
                    print(f" {FG_YELLOW}⚠️{RESET} (continuing anyway)")
            
            print(f"  {FG_CYAN}Removing systemd service...{RESET}", end='', flush=True)
            if delete_service_for_tunnel(config_path):
                print(f" {FG_GREEN}✅{RESET}")
            else:
                print(f" {FG_YELLOW}⚠️{RESET} (continuing anyway)")
            
            print(f"  {FG_CYAN}Deleting config file...{RESET}", end='', flush=True)
            try:
                config_path.unlink()
                print(f" {FG_GREEN}✅{RESET}")
                c_ok(f"\n  ✅ Tunnel deleted: {FG_GREEN}{config_path.name}{RESET}")
            except Exception as e:
                print(f" {FG_RED}❌{RESET}")
                c_err(f"  ❌ Failed to delete config file: {FG_RED}{e}{RESET}")
        else:
            c_err("  ❌ Invalid selection.")
    except ValueError:
        c_err("  ❌ Invalid input. Please enter a number.")
    except Exception as e:
        c_err(f"  ❌ Error: {FG_RED}{e}{RESET}")
    
    pause()

# ========== Core Management ==========
def core_management_menu():
    """منوی مدیریت هسته Netrix"""
    while True:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                           {BOLD}Netrix Core Management{RESET}            ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        binary_exists = Path(NETRIX_BINARY).exists()
        if binary_exists:
            try:
                result = subprocess.run([NETRIX_BINARY, "-version"], capture_output=True, text=True, timeout=5)
                version_info = result.stdout.strip() if result.returncode == 0 else "Unknown"
            except:
                version_info = "Unknown"
            
            print(f"  {BOLD}Status:{RESET} {FG_GREEN}✅ Installed{RESET}")
            print(f"  {BOLD}Path:{RESET} {FG_CYAN}{NETRIX_BINARY}{RESET}")
            if version_info != "Unknown":
                print(f"  {BOLD}Version:{RESET} {FG_GREEN}{version_info}{RESET}")
        else:
            print(f"  {BOLD}Status:{RESET} {FG_RED}❌ Not Installed{RESET}")
        
        print()
        print(f"  {BOLD}{FG_GREEN}1){RESET} Install Netrix Core")
        if binary_exists:
            print(f"  {BOLD}{FG_BLUE}2){RESET} Update Netrix Core")
            print(f"  {BOLD}{FG_RED}3){RESET} Delete Netrix Core")
        print(f"  {FG_WHITE}0){RESET} Back")
        print()
        
        try:
            choice = input(f"  {BOLD}{FG_CYAN}> {RESET}").strip()
        except KeyboardInterrupt:
            print("\n")
            return
        
        if choice == "0":
            return
        elif choice == "1":
            install_netrix_core()
        elif choice == "2" and binary_exists:
            update_netrix_core()
        elif choice == "3" and binary_exists:
            delete_netrix_core()
        else:
            c_err("  ❌ Invalid choice.")
            pause()

def install_netrix_core():
    """نصب هسته Netrix"""
    try:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                              {BOLD}Install Netrix Core{RESET}              ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
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
        
        # Extract tar.gz
        print(f"\n  {FG_CYAN}Extracting archive...{RESET}")
        try:
            import tarfile
            
            # ساخت دایرکتوری موقت برای extract
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract
            with tarfile.open(temp_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            c_ok(f"  ✅ Archive extracted")
            
            # پیدا کردن فایل netrix در دایرکتوری extract شده
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
            
            # پاک کردن فایل‌های موقت
            temp_file.unlink()
            shutil.rmtree(temp_dir)
            
            c_ok(f"  ✅ Netrix Core installed successfully!")
            c_ok(f"  ✅ Binary location: {FG_GREEN}{NETRIX_BINARY}{RESET}")
            
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
        return

def update_netrix_core():
    """آپدیت هسته Netrix"""
    try:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                            {BOLD}Update Netrix Core{RESET}               ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
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
        
        install_netrix_core()
        
        if stopped_count > 0 and ask_yesno(f"\n  {BOLD}Restart previously active tunnels?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Restarting tunnels...{RESET}")
            restarted_count = 0
            for config_path in stopped_tunnels:
                service_name = f"netrix-{config_path.stem}"
                print(f"  {FG_CYAN}Restarting {config_path.name}...{RESET}", end='', flush=True)
                try:
                    result = subprocess.run(
                        ["systemctl", "restart", service_name],
                        check=False,
                        capture_output=True,
                        timeout=15
                    )
                    if result.returncode == 0:
                        print(f" {FG_GREEN}✅{RESET}")
                        restarted_count += 1
                    else:
                        print(f" {FG_YELLOW}⚠️{RESET}")
                except subprocess.TimeoutExpired:
                    print(f" {FG_YELLOW}⚠️{RESET} (timeout)")
                except:
                    print(f" {FG_YELLOW}⚠️{RESET}")
            
            if restarted_count > 0:
                c_ok(f"  ✅ Restarted {restarted_count} tunnel(s)")
            else:
                c_warn("  ⚠️  No tunnels were restarted (check logs)")
        
    except UserCancelled:
        return

def delete_netrix_core():
    """حذف هسته Netrix"""
    try:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                               {BOLD}Delete Netrix Core{RESET}              ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
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
        return

# ========== System Optimizer ==========
def system_optimizer_menu():
    """منوی بهینه‌سازی سیستم"""
    try:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"                                   {BOLD}System Optimizer{RESET}              ")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        print(f"  {BOLD}{FG_YELLOW}⚠️  WARNING:{RESET} This will optimize system settings for high traffic.")
        print(f"  {FG_WHITE}This includes:{RESET}")
        print(f"    • Network kernel parameters (sysctl)")
        print(f"    • System limits (ulimit)")
        print(f"    • Memory and cache settings")
        print()
        
        if not ask_yesno(f"  {BOLD}Do you want to continue?{RESET}", default=False):
            return
        
        print(f"\n  {FG_CYAN}Starting system optimization...{RESET}\n")
        
        print(f"  {FG_CYAN}1/2:{RESET} {BOLD}Applying sysctl optimizations...{RESET}")
        sysctl_optimizations()
        
        print(f"\n  {FG_CYAN}2/2:{RESET} {BOLD}Applying limits optimizations...{RESET}")
        limits_optimizations()
        
        print(f"\n  {FG_GREEN}✅ System optimization completed successfully!{RESET}")
        print(f"  {FG_YELLOW}⚠️  Note: Some changes require a system reboot to take full effect.{RESET}")
        
        print()
        ask_reboot()
        
    except UserCancelled:
        return

def sysctl_optimizations():
    """بهینه‌سازی تنظیمات sysctl"""
    try:
        sysctl_file = Path("/etc/sysctl.conf")
        
        print(f"  {FG_CYAN}Creating backup of sysctl.conf...{RESET}")
        backup_file = Path("/etc/sysctl.conf.bak")
        if sysctl_file.exists():
            shutil.copy(sysctl_file, backup_file)
            c_ok(f"  ✅ Backup created: {backup_file}")
        else:
            sysctl_file.touch()
            c_warn("  ⚠️  sysctl.conf not found, creating new file")
        
        print(f"  {FG_CYAN}Removing old network/kernel settings...{RESET}")
        
        if sysctl_file.exists():
            with open(sysctl_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            new_lines = []
            skip_patterns = [
                'fs.', 'net.', 'vm.', 'kernel.'
            ]
            
            for line in lines:
                line_stripped = line.strip()
                should_skip = False
                
                if not line_stripped or line_stripped.startswith('# Netrix'):
                    continue
                
                for pattern in skip_patterns:
                    if line_stripped.startswith(pattern) or line_stripped.startswith(f'#{pattern}'):
                        should_skip = True
                        break
                
                if not should_skip:
                    new_lines.append(line)
            
            with open(sysctl_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
                if new_lines and not new_lines[-1]:
                    f.write('\n')
        
        c_ok("  ✅ Old settings removed")
        
        print(f"  {FG_CYAN}Adding optimized settings...{RESET}")
        
        new_settings = """# Netrix System Optimizations - Comprehensive Network & Kernel Tuning
# Network Core Settings
net.core.netdev_budget = 600
net.core.netdev_budget_usecs = 4000
net.core.dev_weight = 6
net.core.netdev_max_backlog = 32768
net.core.somaxconn = 65536
net.core.rmem_default = 1048576
net.core.rmem_max = 33554432
net.core.wmem_default = 1048576
net.core.wmem_max = 33554432
net.core.optmem_max = 262144
net.core.default_qdisc = fq
net.core.rps_sock_flow_entries = 65536

# TCP Settings
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_moderate_rcvbuf = 1
net.ipv4.tcp_low_latency = 1
net.ipv4.tcp_frto = 2
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_dsack = 1
net.ipv4.tcp_fack = 1
net.ipv4.tcp_ecn = 1
net.ipv4.tcp_ecn_fallback = 1
net.ipv4.tcp_rmem = 16384 1048576 33554432
net.ipv4.tcp_wmem = 16384 1048576 33554432
net.ipv4.tcp_syn_retries = 6
net.ipv4.tcp_synack_retries = 5
net.ipv4.tcp_fin_timeout = 25
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_keepalive_probes = 7
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_retries2 = 8
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_adv_win_scale = -2
net.ipv4.tcp_notsent_lowat = 32768
net.ipv4.tcp_no_metrics_save = 1
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_max_orphans = 819200
net.ipv4.tcp_max_syn_backlog = 20480
net.ipv4.tcp_max_tw_buckets = 1440000
net.ipv4.tcp_mem = 65536 1048576 33554432
net.ipv4.tcp_early_retrans = 3
net.ipv4.tcp_timestamps = 1

# UDP Settings
net.ipv4.udp_mem = 65536 1048576 33554432
net.ipv4.udp_rmem_min = 131072
net.ipv4.udp_wmem_min = 131072
net.ipv4.udp_l3mdev_accept = 1

# IP Forwarding
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.conf.default.forwarding = 1
net.ipv4.ip_local_port_range = 10240 65535
net.ipv4.ip_nonlocal_bind = 1

# Security Settings
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.rp_filter = 2
net.ipv4.conf.default.rp_filter = 2
net.ipv4.conf.all.log_martians = 0
net.ipv4.conf.default.log_martians = 0
net.ipv4.conf.all.arp_announce = 2
net.ipv4.conf.default.arp_announce = 2
net.ipv4.conf.lo.arp_announce = 2

# IPv6 Settings
net.ipv6.conf.all.disable_ipv6 = 0
net.ipv6.conf.default.disable_ipv6 = 0
net.ipv6.conf.lo.disable_ipv6 = 0
net.ipv6.conf.all.forwarding = 1
net.ipv6.conf.default.forwarding = 1

# Neighbor Cache
net.ipv4.neigh.default.gc_thresh1 = 512
net.ipv4.neigh.default.gc_thresh2 = 2048
net.ipv4.neigh.default.gc_thresh3 = 16384
net.ipv4.neigh.default.gc_stale_time = 60

# Unix Domain Sockets
net.unix.max_dgram_qlen = 256

# File System Settings
fs.file-max = 67108864
fs.nr_open = 4194304
fs.inotify.max_user_watches = 1048576
fs.inotify.max_user_instances = 16384
fs.inotify.max_queued_events = 131072
fs.aio-max-nr = 2097152

# Virtual Memory Settings
vm.min_free_kbytes = 65536
vm.swappiness = 10
vm.vfs_cache_pressure = 250
vm.dirty_ratio = 20
vm.dirty_background_ratio = 4
vm.overcommit_memory = 1
vm.overcommit_ratio = 80
vm.max_map_count = 262144

# Kernel Settings
kernel.panic = 1
"""
        
        with open(sysctl_file, 'a', encoding='utf-8') as f:
            f.write(new_settings)
        
        c_ok("  ✅ New settings added")
        
        print(f"  {FG_CYAN}Applying sysctl settings...{RESET}")
        try:
            result = subprocess.run(
                ["sysctl", "-p"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                c_ok("  ✅ Sysctl settings applied successfully")
            else:
                c_warn(f"  ⚠️  Some warnings during sysctl apply: {result.stderr[:200] if result.stderr else 'Unknown error'}")
        except subprocess.TimeoutExpired:
            c_warn("  ⚠️  Sysctl apply timeout (some settings may not be applied)")
        except Exception as e:
            c_err(f"  ❌ Failed to apply sysctl: {FG_RED}{str(e)}{RESET}")
            
    except Exception as e:
        c_err(f"  ❌ Failed to optimize sysctl: {FG_RED}{str(e)}{RESET}")
        raise

def limits_optimizations():
    """بهینه‌سازی تنظیمات ulimit"""
    try:
        profile_file = Path("/etc/profile")
        
        print(f"  {FG_CYAN}Removing old ulimit settings...{RESET}")
        
        if profile_file.exists():
            with open(profile_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if not (stripped.startswith('ulimit') or stripped.startswith('#ulimit')):
                    new_lines.append(line)
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        else:
            profile_file.touch()
        
        c_ok("  ✅ Old ulimit settings removed")
        
        print(f"  {FG_CYAN}Adding optimized ulimit settings...{RESET}")
        
        new_limits = """# Netrix System Limits Optimizations
ulimit -c unlimited
ulimit -d unlimited
ulimit -f unlimited
ulimit -i unlimited
ulimit -l unlimited
ulimit -m unlimited
ulimit -n 1048576
ulimit -q unlimited
ulimit -s 32768
ulimit -s -H 65536
ulimit -t unlimited
ulimit -u unlimited
ulimit -v unlimited
ulimit -x unlimited
"""
        
        with open(profile_file, 'a', encoding='utf-8') as f:
            f.write(new_limits)
        
        c_ok("  ✅ New ulimit settings added")
        c_warn("  ⚠️  Note: New ulimit settings will apply after logout/login or reboot")
        
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
                print(f"\n  {FG_YELLOW}Reboot cancelled.{RESET}")
        else:
            print(f"\n  {FG_WHITE}Reboot skipped. Remember to reboot later for full effect.{RESET}")
            
    except KeyboardInterrupt:
        print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
    except Exception as e:
        c_err(f"  ❌ Failed to reboot: {FG_RED}{str(e)}{RESET}")

def main_menu():
    """منوی اصلی"""
    while True:
        clear()
        print(f"{BOLD}{FG_CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{FG_CYAN}    ███╗   ██╗███████╗████████╗██████╗ ██╗██╗  ██╗{RESET}")
        print(f"{BOLD}{FG_CYAN}    ████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██║╚██╗██╔╝{RESET}")
        print(f"{BOLD}{FG_CYAN}    ██╔██╗ ██║█████╗     ██║   ██████╔╝██║ ╚███╔╝ {RESET}")
        print(f"{BOLD}{FG_CYAN}    ██║╚██╗██║██╔══╝     ██║   ██╔══██╗██║ ██╔██╗ {RESET}")
        print(f"{BOLD}{FG_CYAN}    ██║ ╚████║███████╗   ██║   ██║  ██║██║██╔╝ ██╗{RESET}")
        print(f"{BOLD}{FG_CYAN}    ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝{RESET}")
        print(f"{BOLD}{FG_CYAN}{'=' * 60}{RESET}")
        print(f"{FG_WHITE}    Tunnel Management Script{RESET}")
        
        core_installed = os.path.exists(NETRIX_BINARY)
        if core_installed:
            print(f"    {FG_GREEN}Core Status: ✅ Installed{RESET}")
        else:
            print(f"    {FG_RED}Core Status: ❌ Not Installed{RESET}")
        
        print(f"    {FG_CYAN}Support: {FG_WHITE}@Karrari_Dev{RESET}")
        print()
        print(f"  {BOLD}{FG_GREEN}1){RESET} Create Tunnel")
        print(f"  {BOLD}{FG_BLUE}2){RESET} Status")
        print(f"  {BOLD}{FG_YELLOW}3){RESET} Stop")
        print(f"  {BOLD}{FG_MAGENTA}4){RESET} Restart")
        print(f"  {BOLD}{FG_RED}5){RESET} Delete")
        print(f"  {BOLD}{FG_CYAN}6){RESET} Netrix Core Management")
        print(f"  {BOLD}{FG_GREEN}7){RESET} System Optimizer")
        print(f"  {FG_WHITE}0){RESET} Exit")
        print()
        
        try:
            ch = input(f"  {BOLD}{FG_CYAN}> {RESET}").strip()
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return
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
            c_err("  ❌ Invalid choice.")
            pause()

# ========== Main ==========
def main():
    require_root()
    
    main_menu()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Netrix Core - اسکریپت مدیریت تانل Netrix
"""
import os, sys, time, subprocess, shutil, socket, signal, urllib.request, platform, json, stat, hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML library not found. Install with: pip install pyyaml")
    sys.exit(1)

# ========== Version ==========
VERSION = "2.0.4"

ROOT_DIR = Path("/root")
NETRIX_CONFIG_DIR = ROOT_DIR / "netrix"
NETRIX_BINARY = "/usr/local/bin/netrix"
NETRIX_RELEASE_URLS = {
    "amd64": f"https://github.com/Karrari-Dev/Netrix-/releases/download/v{VERSION}/netrix-amd64.tar.gz",
    "arm64": f"https://github.com/Karrari-Dev/Netrix-/releases/download/v{VERSION}/netrix-arm64.tar.gz"
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

def get_server_ip() -> Optional[str]:
    """دریافت IP سرور (IPv4) - ابتدا IP عمومی، سپس IP محلی"""
    try:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=3) as response:
                public_ip = response.read().decode().strip()
                if public_ip and '.' in public_ip:
                    return public_ip
        except Exception:
            pass
        
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip and local_ip != "127.0.0.1":
                return local_ip
        except Exception:
            pass
        
        try:
            result = subprocess.run(
                ["ip", "-4", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and '127.0.0.1' not in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[1].split('/')[0]
                            if ip and '.' in ip:
                                return ip
        except Exception:
            pass
        
        return None
    except Exception:
        return None

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

def configure_buffer_pools() -> dict:
    """تنظیم Buffer Pool sizes برای performance tuning"""
    config = {}
    
    print(f"\n  {BOLD}{FG_YELLOW}Buffer Pool Configuration:{RESET}")
    print(f"  {FG_WHITE}Note: Press Enter or enter 0 to use default value{RESET}")
    print(f"  {FG_WHITE}Default values: buffer_pool=64KB, large_buffer=64KB, udp_frame=32KB, udp_slice=1500{RESET}")
    print(f"  {FG_GREEN}✅ These values are now configurable and will be applied by the core{RESET}\n")
    
    buffer_pool_size = ask_int(
        f"  {BOLD}Buffer Pool Size:{RESET} {FG_WHITE}(bytes, default: 65536 = 64KB, 0 = use default){RESET}",
        min_=0,
        default=0
    )
    config["buffer_pool_size"] = buffer_pool_size
    
    large_buffer_pool_size = ask_int(
        f"  {BOLD}Large Buffer Pool Size:{RESET} {FG_WHITE}(bytes, default: 65791, 0 = use default){RESET}",
        min_=0,
        default=0
    )
    config["large_buffer_pool_size"] = large_buffer_pool_size
    
    udp_frame_pool_size = ask_int(
        f"  {BOLD}UDP Frame Pool Size:{RESET} {FG_WHITE}(bytes, default: 65791, 0 = use default){RESET}",
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
    """مسیر فایل کانفیگ YAML در /root/netrix"""
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return NETRIX_CONFIG_DIR / f"server_{tport}.yaml"

def get_default_smux_config(profile: str = "balanced") -> dict:
    """تنظیمات پیش‌فرض SMUX بر اساس profile - همگام با netrix.go"""
    profiles = {
        "balanced": {
            "keepalive": 20,   
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

def get_default_kcp_config(profile: str = "balanced") -> dict:
    """تنظیمات پیش‌فرض KCP بر اساس profile - همگام با netrix.go"""
    profiles = {
        "balanced": {
            "nodelay": 0,      
            "interval": 20,  
            "resend": 2,       
            "nc": 0,         
            "sndwnd": 512,   
            "rcvwnd": 512,
            "mtu": 1350
        },
        "aggressive": {
            "nodelay": 0,      
            "interval": 10,  
            "resend": 2,
            "nc": 1,          
            "sndwnd": 2048,  
            "rcvwnd": 2048,
            "mtu": 1400      
        },
        "latency": {
            "nodelay": 1,     
            "interval": 5,   
            "resend": 1,       
            "nc": 1,           
            "sndwnd": 256,    
            "rcvwnd": 256,
            "mtu": 1200        
        },
        "cpu-efficient": {
            "nodelay": 0,      
            "interval": 50,   
            "resend": 3,    
            "nc": 0,            
            "sndwnd": 128,     
            "rcvwnd": 128,
            "mtu": 1400     
        }
    }
    return profiles.get(profile.lower(), profiles["balanced"])

def get_default_advanced_config(transport: str) -> dict:
    """تنظیمات پیش‌فرض Advanced بر اساس transport - همگام با netrix.go فایل 3"""
    base_config = {
        "tcp_nodelay": True,
        "tcp_keepalive": 30,         
        "tcp_read_buffer": 8388608,  
        "tcp_write_buffer": 8388608, 
        "cleanup_interval": 60,      
        "session_timeout": 120,      
        "stream_timeout": 21600,    
        "stream_idle_timeout": 600,  
        "max_connections": 0,    
        "max_udp_flows": 5000,        
        "udp_flow_timeout": 600,    
        "tls_insecure_skip_verify": False, 
        "verbose": False
    }
    

    if transport in ("kcpmux", "kcp"):
        base_config.update({
            "udp_read_buffer": 4194304,  
            "udp_write_buffer": 4194304  
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
                         str_value.startswith('*') or str_value.startswith('&'))
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
        "frame_size": smux_default["frame_size"],
        "version": smux_default["version"],
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
    
    yaml_data["encryption"] = {
        "enabled": cfg.get("encryption_enabled", False),
        "algorithm": cfg.get("encryption_algorithm", "chacha"),
        "key": cfg.get("encryption_key", "")
    }
    
    yaml_data["stealth"] = {
        "padding_enabled": cfg.get("stealth_padding", False),
        "padding_min": 0,
        "padding_max": cfg.get("stealth_padding_max", 128),
        "jitter_enabled": cfg.get("stealth_jitter", False),
        "jitter_min_ms": 5,
        "jitter_max_ms": 20
    }

    yaml_data["health_port"] = cfg.get('health_port', 19080)
    
    if cfg.get("cert_file") and cfg.get("key_file"):
        yaml_data["cert_file"] = cfg["cert_file"]
        yaml_data["key_file"] = cfg["key_file"]
    
    if "max_sessions" in cfg:
        yaml_data["max_sessions"] = cfg['max_sessions']
    
    if "heartbeat" in cfg:
        yaml_data["heartbeat"] = cfg['heartbeat']
    
    if cfg.get('maps'):
        tcp_ports_list = []
        udp_ports_list = []
        
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
        
        if tcp_ports_list:
            yaml_data["tcp_ports"] = tcp_ports_list
        if udp_ports_list:
            yaml_data["udp_ports"] = udp_ports_list
    
    tun_cfg = cfg.get("tun_config") or {}
    yaml_data["tun"] = {
        "enabled": tun_cfg.get("enabled", False),
        "name": tun_cfg.get("name", "netrix0"),
        "local": tun_cfg.get("local", "10.200.0.1/30"),
        "mtu": tun_cfg.get("mtu", 1400),
        "routes": tun_cfg.get("routes", []),
        "streams": tun_cfg.get("streams", 1),
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
        "advanced.tcp_keepalive": f"TCP KeepAlive in seconds (default: 30)",
        "advanced.tcp_read_buffer": f"TCP read buffer in bytes (default: 8388608 = 8MB)",
        "advanced.tcp_write_buffer": f"TCP write buffer in bytes (default: 8388608 = 8MB)",
        "advanced.cleanup_interval": f"Cleanup interval in seconds (default: 60)",
        "advanced.session_timeout": f"Session timeout in seconds (default: 120 = 2 minutes - فقط برای sessions بدون heartbeat)",
        "advanced.connection_timeout": f"Connection timeout in seconds (default: 600 = 10 minutes)",
        "advanced.stream_timeout": f"Stream max lifetime in seconds (default: 21600 = 6 hours)",
        "advanced.stream_idle_timeout": f"Stream idle timeout in seconds (default: 600 = 10 minutes)",
        "advanced.max_connections": f"Max concurrent connections (default: 0 = use 5M limit, practically unlimited)",
        "advanced.max_udp_flows": f"Max UDP flows (default: 100000 for 10K+ users)",
        "advanced.udp_flow_timeout": f"UDP flow timeout in seconds (default: 7200 = 2 hours)",
        "advanced.tls_insecure_skip_verify": f"Skip TLS certificate verification (default: false - secure by default, can be enabled for self-signed certs)",
        "advanced.buffer_pool_size": f"Buffer pool size in bytes (default: 65536 = 64KB, 0 = use default, configurable)",
        "advanced.large_buffer_pool_size": f"Large buffer pool size in bytes (default: 65791 = maxUDPDataLen+256, 0 = use default, configurable)",
        "advanced.udp_frame_pool_size": f"UDP frame pool size in bytes (default: 65791 = maxUDPDataLen+256, 0 = use default, configurable)",
        "advanced.udp_data_slice_size": f"UDP data slice size in bytes (default: 1500 = MTU, 0 = use default, configurable)",
        "heartbeat": f"Heartbeat interval in seconds (default: 15, 0 = use default)",
        "verbose": f"Verbose logging (default: false)",
        "encryption.enabled": "Enable AEAD encryption (anti-DPI)",
        "encryption.algorithm": "Encryption algorithm: 'chacha' (default) or 'aes-gcm' (faster with AES-NI)",
        "encryption.key": "Encryption key (hex 32 bytes or password, empty = use PSK)",
        "stealth.padding_enabled": "Enable random padding (hides packet sizes)",
        "stealth.padding_min": "Minimum padding bytes (default: 0)",
        "stealth.padding_max": "Maximum padding bytes (default: 128)",
        "stealth.jitter_enabled": "Enable timing jitter (breaks timing patterns)",
        "stealth.jitter_min_ms": "Minimum jitter in ms (default: 5)",
        "stealth.jitter_max_ms": "Maximum jitter in ms (default: 20)",
        "tun.enabled": "Enable TUN mode (Layer 3 VPN)",
        "tun.name": "TUN interface name (default: netrix0)",
        "tun.local": "Local IP address with CIDR (e.g., 10.200.0.1/30)",
        "tun.mtu": "MTU size (default: 1400)",
        "tun.routes": "Networks to route through TUN",
        "tun.streams": "Number of parallel TUN streams (1-64, default: 1) - higher = better throughput",
        "tun.forward_l2tp": "Auto-add iptables DNAT rules for L2TP/IPsec ports (500,4500,1701) on server",
        "tun.l2tp_ports": "List of UDP ports to auto-forward for L2TP/IPsec (default: [500, 4500, 1701])",
        "tun.l2tp_dest_ip": "Optional DNAT destination IP for L2TP/IPsec (empty = use tun.local IP)",
        "tcp_ports": "TCP port mappings (string format like backhole: [\"443\", \"4000=5000\", \"500-567\"])",
        "udp_ports": "UDP port mappings (string format like backhole: [\"500-567\", \"4500\"])",
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
    
    write_yaml_with_comments(config_path, yaml_data, comments)
    
    try:
        os.chmod(config_path, 0o600)
    except Exception:
        pass
    
    return config_path

def create_client_config_file(cfg: dict) -> Path:
    """ساخت فایل کانفیگ YAML برای کلاینت"""
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    tport = cfg.get('tport', 0)
    if not tport:
        paths = cfg.get('paths', [])
        if paths:
            addr = paths[0].get('addr', '')
            tport = addr.split(':')[-1] if ':' in addr else '0'
    
    if tport and tport != '0':
        config_path = NETRIX_CONFIG_DIR / f"client_{tport}.yaml"
    else:
        config_path = NETRIX_CONFIG_DIR / "client.yaml"
    
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
                path_data["connection_pool"] = 8
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
        "frame_size": smux_default["frame_size"],
        "version": smux_default["version"],
        "mux_con": cfg.get('mux_con', smux_default.get("mux_con", 8))  # Fix: استفاده از mux_con از profile
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
    
    if "tls_insecure_skip_verify" in cfg:
        yaml_data["advanced"]["tls_insecure_skip_verify"] = cfg["tls_insecure_skip_verify"]
    
    yaml_data["verbose"] = cfg.get("verbose", False)
    
    yaml_data["encryption"] = {
        "enabled": cfg.get("encryption_enabled", False),
        "algorithm": cfg.get("encryption_algorithm", "chacha"),
        "key": cfg.get("encryption_key", "")
    }
    
    yaml_data["stealth"] = {
        "padding_enabled": cfg.get("stealth_padding", False),
        "padding_min": 0,
        "padding_max": cfg.get("stealth_padding_max", 128),
        "jitter_enabled": cfg.get("stealth_jitter", False),
        "jitter_min_ms": 5,
        "jitter_max_ms": 20
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
        "advanced.tcp_keepalive": f"TCP KeepAlive in seconds (default: 30)",
        "advanced.tcp_read_buffer": f"TCP read buffer in bytes (default: 8388608 = 8MB)",
        "advanced.tcp_write_buffer": f"TCP write buffer in bytes (default: 8388608 = 8MB)",
        "advanced.cleanup_interval": f"Cleanup interval in seconds (default: 60)",
        "advanced.session_timeout": f"Session timeout in seconds (default: 120 = 2 minutes - فقط برای sessions بدون heartbeat)",
        "advanced.connection_timeout": f"Connection timeout in seconds (default: 600 = 10 minutes)",
        "advanced.stream_timeout": f"Stream max lifetime in seconds (default: 21600 = 6 hours)",
        "advanced.stream_idle_timeout": f"Stream idle timeout in seconds (default: 600 = 10 minutes)",
        "advanced.max_connections": f"Max concurrent connections (default: 0 = use 5M limit, practically unlimited)",
        "advanced.max_udp_flows": f"Max UDP flows (default: 100000 for 10K+ users)",
        "advanced.udp_flow_timeout": f"UDP flow timeout in seconds (default: 7200 = 2 hours)",
        "advanced.tls_insecure_skip_verify": f"Skip TLS certificate verification (default: false - secure by default, can be enabled for self-signed certs)",
        "advanced.buffer_pool_size": f"Buffer pool size in bytes (default: 65536 = 64KB, 0 = use default, configurable)",
        "advanced.large_buffer_pool_size": f"Large buffer pool size in bytes (default: 65791 = maxUDPDataLen+256, 0 = use default, configurable)",
        "advanced.udp_frame_pool_size": f"UDP frame pool size in bytes (default: 65791 = maxUDPDataLen+256, 0 = use default, configurable)",
        "advanced.udp_data_slice_size": f"UDP data slice size in bytes (default: 1500 = MTU, 0 = use default, configurable)",
        "heartbeat": f"Heartbeat interval in seconds (default: 15, 0 = use default)",
        "verbose": f"Verbose logging (default: false)",
        "encryption.enabled": "Enable AEAD encryption (anti-DPI)",
        "encryption.algorithm": "Encryption algorithm: 'chacha' (default) or 'aes-gcm' (faster with AES-NI)",
        "encryption.key": "Encryption key (hex 32 bytes or password, empty = use PSK)",
        "stealth.padding_enabled": "Enable random padding (hides packet sizes)",
        "stealth.padding_min": "Minimum padding bytes (default: 0)",
        "stealth.padding_max": "Maximum padding bytes (default: 128)",
        "stealth.jitter_enabled": "Enable timing jitter (breaks timing patterns)",
        "stealth.jitter_min_ms": "Minimum jitter in ms (default: 5)",
        "stealth.jitter_max_ms": "Maximum jitter in ms (default: 20)",
        "tun.enabled": "Enable TUN mode (Layer 3 VPN)",
        "tun.name": "TUN interface name (default: netrix0)",
        "tun.local": "Local IP address with CIDR (e.g., 10.200.0.2/30)",
        "tun.mtu": "MTU size (default: 1400)",
        "tun.routes": "Networks to route through TUN",
        "tun.streams": "Number of parallel TUN streams (1-64, default: 1) - higher = better throughput",
        "proxy_protocol.enabled": "Enable PROXY Protocol (forwards real client IP to backend services) - must match server settings",
        "proxy_protocol.version": "PROXY Protocol version: 'v1' (text-based) or 'v2' (binary, default: v1) - must match server settings",
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
    
    NETRIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config_files_new = list(NETRIX_CONFIG_DIR.glob("server_*.yaml"))
    config_files_old = list(ROOT_DIR.glob("server*.yaml"))
    all_config_files = list(set(config_files_new + config_files_old))
    
    for config_file in all_config_files:
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
    
    client_files_new = list(NETRIX_CONFIG_DIR.glob("client*.yaml"))
    client_files_old = list(ROOT_DIR.glob("client*.yaml"))
    all_client_files = list(set(client_files_new + client_files_old))
    
    for config_file in all_client_files:
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
    """ریستارت تانل از طریق systemd service"""
    service_name = f"netrix-{config_path.stem}"
    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=15 
        )
        if result.returncode == 0:
            return True
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
RestartSec=2
TimeoutStartSec=10
TimeoutStopSec=5
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
    """پاک کردن iptables rules، routes و IP address برای تانل (L2TP forwarding)"""
    try:
        cfg = parse_yaml_config(config_path)
        if not cfg:
            return True 
        
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
        

        if tun_cfg.get("forward_l2tp", False):
            safe_name = ""
            for c in tun_name:
                if c.isalnum() or c == '_':
                    safe_name += c
                else:
                    safe_name += '_'

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
    """منوی ساخت/پیکربندی تانل"""
    while True:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{FG_CYAN}║{RESET}                      {BOLD}Create New Tunnel{RESET}                       {BOLD}{FG_CYAN}║{RESET}")
        print(f"{BOLD}{FG_CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        print(f"  {BOLD}{FG_GREEN}1){RESET} Iran Server")
        print(f"  {BOLD}{FG_BLUE}2){RESET} Kharej Client")
        print()
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
        
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{FG_CYAN}║{RESET}                {BOLD}Create Iran Server Tunnel{RESET}                 {BOLD}{FG_CYAN}║{RESET}")
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
        
        use_ipv6 = False
        if is_ipv6_available():
            print(f"  {FG_GREEN}✅ IPv6 is available on this system{RESET}")
            print(f"  {FG_WHITE}Note: For IPv6, server will listen on both IPv4 and IPv6{RESET}")
            use_ipv6 = ask_yesno(f"  {BOLD}Enable IPv6 support?{RESET}", default=False)
        else:
            print(f"  {FG_YELLOW}⚠️  IPv6 is NOT available on this system (disabled or not supported){RESET}")
            print(f"  {FG_WHITE}Server will listen on IPv4 only{RESET}")
        
        while True:
            tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            if is_port_in_use(tport):
                c_warn(f"  ⚠️  Port {FG_YELLOW}{tport}{RESET} is already in use!")
                if not ask_yesno(f"  {BOLD}Continue anyway?{RESET}", default=False):
                    continue
            break
        
        if use_ipv6:
            listen_addr = f"[::]:{tport}"
        else:
            listen_addr = f"0.0.0.0:{tport}"
        
        print(f"\n  {BOLD}{FG_CYAN}Security Settings:{RESET}")
        psk = ask_nonempty(f"  {BOLD}Pre-shared Key (PSK):{RESET}")
        
        encryption_enabled = ask_yesno(f"  {BOLD}Enable encryption?{RESET} {FG_WHITE}(anti-DPI){RESET}", default=False)
        encryption_key = ""
        encryption_algorithm = "chacha"
        stealth_padding = False
        stealth_padding_max = 0
        stealth_jitter = False
        
        if encryption_enabled:
            print(f"\n  {BOLD}{FG_CYAN}Encryption Algorithm:{RESET}")
            print(f"  {FG_BLUE}1){RESET} {FG_GREEN}ChaCha20-Poly1305{RESET} {FG_WHITE}(default - fast on all CPUs){RESET}")
            print(f"  {FG_BLUE}2){RESET} {FG_GREEN}AES-256-GCM{RESET} {FG_WHITE}(faster with AES-NI hardware){RESET}")
            algo_choice = ask_int(f"  {BOLD}Select algorithm:{RESET}", min_=1, max_=2, default=1)
            encryption_algorithm = "chacha" if algo_choice == 1 else "aes-gcm"
            
            print(f"  {FG_WHITE}Note: Leave empty to use PSK as encryption key{RESET}")
            try:
                encryption_key = input(f"  {BOLD}Encryption Key:{RESET} {FG_WHITE}(empty = use PSK){RESET} ").strip()
            except KeyboardInterrupt:
                print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                raise UserCancelled()
            
        print(f"\n  {BOLD}{FG_CYAN}Performance Profiles:{RESET}")
        print(f"  {FG_BLUE}1){RESET} {FG_GREEN}balanced{RESET} {FG_WHITE}(default - best overall){RESET}")
        print(f"  {FG_BLUE}2){RESET} {FG_GREEN}aggressive{RESET} {FG_WHITE}(high throughput, more CPU){RESET}")
        print(f"  {FG_BLUE}3){RESET} {FG_GREEN}latency{RESET} {FG_WHITE}(low latency priority){RESET}")
        print(f"  {FG_BLUE}4){RESET} {FG_GREEN}cpu-efficient{RESET} {FG_WHITE}(low CPU usage){RESET}")
        profile_choice = ask_int(f"\n  {BOLD}Select profile:{RESET}", min_=1, max_=4, default=1)
        profiles = {1: "balanced", 2: "aggressive", 3: "latency", 4: "cpu-efficient"}
        profile = profiles[profile_choice]
        
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
        print(f"  {FG_RED}IPv6 Support:{RESET} {FG_WHITE}[2001:db8::1]:443{RESET}")
        print(f"  {FG_RED}Mixed (Multiple formats):{RESET} {FG_WHITE}500,443-600:5201,192.168.1.1:666=8080{RESET}")
        
        try:
            tcp_input = input(f"\n  {BOLD}TCP Ports:{RESET} ").strip()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
        
        if tcp_input:
            try:
                tcp_maps = parse_advanced_ports(tcp_input, "tcp")
                maps.extend(tcp_maps)
                if tcp_maps:
                    c_ok(f"  ✅ Added {FG_GREEN}{len(tcp_maps)}{RESET} TCP mapping(s)")
            except ValueError as e:
                c_err(f"  ⚠️  Invalid: {e}")
        
        try:
            udp_input = input(f"  {BOLD}UDP Ports:{RESET} ").strip()
        except KeyboardInterrupt:
            print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
            raise UserCancelled()
        
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
        if transport == "wssmux":
            print(f"\n  {BOLD}🔐 TLS Certificate Configuration:{RESET}")
            print(f"  {FG_GREEN}1){RESET} Get new certificate (Let's Encrypt) - Recommended")
            print(f"  {FG_BLUE}2){RESET} Use existing certificate (provide file paths)")
            print(f"  {FG_YELLOW}3){RESET} Use test certificate (self-signed, auto-generated)")
            cert_choice = ask_int("\nSelect certificate type", min_=1, max_=3, default=1)
            
            if cert_choice == 1:
                while True:
                    try:
                        domain = input(f"\n  {BOLD}{FG_GREEN}Enter your domain:{RESET} {FG_WHITE}(e.g., example.com or sub.example.com){RESET} ").strip()
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
        
        heartbeat = ask_int(f"  {BOLD}Heartbeat Interval:{RESET} {FG_WHITE}(seconds, 0 = use default 15s){RESET}", min_=0, max_=300, default=0)
        
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
        
        print(f"\n  {BOLD}{FG_CYAN}TUN Mode (Layer 3 VPN):{RESET}")
        print(f"  {FG_WHITE}TUN mode creates a virtual network interface for full VPN functionality.{RESET}")
        print(f"  {FG_WHITE}Required for: L2TP/IPsec, OpenVPN (tun), WireGuard, etc.{RESET}")
        print(f"  {FG_YELLOW}⚠️  Note: Requires root privileges and Linux kernel support.{RESET}")
        tun_enabled = ask_yesno(f"  {BOLD}Enable TUN mode?{RESET}", default=False)
        
        tun_config = None
        if tun_enabled:
            print(f"\n  {BOLD}{FG_CYAN}TUN Configuration:{RESET}")
            tun_name = ask_nonempty(f"  {BOLD}Interface Name:{RESET}", default="netrix0")
            tun_local = ask_nonempty(f"  {BOLD}Local IP (CIDR):{RESET} {FG_WHITE}(e.g., 10.200.0.1/30){RESET}", default="10.200.0.1/30")
            tun_mtu = ask_int(f"  {BOLD}MTU:{RESET}", min_=576, max_=9000, default=1400)
            
            tun_routes = []
            print(f"  {FG_WHITE}Routes: Add networks to route through TUN (e.g., 192.168.1.0/24){RESET}")
            while True:
                try:
                    route = input(f"  {BOLD}Add Route:{RESET} {FG_WHITE}(empty to finish){RESET} ").strip()
                except KeyboardInterrupt:
                    print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                    raise UserCancelled()
                if not route:
                    break
                tun_routes.append(route)
                c_ok(f"  ✅ Route added: {route}")

            print(f"\n  {BOLD}{FG_CYAN}Multi-Stream TUN:{RESET}")
            print(f"  {FG_WHITE}Number of parallel TUN streams for better throughput (1-64).{RESET}")
            print(f"  {FG_WHITE}Higher values = better performance but more resource usage.{RESET}")
            tun_streams = ask_int(f"  {BOLD}TUN Streams:{RESET}", min_=1, max_=64, default=1)

            print(f"\n  {BOLD}{FG_CYAN}L2TP/IPsec Auto-Forward:{RESET}")
            print(f"  {FG_WHITE}Automatically forward UDP ports 500/4500/1701 to the TUN IP for external L2TP/IPsec servers.{RESET}")
            forward_l2tp = ask_yesno(
                f"  {BOLD}Enable auto-forward L2TP/IPsec ports (500,4500,1701)?{RESET}", default=True
            )

            l2tp_dest_ip = ""
            if forward_l2tp:
                print(f"  {FG_WHITE}DNAT Destination IP:{RESET}")
                print(f"  {FG_WHITE}- Leave empty to use the server TUN IP (tun.local){RESET}")
                print(f"  {FG_WHITE}- Or enter the remote/peer TUN IP (e.g., client-side TUN IP) if you want DNAT to that.{RESET}")
                try:
                    l2tp_dest_ip = input(f"  {BOLD}L2TP DNAT Destination IP:{RESET} {FG_WHITE}(optional){RESET} ").strip()
                except KeyboardInterrupt:
                    print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                    raise UserCancelled()
            
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
            c_ok(f"  ✅ TUN mode configured: {tun_name} ({tun_local})")
        
        # PROXY Protocol settings
        print(f"\n  {BOLD}{FG_CYAN}PROXY Protocol:{RESET}")
        print(f"  {FG_WHITE}PROXY Protocol forwards real client IP to backend services.{RESET}")
        print(f"  {FG_WHITE}Required for: V2ray, OpenVPN, and other services that need real client IP.{RESET}")
        print(f"  {FG_WHITE}Useful for: Rate limiting, logging, and security based on real client IP.{RESET}")
        proxy_protocol_enabled = ask_yesno(f"  {BOLD}Enable PROXY Protocol?{RESET}", default=False)
        proxy_protocol_version = "v1"
        proxy_protocol_ports = []
        if proxy_protocol_enabled:
            print(f"\n  {BOLD}{FG_CYAN}PROXY Protocol Version:{RESET}")
            print(f"  {FG_BLUE}1){RESET} {FG_GREEN}v1{RESET} {FG_WHITE}(text-based, simple, compatible){RESET}")
            print(f"  {FG_BLUE}2){RESET} {FG_GREEN}v2{RESET} {FG_WHITE}(binary, efficient, modern){RESET}")
            version_choice = ask_int(f"  {BOLD}Select version:{RESET}", min_=1, max_=2, default=1)
            proxy_protocol_version = "v1" if version_choice == 1 else "v2"
            
            print(f"\n  {BOLD}{FG_CYAN}PROXY Protocol Ports:{RESET}")
            print(f"  {FG_WHITE}Enter ports that should use PROXY Protocol (comma-separated){RESET}")
            print(f"  {FG_WHITE}Example: 2083,2093 or 2083,2093,443{RESET}")
            print(f"  {FG_YELLOW}⚠️  Only these ports will have PROXY Protocol header{RESET}")
            print(f"  {FG_YELLOW}⚠️  Other ports will work normally without PROXY Protocol{RESET}")
            try:
                ports_input = input(f"  {BOLD}PROXY Protocol Ports:{RESET} {FG_WHITE}(comma-separated, empty = all ports){RESET} ").strip()
            except KeyboardInterrupt:
                print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                raise UserCancelled()
            
            if ports_input:
                ports_list = [p.strip() for p in ports_input.split(",") if p.strip()]
                proxy_protocol_ports = ports_list
                if proxy_protocol_ports:
                    c_ok(f"  ✅ PROXY Protocol enabled for {FG_GREEN}{len(proxy_protocol_ports)}{RESET} port(s): {FG_CYAN}{', '.join(proxy_protocol_ports)}{RESET}")
            else:
                c_ok(f"  ✅ PROXY Protocol enabled for {FG_GREEN}all ports{RESET}")
        else:
            c_ok(f"  ✅ PROXY Protocol disabled")
        
        cfg = {
            "tport": tport,
            "listen": listen_addr,
            "transport": transport,
            "psk": psk,
            "profile": profile,
            "maps": maps,
            "verbose": verbose,
            "max_sessions": max_sessions,  
            "heartbeat": heartbeat, 
            "buffer_pool_config": buffer_pool_config,
            "encryption_enabled": encryption_enabled,
            "encryption_algorithm": encryption_algorithm,
            "encryption_key": encryption_key,
            "stealth_padding": stealth_padding,
            "stealth_padding_max": stealth_padding_max,
            "stealth_jitter": stealth_jitter,
            "tun_config": tun_config,
            "proxy_protocol_enabled": proxy_protocol_enabled,
            "proxy_protocol_version": proxy_protocol_version,
            "proxy_protocol_ports": proxy_protocol_ports
        }
        
        if cert_file and key_file:
            cfg["cert_file"] = cert_file
            cfg["key_file"] = key_file
        
        config_path = create_server_config_file(tport, cfg)
        
        print()
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        c_ok(f"  ✅ Configuration saved: {FG_WHITE}{config_path}{RESET}")
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        
        print()
        if ask_yesno(f"  {BOLD}{FG_GREEN}Start tunnel now?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
            if run_tunnel(config_path):
                c_ok(f"  ✅ Tunnel started successfully!")
            else:
                c_err("  ❌ Failed to start tunnel!")
        
        pause()
    except UserCancelled:
        return

def create_client_tunnel():
    """ساخت تانل کلاینت (Kharej)"""
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
        
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{FG_CYAN}║{RESET}               {BOLD}Create Kharej Client Tunnel{RESET}                {BOLD}{FG_CYAN}║{RESET}")
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
        
        tls_insecure_skip_verify = False
        if transport == "wssmux":
            print(f"\n  {BOLD}🔐 Server Certificate Type:{RESET}")
            print(f"  {FG_WHITE}What type of certificate does the Iran server use?{RESET}")
            print(f"  {FG_GREEN}1){RESET} Let's Encrypt (real certificate) - Recommended")
            print(f"  {FG_YELLOW}2){RESET} Self-signed certificate (for testing)")
            cert_type = ask_int("\n  Select server certificate type", min_=1, max_=2, default=1)
            
            if cert_type == 2:
                tls_insecure_skip_verify = True
                c_warn("  ⚠️  tls_insecure_skip_verify will be set to true (for self-signed certificate)")
            else:
                tls_insecure_skip_verify = False
                c_ok("  ✅ tls_insecure_skip_verify will be set to false (for Let's Encrypt)")
        
        print(f"\n  {BOLD}{FG_CYAN}Server Connection:{RESET}")
        if transport == "wssmux":
            print(f"  {FG_WHITE}Domain example: example.com or sub.example.com{RESET}")
            print(f"  {FG_YELLOW}⚠️  Note: For Let's Encrypt, you must use domain (not IP address){RESET}")
            server_domain = ask_nonempty(f"  {BOLD}Server Domain:{RESET}")
            tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            server_addr = f"{server_domain}:{tport}"
        else:
            print(f"  {FG_WHITE}IPv4 example: 1.2.3.4{RESET}")
            print(f"  {FG_WHITE}IPv6 example: 2001:db8::1 or fd00::1{RESET}")
            server_ip = ask_nonempty(f"  {BOLD}Iran Server IP:{RESET}")
            tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
            
            if ':' in server_ip and not server_ip.startswith('['):
                server_addr = f"[{server_ip}]:{tport}"
                print(f"  {FG_GREEN}✅ IPv6 detected, formatted as: {server_addr}{RESET}")
            else:
                server_addr = f"{server_ip}:{tport}"
        
        print(f"\n  {BOLD}{FG_CYAN}Security Settings:{RESET}")
        print(f"  {FG_WHITE}Note: Must match server settings!{RESET}")
        psk = ask_nonempty(f"  {BOLD}Pre-shared Key (PSK):{RESET}")
        
        encryption_enabled = ask_yesno(f"  {BOLD}Enable encryption?{RESET} {FG_WHITE}(anti-DPI){RESET}", default=False)
        encryption_key = ""
        encryption_algorithm = "chacha"
        stealth_padding = False
        stealth_padding_max = 0
        stealth_jitter = False
        
        if encryption_enabled:
            print(f"\n  {BOLD}{FG_CYAN}Encryption Algorithm:{RESET} {FG_WHITE}(must match server!){RESET}")
            print(f"  {FG_BLUE}1){RESET} {FG_GREEN}ChaCha20-Poly1305{RESET} {FG_WHITE}(default - fast on all CPUs){RESET}")
            print(f"  {FG_BLUE}2){RESET} {FG_GREEN}AES-256-GCM{RESET} {FG_WHITE}(faster with AES-NI hardware){RESET}")
            algo_choice = ask_int(f"  {BOLD}Select algorithm:{RESET}", min_=1, max_=2, default=1)
            encryption_algorithm = "chacha" if algo_choice == 1 else "aes-gcm"
            
            print(f"  {FG_WHITE}Note: Leave empty to use PSK as encryption key{RESET}")
            try:
                encryption_key = input(f"  {BOLD}Encryption Key:{RESET} {FG_WHITE}(empty = use PSK){RESET} ").strip()
            except KeyboardInterrupt:
                print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                raise UserCancelled()
            
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
        connection_pool = ask_int(f"  {BOLD}Connection Pool:{RESET} {FG_WHITE}(recommended: 8-16){RESET}", min_=1, max_=100, default=8)
        smux_default = get_default_smux_config(profile)
        default_mux_con = smux_default.get("mux_con", 8)
        mux_con = ask_int(f"  {BOLD}Mux Con:{RESET} {FG_WHITE}(recommended: {default_mux_con} for {profile} profile){RESET}", min_=1, max_=100, default=default_mux_con)
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
            
            print(f"\n  {BOLD}Transport Types:{RESET}")
            print(f"  {FG_CYAN}1){RESET} {FG_GREEN}tcpmux{RESET} (TCP with smux)")
            print(f"  {FG_CYAN}2){RESET} {FG_GREEN}kcpmux{RESET} (KCP with smux)")
            print(f"  {FG_CYAN}3){RESET} {FG_GREEN}wsmux{RESET} (WebSocket with smux)")
            print(f"  {FG_CYAN}4){RESET} {FG_GREEN}wssmux{RESET} (WebSocket Secure with smux)")
            new_transport_choice = ask_int(f"\n  {BOLD}Select transport:{RESET}", min_=1, max_=4, default=1)
            new_transport = transports[new_transport_choice]
            
            if new_transport == "wssmux":
                print(f"  {FG_WHITE}Domain example: example.com or sub.example.com{RESET}")
                print(f"  {FG_YELLOW}⚠️  Note: For Let's Encrypt, you must use domain (not IP address){RESET}")
                new_server_domain = ask_nonempty(f"  {BOLD}Server Domain:{RESET}")
                new_tport = ask_int(f"  {BOLD}Tunnel Port:{RESET}", min_=1, max_=65535)
                new_server_addr = f"{new_server_domain}:{new_tport}"
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
            
            paths.append(new_path_dict)
            
            print(f"  {FG_GREEN}✅ Backup server added:{RESET} {FG_CYAN}{new_transport}://{new_server_addr}{RESET} {FG_WHITE}({new_connection_pool} connections){RESET}")
        

        print(f"\n  {BOLD}{FG_CYAN}Advanced Options:{RESET}")
        verbose = ask_yesno(f"  {BOLD}Enable verbose logging (for debugging)?{RESET}", default=False)
        
        heartbeat = ask_int(f"  {BOLD}Heartbeat Interval:{RESET} {FG_WHITE}(seconds, 0 = use default 15s){RESET}", min_=0, max_=300, default=0)
        
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
        
        print(f"\n  {BOLD}{FG_CYAN}TUN Mode (Layer 3 VPN):{RESET}")
        print(f"  {FG_WHITE}TUN mode creates a virtual network interface for full VPN functionality.{RESET}")
        print(f"  {FG_WHITE}Required for: L2TP/IPsec, OpenVPN (tun), WireGuard, etc.{RESET}")
        print(f"  {FG_YELLOW}⚠️  Note: Requires root privileges and Linux kernel support.{RESET}")
        tun_enabled = ask_yesno(f"  {BOLD}Enable TUN mode?{RESET}", default=False)
        
        tun_config = None
        if tun_enabled:
            print(f"\n  {BOLD}{FG_CYAN}TUN Configuration:{RESET}")
            tun_name = ask_nonempty(f"  {BOLD}Interface Name:{RESET}", default="netrix0")
            tun_local = ask_nonempty(f"  {BOLD}Local IP (CIDR):{RESET} {FG_WHITE}(e.g., 10.200.0.2/30){RESET}", default="10.200.0.2/30")
            tun_mtu = ask_int(f"  {BOLD}MTU:{RESET}", min_=576, max_=9000, default=1400)
            
            tun_routes = []
            print(f"  {FG_WHITE}Routes: Add networks to route through TUN (e.g., 192.168.1.0/24){RESET}")
            while True:
                try:
                    route = input(f"  {BOLD}Add Route:{RESET} {FG_WHITE}(empty to finish){RESET} ").strip()
                except KeyboardInterrupt:
                    print(f"\n\n  {FG_YELLOW}Cancelled.{RESET}")
                    raise UserCancelled()
                if not route:
                    break
                tun_routes.append(route)
                c_ok(f"  ✅ Route added: {route}")

            print(f"\n  {BOLD}{FG_CYAN}Multi-Stream TUN:{RESET}")
            print(f"  {FG_WHITE}Number of parallel TUN streams for better throughput (1-64).{RESET}")
            print(f"  {FG_WHITE}Higher values = better performance but more resource usage.{RESET}")
            tun_streams = ask_int(f"  {BOLD}TUN Streams:{RESET}", min_=1, max_=64, default=1)
            
            tun_config = {
                "enabled": True,
                "name": tun_name,
                "local": tun_local,
                "mtu": tun_mtu,
                "routes": tun_routes,
                "streams": tun_streams
            }
            c_ok(f"  ✅ TUN mode configured: {tun_name} ({tun_local})")
        
        print(f"\n  {BOLD}{FG_CYAN}PROXY Protocol:{RESET}")
        print(f"  {FG_WHITE}PROXY Protocol forwards real client IP to backend services.{RESET}")
        print(f"  {FG_WHITE}Required for: V2ray, OpenVPN, and other services that need real client IP.{RESET}")
        print(f"  {FG_WHITE}Useful for: Rate limiting, logging, and security based on real client IP.{RESET}")
        proxy_protocol_enabled = ask_yesno(f"  {BOLD}Enable PROXY Protocol?{RESET}", default=False)
        proxy_protocol_version = "v1"
        if proxy_protocol_enabled:
            print(f"\n  {BOLD}{FG_CYAN}PROXY Protocol Version:{RESET}")
            print(f"  {FG_BLUE}1){RESET} {FG_GREEN}v1{RESET} {FG_WHITE}(text-based, simple, compatible){RESET}")
            print(f"  {FG_BLUE}2){RESET} {FG_GREEN}v2{RESET} {FG_WHITE}(binary, efficient, modern){RESET}")
            version_choice = ask_int(f"  {BOLD}Select version:{RESET}", min_=1, max_=2, default=1)
            proxy_protocol_version = "v1" if version_choice == 1 else "v2"
            c_ok(f"  ✅ PROXY Protocol enabled (v{proxy_protocol_version}) - ports configured on server")
        else:
            c_ok(f"  ✅ PROXY Protocol disabled")
        
        cfg = {
            "psk": psk,
            "profile": profile,
            "mux_con": mux_con,
            "paths": paths,
            "tls_insecure_skip_verify": tls_insecure_skip_verify,
            "verbose": verbose,
            "heartbeat": heartbeat,
            "buffer_pool_config": buffer_pool_config,
            "encryption_enabled": encryption_enabled,
            "encryption_algorithm": encryption_algorithm,
            "encryption_key": encryption_key,
            "stealth_padding": stealth_padding,
            "stealth_padding_max": stealth_padding_max,
            "stealth_jitter": stealth_jitter,
            "tun_config": tun_config,
            "proxy_protocol_enabled": proxy_protocol_enabled,
            "proxy_protocol_version": proxy_protocol_version,
            "proxy_protocol_ports": []
        }
        
        config_path = create_client_config_file(cfg)
        
        print()
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        c_ok(f"  ✅ Configuration saved: {FG_WHITE}{config_path}{RESET}")
        print(f"  {BOLD}{FG_CYAN}{'═' * 60}{RESET}")
        
        print()
        if ask_yesno(f"  {BOLD}{FG_GREEN}Start tunnel now?{RESET}", default=True):
            print(f"\n  {FG_CYAN}Creating systemd service and starting tunnel...{RESET}")
            if run_tunnel(config_path):
                c_ok(f"  ✅ Tunnel started successfully!")
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
        print(f"{BOLD}{FG_CYAN}║{RESET}                          {BOLD}Status{RESET}                          {BOLD}{FG_CYAN}║{RESET}")
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
        print(f"{BOLD}{FG_CYAN}║{RESET}                    {BOLD}Tunnel Details{RESET}                        {BOLD}{FG_CYAN}║{RESET}")
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
        else:
            c_err("  ❌ Invalid choice. Please select 0, 1, 2, or 3.")
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
    print(f"{BOLD}{FG_CYAN}║{RESET}                     {BOLD}Health Check{RESET}                         {BOLD}{FG_CYAN}║{RESET}")
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
        ("http://localhost:19080/health", "Simple Health Check"),
        ("http://localhost:19080/health/detailed", "Detailed Health Check")
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
                            
                            if "tcp_in" in data and isinstance(data["tcp_in"], dict):
                                print(f"    {BOLD}TCP In:{RESET} {FG_CYAN}{data['tcp_in']['formatted']}{RESET}")
                                print(f"    {BOLD}TCP Out:{RESET} {FG_CYAN}{data['tcp_out']['formatted']}{RESET}")
                                print(f"    {BOLD}UDP In:{RESET} {FG_CYAN}{data['udp_in']['formatted']}{RESET}")
                                print(f"    {BOLD}UDP Out:{RESET} {FG_CYAN}{data['udp_out']['formatted']}{RESET}")
                                if "total_traffic" in data:
                                    print(f"    {BOLD}Total Traffic:{RESET} {FG_GREEN}{data['total_traffic']['formatted']}{RESET}")
                            elif "tcp_in_mb" in data:
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
            print(f"    {FG_YELLOW}⚠️  Health check server may not be running on port 19080{RESET}")
        except Exception as e:
            print(f"    {FG_RED}❌ Error: {e}{RESET}")
        print()
    
    pause()

def stop_tunnel_menu():
    """منوی توقف تانل"""
    clear()
    print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{FG_CYAN}║{RESET}                       {BOLD}Stop Tunnel{RESET}                        {BOLD}{FG_CYAN}║{RESET}")
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
                time.sleep(1)
                print(f"  {FG_CYAN}Cleaning up iptables rules...{RESET}", end='', flush=True)
                if cleanup_iptables_rules(config_path):
                    print(f" {FG_GREEN}✅{RESET}")
                else:
                    print(f" {FG_YELLOW}⚠️{RESET}")
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
    print(f"{BOLD}{FG_CYAN}║{RESET}                     {BOLD}Restart Tunnel{RESET}                       {BOLD}{FG_CYAN}║{RESET}")
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
            
            print(f"\n  {FG_CYAN}Restarting tunnel...{RESET}", end='', flush=True)
            if restart_tunnel(config_path):
                print(f" {FG_GREEN}✅{RESET}")
                c_ok(f"  ✅ Tunnel restarted successfully.")
            else:
                print(f" {FG_RED}❌{RESET}")
                c_err(f"  ❌ Failed to restart tunnel.")
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
    print(f"{BOLD}{FG_RED}║{RESET}                      {BOLD}Delete Tunnel{RESET}                       {BOLD}{FG_RED}║{RESET}")
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
            
            print(f"  {FG_CYAN}Cleaning up routes and iptables rules...{RESET}", end='', flush=True)
            if cleanup_iptables_rules(config_path):
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
        print(f"{BOLD}{FG_CYAN}║{RESET}                {BOLD}Install/Update Core{RESET}                    {BOLD}{FG_CYAN}║{RESET}")
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
        print(f"{BOLD}{FG_CYAN}║{RESET}                   {BOLD}Install Netrix Core{RESET}                    {BOLD}{FG_CYAN}║{RESET}")
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
        return

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
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{FG_CYAN}║{RESET}                   {BOLD}Update Netrix Core{RESET}                     {BOLD}{FG_CYAN}║{RESET}")
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
        return

def delete_netrix_core():
    """حذف هسته Netrix"""
    try:
        clear()
        print(f"{BOLD}{FG_CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{FG_CYAN}║{RESET}                   {BOLD}Delete Netrix Core{RESET}                     {BOLD}{FG_CYAN}║{RESET}")
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
        print(f"{BOLD}{FG_CYAN}║{RESET}                     {BOLD}System Optimizer{RESET}                     {BOLD}{FG_CYAN}║{RESET}")
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
        print(f"{FG_WHITE}    Tunnel Management Script          {FG_YELLOW}v{VERSION}{RESET}")
        
        core_installed = os.path.exists(NETRIX_BINARY)
        if core_installed:
            print(f"    {FG_GREEN}Core Status: ✅ Installed{RESET}")
        else:
            print(f"    {FG_RED}Core Status: ❌ Not Installed{RESET}")
        
        server_ip = get_server_ip()
        if server_ip:
            print(f"    {FG_CYAN}Server IP: {FG_WHITE}{server_ip}{RESET}")
        
        print(f"    {FG_CYAN}Support: {FG_WHITE}@g0dline{RESET}")
        print()
        print(f"  {BOLD}{FG_GREEN}1){RESET} Create Tunnel")
        print(f"  {BOLD}{FG_BLUE}2){RESET} Status")
        print(f"  {BOLD}{FG_YELLOW}3){RESET} Stop")
        print(f"  {BOLD}{FG_MAGENTA}4){RESET} Restart")
        print(f"  {BOLD}{FG_RED}5){RESET} Delete")
        print(f"  {BOLD}{FG_CYAN}6){RESET} Install/Update Core")
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


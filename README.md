# Netrix - Advanced Reverse Tunneling Solution

[![Go Version](https://img.shields.io/badge/Go-1.20+-00ADD8?style=flat&logo=go)](https://golang.org/)
[![Release](https://img.shields.io/badge/Release-Stable-green.svg)](https://github.com/Karrari-Dev/Netrix-/releases)

---

## 🌐 Language | زبان

**English** | [فارسی (Persian)](#درباره-تونل-معکوس-netrix)

---

## About Netrix Reverse Tunneling

**Netrix** is an advanced and professional reverse tunneling solution designed for NAT traversal, firewall bypass, and network restrictions.

### What is Reverse Tunneling?

Reverse tunneling is a network technique that allows you to connect from a restricted network (like home or corporate network with NAT and firewall) to an external server, then use that server to access local services.

**How it works:**
1. Client (inside restricted network) connects to external server
2. Server accesses local services through this connection
3. Users connect to local services through the server

### Key Features

- ✅ **NAT Traversal** - No port forwarding required
- ✅ **Multiple Transports** - TCP, KCP, WebSocket, Secure WebSocket
- ✅ **Stream Multiplexing** - Multiple connections over single tunnel (SMUX)
- ✅ **Full UDP Support** - Frame protocol for UDP traversal
- ✅ **ChaCha20-Poly1305 Encryption** - Anti-DPI with AEAD encryption
- ✅ **Stealth Mode** - Random padding and timing jitter
- ✅ **TUN Mode** - Layer 3 VPN for L2TP/IPsec, WireGuard
- ✅ **IPv6 Support** - Full IPv4 and IPv6 compatibility
- ✅ **Multi-Path** - Multiple server paths with automatic failover
- ✅ **Health Check API** - Built-in monitoring endpoints
- ✅ **Performance Profiles** - Pre-configured optimization profiles
- ✅ **License Management** - Built-in license validation

### Use Cases

- 🎮 **Gaming** - Connect to game servers behind NAT
- 🖥️ **Remote Access** - Access local services remotely
- 📡 **Service Exposure** - Expose local services to internet
- 🔒 **Bypass Restrictions** - Bypass network restrictions
- 🌐 **VPN Alternative** - Alternative to traditional VPN

---

## Architecture

Netrix uses a multi-layer architecture:

### 1. Transport Layer (TCP, KCP, WebSocket, WSS)
- **TCP (tcpmux)** - Reliable and stable
- **KCP (kcpmux)** - Fast, low latency for gaming
- **WebSocket (wsmux)** - Bypass HTTP-aware firewalls
- **WSS (wssmux)** - Secure with TLS/SSL

### 2. SMUX Layer (Stream Multiplexing)
- Multiple streams over one transport connection
- Reduced overhead and optimal usage
- Concurrent connection capability
- Configurable mux_con for nested multiplexing

### 3. Session Manager Layer
- Session pool management
- Health-aware load balancing (least-loaded)
- Precise stream tracking
- Automatic slow session detection

### 4. Frame Protocol for UDP
- Encapsulate UDP packets in frames
- UDP traversal through tunnel
- Multiple UDP flow management

### 5. Encryption Layer (Optional)
- ChaCha20-Poly1305 AEAD encryption
- Per-direction nonce counters
- Random padding (anti-DPI)
- Timing jitter (anti-DPI)

### 6. TUN Mode (Layer 3 VPN)
- Virtual network interface
- Full IP packet forwarding
- Route configuration
- Support for L2TP/IPsec, WireGuard

---

## Performance Profiles

Netrix provides 4 pre-configured performance profiles:

| Profile | Use Case | SMUX Keepalive | SMUX Buffer | KCP Interval | KCP Windows | Best For |
|---------|----------|----------------|-------------|--------------|-------------|----------|
| **balanced** (default) | General purpose | 20s | 4MB | 20ms | 512/512 | Most users |
| **aggressive** | High throughput | 30s | 8MB | 10ms | 2048/2048 | Maximum speed |
| **latency** | Low latency | 5s | 2MB | 5ms | 256/256 | Gaming, real-time |
| **cpu-efficient** | Low CPU usage | 60s | 2MB | 50ms | 128/128 | Resource-constrained |

### Profile Details

- **balanced**: Best overall performance. Good balance between latency, throughput, and CPU usage.
- **aggressive**: Maximum throughput. Uses more CPU and memory. Best for high-bandwidth applications.
- **latency**: Optimized for low latency. Best for gaming, video calls, and real-time applications.
- **cpu-efficient**: Minimizes CPU usage. Best for servers with limited resources.

---

## Installation

### Quick Install (One Command)

```bash
wget https://raw.githubusercontent.com/Karrari-Dev/Netrix-/main/netrix-manager.py -O /usr/local/bin/netrix-manager.py && chmod +x /usr/local/bin/netrix-manager.py && echo 'alias netrix-manager="python3 /usr/local/bin/netrix-manager.py"' >> ~/.bashrc && source ~/.bashrc
```

After installation, just run:
```bash
netrix-manager
```

### Manual Installation

```bash
# Download binary for your architecture
# AMD64
wget https://github.com/Karrari-Dev/Netrix-/releases/download/v2.0.0/netrix-amd64.tar.gz
tar -xzf netrix-amd64.tar.gz
mv netrix /usr/local/bin/

# ARM64
wget https://github.com/Karrari-Dev/Netrix-/releases/download/v2.0.0/netrix-arm64.tar.gz
tar -xzf netrix-arm64.tar.gz
mv netrix /usr/local/bin/
```

---

## Configuration

### Server Configuration (Iran)

```yaml
mode: "server"
listen: "0.0.0.0:4000"           # Use [::]:4000 for IPv6
transport: "tcpmux"              # tcpmux|kcpmux|wsmux|wssmux
psk: "your_secret_key_here"
profile: "balanced"              # balanced|aggressive|latency|cpu-efficient

# Port mappings (simplified format)
tcp_ports: [2066, 9988, 6665]    # TCP ports to forward
udp_ports: [2066, 9988]          # UDP ports to forward

# SMUX settings
smux:
  keepalive: 20                  # seconds (default: 20)
  max_recv: 4194304              # 4MB (default)
  max_stream: 2097152            # 2MB (default)
  frame_size: 32768              # 32KB (default)
  version: 2                     # SMUX version
  mux_con: 8                     # multiplexed connections

# KCP settings (only for kcpmux)
kcp:
  nodelay: 0                     # 0=batching, 1=no batching
  interval: 20                   # ms (update interval)
  resend: 2                      # fast resend threshold
  nc: 0                          # 0=congestion control, 1=no CC
  sndwnd: 512                    # send window
  rcvwnd: 512                    # receive window
  mtu: 1350                      # MTU

# Advanced settings
advanced:
  tcp_nodelay: true
  tcp_keepalive: 30              # seconds
  tcp_read_buffer: 8388608       # 8MB
  tcp_write_buffer: 8388608      # 8MB
  cleanup_interval: 60           # seconds
  session_timeout: 120           # seconds
  connection_timeout: 600        # seconds
  stream_timeout: 21600          # 6 hours
  stream_idle_timeout: 600       # 10 minutes
  max_connections: 0             # 0 = unlimited (1M limit)
  max_udp_flows: 5000
  udp_flow_timeout: 600          # seconds

# Encryption (ChaCha20-Poly1305)
encryption:
  enabled: false                 # enable encryption
  key: ""                        # empty = use PSK

# Stealth (anti-DPI)
stealth:
  padding_enabled: false
  padding_min: 0
  padding_max: 128
  jitter_enabled: false
  jitter_min_ms: 5
  jitter_max_ms: 20

# TUN Mode (Layer 3 VPN)
tun:
  enabled: false
  name: "netrix0"
  local: "10.200.0.1/30"
  mtu: 1400
  routes: []

# Health check
health_port: 19080               # default: 19080
heartbeat: 20                    # seconds (default: 20)
verbose: false
```

### Client Configuration (Kharej)

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

# Multi-path support (multiple servers)
paths:
  - transport: "tcpmux"
    addr: "SERVER_IP:4000"       # IPv6: [2001:db8::1]:4000
    connection_pool: 24          # recommended: 8-24
    aggressive_pool: false
    retry_interval: 3            # seconds
    dial_timeout: 10             # seconds
  # Backup server (optional)
  - transport: "tcpmux"
    addr: "BACKUP_IP:4000"
    connection_pool: 8
    retry_interval: 5
    dial_timeout: 10

# SMUX settings
smux:
  keepalive: 20
  max_recv: 4194304
  max_stream: 2097152
  frame_size: 32768
  version: 2
  mux_con: 10                    # recommended: 8-16

# KCP settings (if using kcpmux)
kcp:
  nodelay: 0
  interval: 20
  resend: 2
  nc: 0
  sndwnd: 512
  rcvwnd: 512
  mtu: 1350

# Advanced settings
advanced:
  tcp_nodelay: true
  tcp_keepalive: 30
  tcp_read_buffer: 8388608
  tcp_write_buffer: 8388608
  cleanup_interval: 60
  session_timeout: 120
  connection_timeout: 600
  stream_timeout: 21600
  stream_idle_timeout: 600
  max_connections: 0
  max_udp_flows: 5000
  udp_flow_timeout: 600

# Encryption (must match server)
encryption:
  enabled: false
  key: ""

# Stealth (must match server)
stealth:
  padding_enabled: false
  padding_min: 0
  padding_max: 128
  jitter_enabled: false
  jitter_min_ms: 5
  jitter_max_ms: 20

# TUN Mode (must match server)
tun:
  enabled: false
  name: "netrix0"
  local: "10.200.0.2/30"         # Different from server!
  mtu: 1400
  routes: ["0.0.0.0/0"]          # Route all traffic

heartbeat: 20
verbose: false
```

---

## Running Netrix

### Using Config File

```bash
# Server
netrix -config /root/server4000.yaml

# Client
netrix -config /root/client_SERVER_IP_4000.yaml
```

### Using Systemd (Recommended)

The `netrixcore.py` script automatically creates systemd services:

```bash
# Check status
systemctl status netrix-server4000

# Start/Stop/Restart
systemctl start netrix-server4000
systemctl stop netrix-server4000
systemctl restart netrix-server4000

# View logs
journalctl -u netrix-server4000 -f
```

---

## Health Check API

Netrix provides built-in health check endpoints on port 19080:

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | Simple liveness check |
| `/health/ready` | Readiness check (sessions active) |
| `/health/detailed` | Detailed stats (JSON) |

### Example Response (/health/detailed)

```json
{
  "status": "healthy",
  "sessions": 4,
  "streams": 128,
  "rtt_ms": 45,
  "tcp_in": {"bytes": 1073741824, "formatted": "1.00 GB"},
  "tcp_out": {"bytes": 536870912, "formatted": "512.00 MB"},
  "udp_in": {"bytes": 104857600, "formatted": "100.00 MB"},
  "udp_out": {"bytes": 52428800, "formatted": "50.00 MB"},
  "total_traffic": {"bytes": 1768000000, "formatted": "1.65 GB"}
}
```

---

## Transport Examples

### TCP Multiplexing (tcpmux)

Best for: General purpose, reliable connections

**Server:**
```yaml
mode: "server"
listen: "0.0.0.0:4000"
transport: "tcpmux"
psk: "your_secret_key"
profile: "balanced"
tcp_ports: [2066]
udp_ports: [2066]
```

**Client:**
```yaml
mode: "client"
psk: "your_secret_key"
profile: "balanced"
paths:
  - transport: "tcpmux"
    addr: "SERVER_IP:4000"
    connection_pool: 16
```

### KCP Multiplexing (kcpmux)

Best for: Gaming, low latency applications

**Server:**
```yaml
mode: "server"
listen: "0.0.0.0:4001"
transport: "kcpmux"
psk: "your_secret_key"
profile: "latency"
tcp_ports: [2066]
udp_ports: [2066]
kcp:
  nodelay: 1
  interval: 5
  resend: 1
  nc: 1
  sndwnd: 256
  rcvwnd: 256
  mtu: 1200
```

**Client:**
```yaml
mode: "client"
psk: "your_secret_key"
profile: "latency"
paths:
  - transport: "kcpmux"
    addr: "SERVER_IP:4001"
    connection_pool: 8
    aggressive_pool: true
```

### WebSocket Multiplexing (wsmux)

Best for: Bypassing HTTP-aware firewalls

**Server:**
```yaml
mode: "server"
listen: "0.0.0.0:8080"
transport: "wsmux"
psk: "your_secret_key"
profile: "balanced"
tcp_ports: [2066]
udp_ports: [2066]
advanced:
  websocket_read_buffer: 524288
  websocket_write_buffer: 524288
  websocket_compression: false
```

**Client:**
```yaml
mode: "client"
psk: "your_secret_key"
profile: "balanced"
paths:
  - transport: "wsmux"
    addr: "SERVER_IP:8080"
    connection_pool: 16
```

### Secure WebSocket (wssmux)

Best for: Encrypted connections through firewalls

**Generate TLS Certificate:**
```bash
# Self-signed (testing)
openssl genpkey -algorithm RSA -out server.key -pkeyopt rsa_keygen_bits:2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365

# Let's Encrypt (production) - use netrixcore.py
```

**Server:**
```yaml
mode: "server"
listen: "0.0.0.0:8443"
transport: "wssmux"
psk: "your_secret_key"
profile: "balanced"
cert_file: "/root/cert.crt"
key_file: "/root/private.key"
tcp_ports: [2066]
udp_ports: [2066]
```

**Client:**
```yaml
mode: "client"
psk: "your_secret_key"
profile: "balanced"
paths:
  - transport: "wssmux"
    addr: "SERVER_IP:8443"
    connection_pool: 16
```

---

## Advanced Features

### Encryption (Anti-DPI)

Enable ChaCha20-Poly1305 encryption for traffic obfuscation:

```yaml
encryption:
  enabled: true
  key: ""  # Empty = use PSK as key

stealth:
  padding_enabled: true    # Random padding
  padding_min: 0
  padding_max: 32
  jitter_enabled: false    # Timing jitter (adds latency)
  jitter_min_ms: 5
  jitter_max_ms: 20
```

### TUN Mode (Layer 3 VPN)

Enable TUN mode for full VPN functionality:

**Server:**
```yaml
tun:
  enabled: true
  name: "netrix0"
  local: "10.200.0.1/30"
  mtu: 1400
  routes: []
```

**Client:**
```yaml
tun:
  enabled: true
  name: "netrix0"
  local: "10.200.0.2/30"
  mtu: 1400
  routes: ["0.0.0.0/0"]  # Route all traffic
```

### Multi-Path (Failover)

Configure multiple servers for redundancy:

```yaml
paths:
  - transport: "tcpmux"
    addr: "PRIMARY_IP:4000"
    connection_pool: 16
  - transport: "tcpmux"
    addr: "BACKUP_IP:4000"
    connection_pool: 8
  - transport: "kcpmux"
    addr: "BACKUP2_IP:4001"
    connection_pool: 4
```

### IPv6 Support

**Server (listen on all interfaces):**
```yaml
listen: "[::]:4000"  # IPv4 and IPv6
```

**Client (connect to IPv6 server):**
```yaml
paths:
  - addr: "[2001:db8::1]:4000"
```

---

## Buffer Pool Configuration

Fine-tune memory usage for high-performance scenarios:

```yaml
advanced:
  buffer_pool_size: 65536        # 64KB (default)
  large_buffer_pool_size: 65536  # 64KB (default)
  udp_frame_pool_size: 32768     # 32KB (default)
  udp_data_slice_size: 1500      # MTU (default)
```

---

## Troubleshooting

### Common Issues

1. **Connection refused**
   - Check if server is running: `systemctl status netrix-server*`
   - Check firewall: `ufw status` or `iptables -L`
   - Verify port is open: `netstat -tlnp | grep 4000`

2. **High latency**
   - Use `latency` profile
   - Switch to KCP transport
   - Reduce `connection_pool` size

3. **Connection drops**
   - Increase `session_timeout` and `stream_timeout`
   - Enable `aggressive_pool` on client
   - Check network stability

4. **License errors**
   - Verify license server is reachable
   - Check IP registration

### Debug Mode

Enable verbose logging:

```yaml
verbose: true
```

Or via command line:
```bash
netrix -config config.yaml -verbose
```

### Health Check

```bash
# Simple check
curl http://localhost:19080/health

# Detailed stats
curl http://localhost:19080/health/detailed | jq
```

---

## netrixcore.py Management Script

The Python management script provides an interactive menu:

```
╔══════════════════════════════════════════════════════════╗
║                    Netrix Management                      ║
╚══════════════════════════════════════════════════════════╝

  1) Create Tunnel
  2) Status
  3) Stop Tunnel
  4) Restart Tunnel
  5) Delete Tunnel
  6) Core Management
  0) Exit
```

### Features

- Create server/client tunnels interactively
- View tunnel status and logs
- Start/stop/restart tunnels
- Health check monitoring
- Core installation and updates
- Let's Encrypt certificate automation
- Systemd service management

---


---

<div dir="rtl">

## درباره تونل معکوس Netrix

**Netrix** یک راه‌حل پیشرفته و حرفه‌ای برای تونل‌سازی معکوس (Reverse Tunneling) است که برای عبور از NAT، فایروال‌ها و محدودیت‌های شبکه طراحی شده است.

### تونل معکوس چیست؟

تونل معکوس یک تکنیک شبکه است که به شما اجازه می‌دهد از یک شبکه محدود (مثل شبکه خانگی یا شرکتی با NAT و فایروال) به یک سرور خارجی متصل شوید و سپس از آن سرور برای اتصال به خدمات محلی استفاده کنید.

**نحوه کار:**
1. کلاینت (داخل شبکه محدود) به سرور خارجی متصل می‌شود
2. سرور از طریق این اتصال به خدمات محلی کلاینت دسترسی پیدا می‌کند
3. کاربران از طریق سرور به خدمات محلی کلاینت متصل می‌شوند

### ویژگی‌های کلیدی

- ✅ **عبور از NAT** - بدون نیاز به port forwarding
- ✅ **چندین Transport** - TCP، KCP، WebSocket، Secure WebSocket
- ✅ **Stream Multiplexing** - چندین اتصال روی یک تونل (SMUX)
- ✅ **پشتیبانی کامل UDP** - پروتکل Frame برای عبور UDP
- ✅ **رمزنگاری ChaCha20-Poly1305** - ضد DPI با رمزنگاری AEAD
- ✅ **حالت Stealth** - Padding تصادفی و Jitter زمانی
- ✅ **حالت TUN** - VPN لایه 3 برای L2TP/IPsec، WireGuard
- ✅ **پشتیبانی IPv6** - سازگاری کامل با IPv4 و IPv6
- ✅ **Multi-Path** - چندین مسیر سرور با failover خودکار
- ✅ **Health Check API** - endpoint های مانیتورینگ داخلی
- ✅ **پروفایل‌های عملکرد** - پروفایل‌های بهینه‌سازی از پیش تنظیم شده
- ✅ **مدیریت لایسنس** - اعتبارسنجی لایسنس داخلی

### کاربردها

- 🎮 **گیمینگ** - اتصال به سرورهای بازی از پشت NAT
- 🖥️ **دسترسی از راه دور** - دسترسی به سرویس‌های محلی از راه دور
- 📡 **انتشار سرویس** - در دسترس قرار دادن سرویس‌های محلی در اینترنت
- 🔒 **عبور از محدودیت‌ها** - عبور از محدودیت‌های شبکه
- 🌐 **جایگزین VPN** - جایگزین برای VPN سنتی

---

## معماری

Netrix از معماری چند لایه استفاده می‌کند:

### 1. لایه Transport (TCP, KCP, WebSocket, WSS)
- **TCP (tcpmux)** - قابل اعتماد و پایدار
- **KCP (kcpmux)** - سریع، latency کم برای گیمینگ
- **WebSocket (wsmux)** - عبور از فایروال‌های HTTP-aware
- **WSS (wssmux)** - امن با TLS/SSL

### 2. لایه SMUX (Stream Multiplexing)
- چندین stream روی یک transport connection
- کاهش overhead و استفاده بهینه
- امکان اجرای همزمان چندین اتصال
- mux_con قابل تنظیم برای multiplexing تو در تو

### 3. لایه Session Manager
- مدیریت pool از sessions
- Load balancing آگاه از سلامت (least-loaded)
- Tracking دقیق streams
- تشخیص خودکار sessions کند

### 4. Frame Protocol برای UDP
- Encapsulation UDP packets داخل frames
- امکان عبور UDP از طریق tunnel
- مدیریت چندین UDP flow

### 5. لایه رمزنگاری (اختیاری)
- رمزنگاری ChaCha20-Poly1305 AEAD
- شمارنده nonce جداگانه برای هر جهت
- Padding تصادفی (ضد DPI)
- Jitter زمانی (ضد DPI)

### 6. حالت TUN (VPN لایه 3)
- رابط شبکه مجازی
- فوروارد کامل پکت‌های IP
- پیکربندی route
- پشتیبانی از L2TP/IPsec، WireGuard

---

## پروفایل‌های عملکرد

Netrix شامل 4 پروفایل از پیش تنظیم شده است:

| پروفایل | کاربرد | SMUX Keepalive | SMUX Buffer | KCP Interval | KCP Windows | بهترین برای |
|---------|--------|----------------|-------------|--------------|-------------|-------------|
| **balanced** (پیش‌فرض) | استفاده عمومی | 20s | 4MB | 20ms | 512/512 | بیشتر کاربران |
| **aggressive** | سرعت بالا | 30s | 8MB | 10ms | 2048/2048 | حداکثر سرعت |
| **latency** | تاخیر کم | 5s | 2MB | 5ms | 256/256 | گیمینگ، real-time |
| **cpu-efficient** | مصرف CPU کم | 60s | 2MB | 50ms | 128/128 | سرورهای محدود |

### جزئیات پروفایل‌ها

- **balanced**: بهترین عملکرد کلی. تعادل خوب بین latency، throughput و مصرف CPU.
- **aggressive**: حداکثر throughput. CPU و حافظه بیشتری استفاده می‌کند. بهترین برای اپلیکیشن‌های پهن‌باند.
- **latency**: بهینه شده برای latency پایین. بهترین برای گیمینگ، تماس ویدیویی و اپلیکیشن‌های real-time.
- **cpu-efficient**: مصرف CPU را به حداقل می‌رساند. بهترین برای سرورهای محدود.

---

## نصب

### نصب سریع (یک دستور)

```bash
wget https://raw.githubusercontent.com/Karrari-Dev/Netrix-/main/netrix-manager.py -O /usr/local/bin/netrix-manager.py && chmod +x /usr/local/bin/netrix-manager.py && echo 'alias netrix-manager="python3 /usr/local/bin/netrix-manager.py"' >> ~/.bashrc && source ~/.bashrc
```

بعد از نصب، فقط اجرا کنید:
```bash
netrix-manager
```

### نصب دستی

```bash
# دانلود باینری برای معماری شما
# AMD64
wget https://github.com/Karrari-Dev/Netrix-/releases/download/v2.0.0/netrix-amd64.tar.gz
tar -xzf netrix-amd64.tar.gz
mv netrix /usr/local/bin/
```

```bash
# ARM64
wget https://github.com/Karrari-Dev/Netrix-/releases/download/v2.0.0/netrix-arm64.tar.gz
tar -xzf netrix-arm64.tar.gz
mv netrix /usr/local/bin/
```

---

## پیکربندی

### پیکربندی سرور (ایران)

```yaml
mode: "server"
listen: "0.0.0.0:4000"           # برای IPv6: [::]:4000
transport: "tcpmux"              # tcpmux|kcpmux|wsmux|wssmux
psk: "کلید_مخفی_شما"
profile: "balanced"              # balanced|aggressive|latency|cpu-efficient

# مپ کردن پورت‌ها (فرمت ساده)
tcp_ports: [2066, 9988, 6665]    # پورت‌های TCP برای فوروارد
udp_ports: [2066, 9988]          # پورت‌های UDP برای فوروارد

# تنظیمات SMUX
smux:
  keepalive: 20                  # ثانیه (پیش‌فرض: 20)
  max_recv: 4194304              # 4MB (پیش‌فرض)
  max_stream: 2097152            # 2MB (پیش‌فرض)
  frame_size: 32768              # 32KB (پیش‌فرض)
  version: 2                     # نسخه SMUX
  mux_con: 8                     # اتصالات multiplexed

# تنظیمات KCP (فقط برای kcpmux)
kcp:
  nodelay: 0                     # 0=batching، 1=بدون batching
  interval: 20                   # میلی‌ثانیه (فاصله update)
  resend: 2                      # آستانه resend سریع
  nc: 0                          # 0=کنترل ازدحام، 1=بدون CC
  sndwnd: 512                    # پنجره ارسال
  rcvwnd: 512                    # پنجره دریافت
  mtu: 1350                      # MTU

# تنظیمات پیشرفته
advanced:
  tcp_nodelay: true
  tcp_keepalive: 30              # ثانیه
  tcp_read_buffer: 8388608       # 8MB
  tcp_write_buffer: 8388608      # 8MB
  cleanup_interval: 60           # ثانیه
  session_timeout: 120           # ثانیه
  connection_timeout: 600        # ثانیه
  stream_timeout: 21600          # 6 ساعت
  stream_idle_timeout: 600       # 10 دقیقه
  max_connections: 0             # 0 = نامحدود (محدودیت 1M)
  max_udp_flows: 5000
  udp_flow_timeout: 600          # ثانیه

# رمزنگاری (ChaCha20-Poly1305)
encryption:
  enabled: false                 # فعال‌سازی رمزنگاری
  key: ""                        # خالی = استفاده از PSK

# Stealth (ضد DPI)
stealth:
  padding_enabled: false
  padding_min: 0
  padding_max: 128
  jitter_enabled: false
  jitter_min_ms: 5
  jitter_max_ms: 20

# حالت TUN (VPN لایه 3)
tun:
  enabled: false
  name: "netrix0"
  local: "10.200.0.1/30"
  mtu: 1400
  routes: []

# Health check
health_port: 19080               # پیش‌فرض: 19080
heartbeat: 20                    # ثانیه (پیش‌فرض: 20)
verbose: false
```

### پیکربندی کلاینت (خارج)

```yaml
mode: "client"
psk: "کلید_مخفی_شما"
profile: "balanced"

# پشتیبانی Multi-path (چندین سرور)
paths:
  - transport: "tcpmux"
    addr: "SERVER_IP:4000"       # IPv6: [2001:db8::1]:4000
    connection_pool: 24          # توصیه: 8-24
    aggressive_pool: false
    retry_interval: 3            # ثانیه
    dial_timeout: 10             # ثانیه
  # سرور پشتیبان (اختیاری)
  - transport: "tcpmux"
    addr: "BACKUP_IP:4000"
    connection_pool: 8
    retry_interval: 5
    dial_timeout: 10

# تنظیمات SMUX
smux:
  keepalive: 20
  max_recv: 4194304
  max_stream: 2097152
  frame_size: 32768
  version: 2
  mux_con: 10                    # توصیه: 8-16

# تنظیمات KCP (اگر از kcpmux استفاده می‌کنید)
kcp:
  nodelay: 0
  interval: 20
  resend: 2
  nc: 0
  sndwnd: 512
  rcvwnd: 512
  mtu: 1350

# تنظیمات پیشرفته
advanced:
  tcp_nodelay: true
  tcp_keepalive: 30
  tcp_read_buffer: 8388608
  tcp_write_buffer: 8388608
  cleanup_interval: 60
  session_timeout: 120
  connection_timeout: 600
  stream_timeout: 21600
  stream_idle_timeout: 600
  max_connections: 0
  max_udp_flows: 5000
  udp_flow_timeout: 600

# رمزنگاری (باید با سرور مطابقت داشته باشد)
encryption:
  enabled: false
  key: ""

# Stealth (باید با سرور مطابقت داشته باشد)
stealth:
  padding_enabled: false
  padding_min: 0
  padding_max: 128
  jitter_enabled: false
  jitter_min_ms: 5
  jitter_max_ms: 20

# حالت TUN (باید با سرور مطابقت داشته باشد)
tun:
  enabled: false
  name: "netrix0"
  local: "10.200.0.2/30"         # متفاوت از سرور!
  mtu: 1400
  routes: ["0.0.0.0/0"]          # Route کردن همه ترافیک

heartbeat: 20
verbose: false
```

---

## اجرای Netrix

### استفاده از فایل کانفیگ

```bash
# سرور
netrix -config /root/server4000.yaml

# کلاینت
netrix -config /root/client_SERVER_IP_4000.yaml
```

### استفاده از Systemd (توصیه شده)

اسکریپت `netrixcore.py` به صورت خودکار سرویس‌های systemd ایجاد می‌کند:

```bash
# بررسی وضعیت
systemctl status netrix-server4000

# شروع/توقف/ریستارت
systemctl start netrix-server4000
systemctl stop netrix-server4000
systemctl restart netrix-server4000

# مشاهده لاگ‌ها
journalctl -u netrix-server4000 -f
```

---

## Health Check API

Netrix endpoint های health check داخلی روی پورت 19080 ارائه می‌دهد:

### Endpoint ها

| Endpoint | توضیحات |
|----------|---------|
| `/health` | بررسی ساده liveness |
| `/health/ready` | بررسی readiness (sessions فعال) |
| `/health/detailed` | آمار دقیق (JSON) |

### نمونه پاسخ (/health/detailed)

```json
{
  "status": "healthy",
  "sessions": 4,
  "streams": 128,
  "rtt_ms": 45,
  "tcp_in": {"bytes": 1073741824, "formatted": "1.00 GB"},
  "tcp_out": {"bytes": 536870912, "formatted": "512.00 MB"},
  "udp_in": {"bytes": 104857600, "formatted": "100.00 MB"},
  "udp_out": {"bytes": 52428800, "formatted": "50.00 MB"},
  "total_traffic": {"bytes": 1768000000, "formatted": "1.65 GB"}
}
```

---

## ویژگی‌های پیشرفته

### رمزنگاری (ضد DPI)

فعال‌سازی رمزنگاری ChaCha20-Poly1305 برای مبهم‌سازی ترافیک:

```yaml
encryption:
  enabled: true
  key: ""  # خالی = استفاده از PSK به عنوان کلید

stealth:
  padding_enabled: true    # Padding تصادفی
  padding_min: 0
  padding_max: 32
  jitter_enabled: false    # Jitter زمانی (latency اضافه می‌کند)
  jitter_min_ms: 5
  jitter_max_ms: 20
```

### حالت TUN (VPN لایه 3)

فعال‌سازی حالت TUN برای عملکرد کامل VPN:

**سرور:**
```yaml
tun:
  enabled: true
  name: "netrix0"
  local: "10.200.0.1/30"
  mtu: 1400
  routes: []
```

**کلاینت:**
```yaml
tun:
  enabled: true
  name: "netrix0"
  local: "10.200.0.2/30"
  mtu: 1400
  routes: ["0.0.0.0/0"]  # Route کردن همه ترافیک
```

### Multi-Path (Failover)

پیکربندی چندین سرور برای redundancy:

```yaml
paths:
  - transport: "tcpmux"
    addr: "PRIMARY_IP:4000"
    connection_pool: 16
  - transport: "tcpmux"
    addr: "BACKUP_IP:4000"
    connection_pool: 8
  - transport: "kcpmux"
    addr: "BACKUP2_IP:4001"
    connection_pool: 4
```

### پشتیبانی IPv6

**سرور (گوش دادن روی همه رابط‌ها):**
```yaml
listen: "[::]:4000"  # IPv4 و IPv6
```

**کلاینت (اتصال به سرور IPv6):**
```yaml
paths:
  - addr: "[2001:db8::1]:4000"
```

---

## عیب‌یابی

### مشکلات رایج

1. **Connection refused**
   - بررسی اجرای سرور: `systemctl status netrix-server*`
   - بررسی فایروال: `ufw status` یا `iptables -L`
   - تأیید باز بودن پورت: `netstat -tlnp | grep 4000`

2. **Latency بالا**
   - استفاده از پروفایل `latency`
   - تغییر به transport KCP
   - کاهش اندازه `connection_pool`

3. **قطع اتصال**
   - افزایش `session_timeout` و `stream_timeout`
   - فعال‌سازی `aggressive_pool` روی کلاینت
   - بررسی پایداری شبکه

4. **خطاهای لایسنس**
   - تأیید دسترسی به سرور لایسنس
   - بررسی ثبت IP

### حالت Debug

فعال‌سازی verbose logging:

```yaml
verbose: true
```

یا از طریق خط فرمان:
```bash
netrix -config config.yaml -verbose
```

### Health Check

```bash
# بررسی ساده
curl http://localhost:19080/health

# آمار دقیق
curl http://localhost:19080/health/detailed | jq
```

---

## اسکریپت مدیریت netrixcore.py

اسکریپت مدیریت Python یک منوی تعاملی ارائه می‌دهد:

```
╔══════════════════════════════════════════════════════════╗
║                    Netrix Management                      ║
╚══════════════════════════════════════════════════════════╝

  1) Create Tunnel
  2) Status
  3) Stop Tunnel
  4) Restart Tunnel
  5) Delete Tunnel
  6) Core Management
  0) Exit
```

### ویژگی‌ها

- ایجاد تونل‌های سرور/کلاینت به صورت تعاملی
- مشاهده وضعیت و لاگ تونل‌ها
- شروع/توقف/ریستارت تونل‌ها
- مانیتورینگ health check
- نصب و به‌روزرسانی هسته
- اتوماسیون گواهینامه Let's Encrypt
- مدیریت سرویس systemd

</div>

---

## License

This project is commercial software. Please contact the author for licensing information.

---

Made with ❤️ by Netrix Team

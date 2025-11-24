# Netrix - Advanced Reverse Tunneling Solution

[![Go Version](https://img.shields.io/badge/Go-1.20+-00ADD8?style=flat&logo=go)](https://golang.org/)
[![License](https://img.shields.io/badge/License-Commercial-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-Stable-green.svg)](https://github.com/yourusername/netrix/releases)

---

## 🌐 Language | زبان

**English** | [فارسی (Persian)](#about-netrix-reverse-tunneling-فارسی)

<div dir="rtl">

**فارسی** | [English (انگلیسی)](#about-netrix-reverse-tunneling)

</div>

---

<a id="about-netrix-reverse-tunneling"></a>

## About Netrix Reverse Tunneling

**Netrix** is an advanced and professional reverse tunneling solution designed for NAT traversal, firewall bypass, and network restrictions.

### What is Reverse Tunneling?

Reverse tunneling is a network technique that allows you to connect from a restricted network (like home or corporate network with NAT and firewall) to an external server, then use that server to access local services.

**How it works:**
1. Client (inside restricted network) connects to external server
2. Server accesses local services through this connection
3. Users connect to local services through the server

**Benefits:**
- ✅ NAT traversal without port forwarding
- ✅ Firewall bypass through TCP/WebSocket
- ✅ Security with PSK authentication and TLS encryption
- ✅ High performance for massive connections
- ✅ Multiplexing: multiple connections over one tunnel
- ✅ Full UDP support with frame protocol

**Use Cases:**
- 🎮 Gaming: Connect to game servers behind NAT
- 🖥️ Remote Access: Remote access to local services
- 📡 Service Exposure: Expose local services to internet
- 🔒 Bypass Restrictions: Bypass network restrictions
- 🌐 VPN Alternative: Alternative to traditional VPN

### Netrix Architecture

Netrix uses a multi-layer architecture:

**1. Transport Layer (TCP, KCP, WebSocket, WSS)**
- Base connection between client and server
- TCP: Reliable and stable
- KCP: Fast and low latency for gaming
- WebSocket: Bypass HTTP-aware firewalls
- WSS: Secure with TLS/SSL

**2. SMUX Layer (Stream Multiplexing)**
- Multiple streams over one transport connection
- Reduced overhead and optimal usage
- Concurrent connection capability

**3. Session Manager Layer**
- Session pool management
- Intelligent load balancing (least-loaded)
- Precise stream tracking

**4. Frame Protocol for UDP**
- Encapsulate UDP packets in frames
- UDP traversal through tunnel
- Multiple UDP flow management

---

## Server Configuration

### Server Flags

```bash
netrix server [OPTIONS]
```

**Basic Options:**
- `-listen string` - Listen address (default: `:4000`)
- `-transport string` - Transport: `tcpmux|kcpmux|wsmux|wssmux` (default: `tcpmux`)
- `-map string` - Port mappings: `"tcp::bind->target,udp::bind->target"`
- `-psk string` - Pre-shared key (required)
- `-profile string` - Profile: `balanced|aggressive|latency|cpu-efficient` (default: `balanced`)
- `-verbose` - Enable verbose logging
- `-cert string` - TLS certificate file path (for wssmux)
- `-key string` - TLS private key file path (for wssmux)

**SMUX Options:**
- `-smux-keepalive int` - SMUX keepalive interval (seconds, overrides profile)
- `-smux-max-recv int` - SMUX max receive buffer (bytes, overrides profile)
- `-smux-max-stream int` - SMUX max stream buffer (bytes, overrides profile)
- `-smux-frame-size int` - SMUX frame size (bytes, default: 32768, overrides profile)

**KCP Options:**
- `-kcp-nodelay int` - Enable KCP nodelay (0=disable, 1=enable, overrides profile)
- `-kcp-interval int` - KCP update interval (milliseconds, overrides profile)
- `-kcp-resend int` - KCP fast resend threshold (overrides profile)
- `-kcp-nc int` - Disable KCP congestion control (0=disable, 1=enable, overrides profile)
- `-kcp-sndwnd int` - KCP send window size (overrides profile)
- `-kcp-rcvwnd int` - KCP receive window size (overrides profile)
- `-kcp-mtu int` - KCP Maximum Transmission Unit (overrides profile)

---

## Client Configuration

### Client Flags

```bash
netrix client [OPTIONS]
```

**Basic Options:**
- `-server string` - Server address `host:port` (legacy single-path mode)
- `-transport string` - Transport: `tcpmux|kcpmux|wsmux|wssmux` (default: `tcpmux`)
- `-parallel int` - Number of parallel tunnels (legacy, default: 1)
- `-paths string` - Multi-path: `"tcpmux:addr:parallel,kcpmux:addr:parallel,..."`
- `-psk string` - Pre-shared key (must match server)
- `-profile string` - Profile: `balanced|aggressive|latency|cpu-efficient` (default: `balanced`)
- `-verbose` - Enable verbose logging

**Connection Pool Options:**
- `-connection-pool int` - Number of simultaneous tunnels (alias of parallel, default: 0)
- `-aggressive-pool` - Aggressively re-dial tunnels to minimize downtime
- `-retry-interval duration` - Retry interval for dial errors (default: 3s)
- `-dial-timeout duration` - Dial timeout for tunnel transports (default: 10s)

**SMUX Options:** (same as server)
- `-smux-keepalive int`
- `-smux-max-recv int`
- `-smux-max-stream int`
- `-smux-frame-size int`

**KCP Options:** (same as server)
- `-kcp-nodelay int`
- `-kcp-interval int`
- `-kcp-resend int`
- `-kcp-nc int`
- `-kcp-sndwnd int`
- `-kcp-rcvwnd int`
- `-kcp-mtu int`

---

## Complete Examples for Each Transport

### TCP Multiplexing (tcpmux)

**Server file: server-tcp.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:4000"
transport: "tcpmux"
psk: "your_secret_key_here"
profile: "balanced"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**Run server:**

```bash
netrix -config server-tcp.yaml
```

**Client file: client-tcp.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

paths:
  - transport: "tcpmux"
    addr: "SERVER_IP:4000"
    connection_pool: 4
    aggressive_pool: false
    retry_interval: 3
    dial_timeout: 10

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**Run client:**

```bash
netrix -config client-tcp.yaml
```

---

### KCP Multiplexing (kcpmux)

**Server file: server-kcp.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:4001"
transport: "kcpmux"
psk: "your_secret_key_here"
profile: "latency"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 3
  max_recv: 4194304
  max_stream: 4194304
  frame_size: 32768

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 768
  rcvwnd: 768
  mtu: 1350

advanced:
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**Run server:**

```bash
netrix -config server-kcp.yaml
```

**Client file: client-kcp.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "latency"

paths:
  - transport: "kcpmux"
    addr: "SERVER_IP:4001"
    connection_pool: 4
    aggressive_pool: true
    retry_interval: 1
    dial_timeout: 5

smux:
  keepalive: 3
  max_recv: 4194304
  max_stream: 4194304
  frame_size: 32768

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 512
  rcvwnd: 512
  mtu: 1350

advanced:
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**Run client:**

```bash
netrix -config client-kcp.yaml
```

---

### WebSocket Multiplexing (wsmux)

**Server file: server-ws.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:8080"
transport: "wsmux"
psk: "your_secret_key_here"
profile: "balanced"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**Run server:**

```bash
netrix -config server-ws.yaml
```

**Client file: client-ws.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

paths:
  - transport: "wsmux"
    addr: "SERVER_IP:8080"
    connection_pool: 8
    aggressive_pool: false
    retry_interval: 3
    dial_timeout: 10

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**Run client:**

```bash
netrix -config client-ws.yaml
```

---

### Secure WebSocket Multiplexing (wssmux)

**Generate TLS Certificate:**

```bash
openssl genpkey -algorithm RSA -out server.key -pkeyopt rsa_keygen_bits:2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365
```

**Server file: server-wss.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:8443"
transport: "wssmux"
psk: "your_secret_key_here"
profile: "balanced"

cert_file: "/path/to/server.crt"
key_file: "/path/to/server.key"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**Run server:**

```bash
netrix -config server-wss.yaml
```

**Client file: client-wss.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

paths:
  - transport: "wssmux"
    addr: "SERVER_IP:8443"
    connection_pool: 8
    aggressive_pool: false
    retry_interval: 3
    dial_timeout: 10

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**Run client:**

```bash
netrix -config client-wss.yaml
```

---

<div dir="rtl">

<a id="about-netrix-reverse-tunneling-فارسی"></a>

## درباره تونل معکوس Netrix

**Netrix** یک راه‌حل پیشرفته و حرفه‌ای برای تونل‌سازی معکوس (Reverse Tunneling) است که برای عبور از NAT، فایروال‌ها و محدودیت‌های شبکه طراحی شده است.

### تونل معکوس چیست؟

تونل معکوس یک تکنیک شبکه است که به شما اجازه می‌دهد از یک شبکه محدود (مثل شبکه خانگی یا شرکتی با NAT و فایروال) به یک سرور خارجی متصل شوید و سپس از آن سرور برای اتصال به خدمات محلی استفاده کنید.

**نحوه کار:**
1. کلاینت (داخل شبکه محدود) به سرور خارجی متصل می‌شود
2. سرور از طریق این اتصال به خدمات محلی کلاینت دسترسی پیدا می‌کند
3. کاربران از طریق سرور به خدمات محلی کلاینت متصل می‌شوند

**مزایا:**
- ✅ عبور از NAT بدون نیاز به port forwarding
- ✅ عبور از فایروال‌ها از طریق TCP/WebSocket
- ✅ امنیت با PSK authentication و TLS encryption
- ✅ Performance بالا برای اتصالات زیاد
- ✅ Multiplexing: چندین connection روی یک tunnel
- ✅ پشتیبانی کامل UDP با frame protocol

**کاربردها:**
- 🎮 Gaming: اتصال به game servers از پشت NAT
- 🖥️ Remote Access: دسترسی از راه دور به services محلی
- 📡 Service Exposure: در دسترس قرار دادن services محلی در اینترنت
- 🔒 Bypass Restrictions: عبور از محدودیت‌های شبکه
- 🌐 VPN Alternative: جایگزین برای VPN سنتی

### معماری Netrix

Netrix از معماری چند لایه استفاده می‌کند:

**1. لایه Transport (TCP, KCP, WebSocket, WSS)**
- اتصال پایه بین کلاینت و سرور
- TCP: قابل اعتماد و پایدار
- KCP: سریع و کم latency برای gaming
- WebSocket: عبور از فایروال‌های HTTP-aware
- WSS: امن با TLS/SSL

**2. لایه SMUX (Stream Multiplexing)**
- چندین stream روی یک transport connection
- کاهش overhead و استفاده بهینه
- امکان اجرای همزمان چندین اتصال

**3. لایه Session Manager**
- مدیریت pool از sessions
- Load balancing هوشمند (least-loaded)
- Tracking دقیق streams

**4. Frame Protocol برای UDP**
- Encapsulation UDP packets داخل frames
- امکان عبور UDP از طریق tunnel
- مدیریت چندین UDP flow

</div>

---

<div dir="rtl">

## تنظیمات سرور (Server Configuration)

### Flags سمت سرور

```bash
netrix server [OPTIONS]
```

**تنظیمات پایه:**
- `-listen string` - آدرس گوش دادن (پیش‌فرض: `:4000`)
- `-transport string` - نوع transport: `tcpmux|kcpmux|wsmux|wssmux` (پیش‌فرض: `tcpmux`)
- `-map string` - مپ کردن پورت‌ها: `"tcp::bind->target,udp::bind->target"`
- `-psk string` - Pre-shared key (الزامی)
- `-profile string` - پروفایل: `balanced|aggressive|latency|cpu-efficient` (پیش‌فرض: `balanced`)
- `-verbose` - فعال‌سازی logging دقیق
- `-cert string` - مسیر فایل گواهینامه TLS (برای wssmux)
- `-key string` - مسیر فایل private key TLS (برای wssmux)

**تنظیمات SMUX:**
- `-smux-keepalive int` - فاصله زمانی keepalive برای SMUX (ثانیه، بازنویسی می‌کند profile)
- `-smux-max-recv int` - حداکثر buffer دریافت برای SMUX (بایت، بازنویسی می‌کند profile)
- `-smux-max-stream int` - حداکثر buffer stream برای SMUX (بایت، بازنویسی می‌کند profile)
- `-smux-frame-size int` - اندازه frame برای SMUX (بایت، پیش‌فرض: 32768، بازنویسی می‌کند profile)

**تنظیمات KCP:**
- `-kcp-nodelay int` - فعال‌سازی nodelay برای KCP (0=غیرفعال, 1=فعال، بازنویسی می‌کند profile)
- `-kcp-interval int` - فاصله زمانی update برای KCP (میلی‌ثانیه، بازنویسی می‌کند profile)
- `-kcp-resend int` - آستانه resend سریع برای KCP (بازنویسی می‌کند profile)
- `-kcp-nc int` - غیرفعال‌سازی congestion control برای KCP (0=غیرفعال, 1=فعال، بازنویسی می‌کند profile)
- `-kcp-sndwnd int` - اندازه پنجره ارسال برای KCP (بازنویسی می‌کند profile)
- `-kcp-rcvwnd int` - اندازه پنجره دریافت برای KCP (بازنویسی می‌کند profile)
- `-kcp-mtu int` - Maximum Transmission Unit برای KCP (بازنویسی می‌کند profile)

</div>

---

<div dir="rtl">

## تنظیمات کلاینت (Client Configuration)

### Flags سمت کلاینت

```bash
netrix client [OPTIONS]
```

**تنظیمات پایه:**
- `-server string` - آدرس سرور `host:port` (حالت legacy single-path)
- `-transport string` - نوع transport: `tcpmux|kcpmux|wsmux|wssmux` (پیش‌فرض: `tcpmux`)
- `-parallel int` - تعداد تونل‌های موازی (legacy، پیش‌فرض: 1)
- `-paths string` - حالت multi-path: `"tcpmux:addr:parallel,kcpmux:addr:parallel,..."`
- `-psk string` - Pre-shared key (باید با سرور مطابقت داشته باشد)
- `-profile string` - پروفایل: `balanced|aggressive|latency|cpu-efficient` (پیش‌فرض: `balanced`)
- `-verbose` - فعال‌سازی logging دقیق

**تنظیمات Connection Pool:**
- `-connection-pool int` - تعداد تونل‌های همزمان (alias برای parallel، پیش‌فرض: 0)
- `-aggressive-pool` - به صورت تهاجمی تونل‌ها را دوباره dial می‌کند
- `-retry-interval duration` - فاصله زمانی retry برای خطاهای dial (پیش‌فرض: 3s)
- `-dial-timeout duration` - Timeout برای dial کردن transport (پیش‌فرض: 10s)

**تنظیمات SMUX:** (مشابه سرور)
- `-smux-keepalive int`
- `-smux-max-recv int`
- `-smux-max-stream int`
- `-smux-frame-size int`

**تنظیمات KCP:** (مشابه سرور)
- `-kcp-nodelay int`
- `-kcp-interval int`
- `-kcp-resend int`
- `-kcp-nc int`
- `-kcp-sndwnd int`
- `-kcp-rcvwnd int`
- `-kcp-mtu int`

</div>

---

<div dir="rtl">

## مثال‌های کامل برای هر Transport

### TCP Multiplexing (tcpmux)

**فایل سرور: server-tcp.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:4000"
transport: "tcpmux"
psk: "your_secret_key_here"
profile: "balanced"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**اجرای سرور:**

```bash
netrix -config server-tcp.yaml
```

**فایل کلاینت: client-tcp.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

paths:
  - transport: "tcpmux"
    addr: "SERVER_IP:4000"
    connection_pool: 4
    aggressive_pool: false
    retry_interval: 3
    dial_timeout: 10

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**اجرای کلاینت:**

```bash
netrix -config client-tcp.yaml
```

---

### KCP Multiplexing (kcpmux)

**فایل سرور: server-kcp.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:4001"
transport: "kcpmux"
psk: "your_secret_key_here"
profile: "latency"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 3
  max_recv: 4194304
  max_stream: 4194304
  frame_size: 32768

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 768
  rcvwnd: 768
  mtu: 1350

advanced:
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**اجرای سرور:**

```bash
netrix -config server-kcp.yaml
```

**فایل کلاینت: client-kcp.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "latency"

paths:
  - transport: "kcpmux"
    addr: "SERVER_IP:4001"
    connection_pool: 4
    aggressive_pool: true
    retry_interval: 1
    dial_timeout: 5

smux:
  keepalive: 3
  max_recv: 4194304
  max_stream: 4194304
  frame_size: 32768

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 512
  rcvwnd: 512
  mtu: 1350

advanced:
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**اجرای کلاینت:**

```bash
netrix -config client-kcp.yaml
```

---

### WebSocket Multiplexing (wsmux)

**فایل سرور: server-ws.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:8080"
transport: "wsmux"
psk: "your_secret_key_here"
profile: "balanced"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**اجرای سرور:**

```bash
netrix -config server-ws.yaml
```

**فایل کلاینت: client-ws.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

paths:
  - transport: "wsmux"
    addr: "SERVER_IP:8080"
    connection_pool: 8
    aggressive_pool: false
    retry_interval: 3
    dial_timeout: 10

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**اجرای کلاینت:**

```bash
netrix -config client-ws.yaml
```

---

### Secure WebSocket Multiplexing (wssmux)

**تولید گواهینامه TLS:**

```bash
openssl genpkey -algorithm RSA -out server.key -pkeyopt rsa_keygen_bits:2048
openssl req -new -key server.key -out server.csr
openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365
```

**فایل سرور: server-wss.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:8443"
transport: "wssmux"
psk: "your_secret_key_here"
profile: "balanced"

cert_file: "/path/to/server.crt"
key_file: "/path/to/server.key"

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

max_sessions: 0
heartbeat: 10
verbose: false
```

**اجرای سرور:**

```bash
netrix -config server-wss.yaml
```

**فایل کلاینت: client-wss.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"

paths:
  - transport: "wssmux"
    addr: "SERVER_IP:8443"
    connection_pool: 8
    aggressive_pool: false
    retry_interval: 3
    dial_timeout: 10

smux:
  keepalive: 8
  max_recv: 8388608
  max_stream: 8388608
  frame_size: 32768

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false
  tcp_nodelay: true
  tcp_keepalive: 15
  tcp_read_buffer: 4194304
  tcp_write_buffer: 4194304
  udp_read_buffer: 4194304
  udp_write_buffer: 4194304
  cleanup_interval: 3
  session_timeout: 30
  connection_timeout: 60
  stream_timeout: 120
  max_connections: 2000
  max_udp_flows: 1000
  udp_flow_timeout: 300

heartbeat: 10
verbose: false
```

**اجرای کلاینت:**

```bash
netrix -config client-wss.yaml
```

</div>

---

## License

This project is commercial software. Please contact the author for licensing information.

---

Made with ❤️ by Netrix Team

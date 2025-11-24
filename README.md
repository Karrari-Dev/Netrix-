# Netrix - راه‌حل پیشرفته تونل معکوس

<div dir="rtl">

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

#### تنظیمات پایه:

**-listen string**
- آدرس و پورت برای گوش دادن به اتصالات تونل
- پیش‌فرض: `:4000`
- مثال: `0.0.0.0:4000` یا `:4000`

**-transport string**
- نوع transport: `tcpmux`, `kcpmux`, `wsmux`, `wssmux`
- پیش‌فرض: `tcpmux`
- همچنین پشتیبانی می‌شود: `tcp`, `kcp`, `ws`, `wss` (برای سازگاری)

**-map string**
- مپ کردن پورت‌ها: `"tcp::bind->target,udp::bind->target"`
- مثال: `"tcp::0.0.0.0:2066->127.0.0.1:22,udp::0.0.0.0:2066->127.0.0.1:2066"`

**-psk string**
- Pre-shared key برای احراز هویت (اختیاری، اگر خالی باشد authentication غیرفعال است)

**-profile string**
- پروفایل عملکرد: `balanced`, `aggressive`, `latency`, `cpu-efficient`
- پیش‌فرض: `balanced`

**-verbose**
- فعال‌سازی logging دقیق برای debugging

**-cert string**
- مسیر فایل گواهینامه TLS (برای wssmux)

**-key string**
- مسیر فایل private key TLS (برای wssmux)

#### تنظیمات SMUX:

**-smux-keepalive int**
- فاصله زمانی keepalive برای SMUX (ثانیه)
- بازنویسی می‌کند profile

**-smux-max-recv int**
- حداکثر buffer دریافت برای SMUX (بایت)
- بازنویسی می‌کند profile

**-smux-max-stream int**
- حداکثر buffer stream برای SMUX (بایت)
- بازنویسی می‌کند profile

**-smux-frame-size int**
- اندازه frame برای SMUX (بایت)
- پیش‌فرض: `32768` (32KB)
- بازنویسی می‌کند profile

#### تنظیمات KCP:

**-kcp-nodelay int**
- فعال‌سازی nodelay برای KCP
- `0` = غیرفعال, `1` = فعال
- بازنویسی می‌کند profile

**-kcp-interval int**
- فاصله زمانی update برای KCP (میلی‌ثانیه)
- بازنویسی می‌کند profile

**-kcp-resend int**
- آستانه resend سریع برای KCP
- بازنویسی می‌کند profile

**-kcp-nc int**
- غیرفعال‌سازی congestion control برای KCP
- `0` = غیرفعال, `1` = فعال
- بازنویسی می‌کند profile

**-kcp-sndwnd int**
- اندازه پنجره ارسال برای KCP
- بازنویسی می‌کند profile

**-kcp-rcvwnd int**
- اندازه پنجره دریافت برای KCP
- بازنویسی می‌کند profile

**-kcp-mtu int**
- Maximum Transmission Unit برای KCP
- بازنویسی می‌کند profile

</div>

---

<div dir="rtl">

## تنظیمات کلاینت (Client Configuration)

### Flags سمت کلاینت

```bash
netrix client [OPTIONS]
```

#### تنظیمات پایه:

**-server string**
- آدرس سرور به صورت `host:port` (حالت legacy single-path)

**-transport string**
- نوع transport: `tcpmux`, `kcpmux`, `wsmux`, `wssmux`
- پیش‌فرض: `tcpmux`
- همچنین پشتیبانی می‌شود: `tcp`, `kcp`, `ws`, `wss` (برای سازگاری)

**-parallel int**
- تعداد تونل‌های موازی (legacy mode)
- پیش‌فرض: `1`

**-paths string**
- حالت multi-path: `"tcpmux:addr:parallel,kcpmux:addr:parallel,..."`
- مثال: `"tcpmux:SERVER_IP:4000:2,kcpmux:SERVER_IP:4001:2"`

**-psk string**
- Pre-shared key (باید با سرور مطابقت داشته باشد)

**-profile string**
- پروفایل عملکرد: `balanced`, `aggressive`, `latency`, `cpu-efficient`
- پیش‌فرض: `balanced`

**-verbose**
- فعال‌سازی logging دقیق برای debugging

#### تنظیمات Connection Pool:

**-connection-pool int**
- تعداد تونل‌های همزمان (alias برای parallel)
- پیش‌فرض: `0` (استفاده از parallel)

**-aggressive-pool**
- به صورت تهاجمی تونل‌ها را دوباره dial می‌کند برای کاهش downtime

**-retry-interval duration**
- فاصله زمانی retry برای خطاهای dial (مثال: `3s`)
- پیش‌فرض: `3s`

**-dial-timeout duration**
- Timeout برای dial کردن transport تونل (مثال: `10s`)
- پیش‌فرض: `10s`

#### تنظیمات SMUX:

**-smux-keepalive int**
- فاصله زمانی keepalive برای SMUX (ثانیه)
- بازنویسی می‌کند profile

**-smux-max-recv int**
- حداکثر buffer دریافت برای SMUX (بایت)
- بازنویسی می‌کند profile

**-smux-max-stream int**
- حداکثر buffer stream برای SMUX (بایت)
- بازنویسی می‌کند profile

**-smux-frame-size int**
- اندازه frame برای SMUX (بایت)
- پیش‌فرض: `32768` (32KB)
- بازنویسی می‌کند profile

#### تنظیمات KCP:

**-kcp-nodelay int**
- فعال‌سازی nodelay برای KCP
- `0` = غیرفعال, `1` = فعال
- بازنویسی می‌کند profile

**-kcp-interval int**
- فاصله زمانی update برای KCP (میلی‌ثانیه)
- بازنویسی می‌کند profile

**-kcp-resend int**
- آستانه resend سریع برای KCP
- بازنویسی می‌کند profile

**-kcp-nc int**
- غیرفعال‌سازی congestion control برای KCP
- `0` = غیرفعال, `1` = فعال
- بازنویسی می‌کند profile

**-kcp-sndwnd int**
- اندازه پنجره ارسال برای KCP
- بازنویسی می‌کند profile

**-kcp-rcvwnd int**
- اندازه پنجره دریافت برای KCP
- بازنویسی می‌کند profile

**-kcp-mtu int**
- Maximum Transmission Unit برای KCP
- بازنویسی می‌کند profile

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

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 768
  rcvwnd: 768
  mtu: 1350

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

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 512
  rcvwnd: 512
  mtu: 1350

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

heartbeat: 10
verbose: false
```

**اجرای کلاینت:**

```bash
netrix -config client-wss.yaml
```

</div>

---

## Netrix - Advanced Reverse Tunneling Solution

**Netrix** is an advanced and professional reverse tunneling solution designed for NAT traversal, firewall bypass, and network restrictions.

### About Reverse Tunneling

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

#### Basic Options:

**-listen string**
- Address and port to listen for tunnel connections
- Default: `:4000`
- Example: `0.0.0.0:4000` or `:4000`

**-transport string**
- Transport type: `tcpmux`, `kcpmux`, `wsmux`, `wssmux`
- Default: `tcpmux`
- Also supported: `tcp`, `kcp`, `ws`, `wss` (for compatibility)

**-map string**
- Port mappings: `"tcp::bind->target,udp::bind->target"`
- Example: `"tcp::0.0.0.0:2066->127.0.0.1:22,udp::0.0.0.0:2066->127.0.0.1:2066"`

**-psk string**
- Pre-shared key for authentication (optional, empty disables auth)

**-profile string**
- Performance profile: `balanced`, `aggressive`, `latency`, `cpu-efficient`
- Default: `balanced`

**-verbose**
- Enable verbose logging for debugging

**-cert string**
- TLS certificate file path (for wssmux)

**-key string**
- TLS private key file path (for wssmux)

#### SMUX Options:

**-smux-keepalive int**
- SMUX keepalive interval (seconds)
- Overrides profile

**-smux-max-recv int**
- SMUX max receive buffer (bytes)
- Overrides profile

**-smux-max-stream int**
- SMUX max stream buffer (bytes)
- Overrides profile

**-smux-frame-size int**
- SMUX frame size (bytes)
- Default: `32768` (32KB)
- Overrides profile

#### KCP Options:

**-kcp-nodelay int**
- Enable KCP nodelay
- `0` = disable, `1` = enable
- Overrides profile

**-kcp-interval int**
- KCP update interval (milliseconds)
- Overrides profile

**-kcp-resend int**
- KCP fast resend threshold
- Overrides profile

**-kcp-nc int**
- Disable KCP congestion control
- `0` = disable, `1` = enable
- Overrides profile

**-kcp-sndwnd int**
- KCP send window size
- Overrides profile

**-kcp-rcvwnd int**
- KCP receive window size
- Overrides profile

**-kcp-mtu int**
- KCP Maximum Transmission Unit
- Overrides profile

---

## Client Configuration

### Client Flags

```bash
netrix client [OPTIONS]
```

#### Basic Options:

**-server string**
- Server address as `host:port` (legacy single-path mode)

**-transport string**
- Transport type: `tcpmux`, `kcpmux`, `wsmux`, `wssmux`
- Default: `tcpmux`
- Also supported: `tcp`, `kcp`, `ws`, `wss` (for compatibility)

**-parallel int**
- Number of parallel tunnels (legacy mode)
- Default: `1`

**-paths string**
- Multi-path mode: `"tcpmux:addr:parallel,kcpmux:addr:parallel,..."`
- Example: `"tcpmux:SERVER_IP:4000:2,kcpmux:SERVER_IP:4001:2"`

**-psk string**
- Pre-shared key (must match server)

**-profile string**
- Performance profile: `balanced`, `aggressive`, `latency`, `cpu-efficient`
- Default: `balanced`

**-verbose**
- Enable verbose logging for debugging

#### Connection Pool Options:

**-connection-pool int**
- Number of simultaneous tunnels (alias for parallel)
- Default: `0` (uses parallel)

**-aggressive-pool**
- Aggressively re-dial tunnels to minimize downtime

**-retry-interval duration**
- Retry interval for dial errors (e.g., `3s`)
- Default: `3s`

**-dial-timeout duration**
- Timeout for dialing tunnel transports (e.g., `10s`)
- Default: `10s`

#### SMUX Options:

**-smux-keepalive int**
- SMUX keepalive interval (seconds)
- Overrides profile

**-smux-max-recv int**
- SMUX max receive buffer (bytes)
- Overrides profile

**-smux-max-stream int**
- SMUX max stream buffer (bytes)
- Overrides profile

**-smux-frame-size int**
- SMUX frame size (bytes)
- Default: `32768` (32KB)
- Overrides profile

#### KCP Options:

**-kcp-nodelay int**
- Enable KCP nodelay
- `0` = disable, `1` = enable
- Overrides profile

**-kcp-interval int**
- KCP update interval (milliseconds)
- Overrides profile

**-kcp-resend int**
- KCP fast resend threshold
- Overrides profile

**-kcp-nc int**
- Disable KCP congestion control
- `0` = disable, `1` = enable
- Overrides profile

**-kcp-sndwnd int**
- KCP send window size
- Overrides profile

**-kcp-rcvwnd int**
- KCP receive window size
- Overrides profile

**-kcp-mtu int**
- KCP Maximum Transmission Unit
- Overrides profile

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

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 768
  rcvwnd: 768
  mtu: 1350

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

kcp:
  nodelay: 1
  interval: 8
  resend: 2
  nc: 1
  sndwnd: 512
  rcvwnd: 512
  mtu: 1350

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

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

advanced:
  websocket_read_buffer: 262144
  websocket_write_buffer: 262144
  websocket_compression: false

heartbeat: 10
verbose: false
```

**Run client:**

```bash
netrix -config client-wss.yaml
```

---

## License

This project is commercial software. Please contact the author for licensing information.

---

Made with ❤️ by Netrix Team

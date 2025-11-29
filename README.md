# Netrix - Advanced Reverse Tunneling Solution

[![Go Version](https://img.shields.io/badge/Go-1.20+-00ADD8?style=flat&logo=go)](https://golang.org/)


---

## 🌐 Language | زبان

**فارسی** | [فارسی (Persian)](#about-netrix-reverse-tunneling-فارسی)

<div dir="rtl">

**English** | [English (انگلیسی)](#about-netrix-reverse-tunneling)

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

## 🚀 Quick Start with Management Script

For easier tunnel management, we provide a Python management script that handles configuration, installation, and system optimization automatically.

### 🔐 License Purchase

**Important:** To use Netrix, you need to purchase a license first.

**Purchase License:**
- 🤖 **Telegram Bot**: [@mnxcore_bot](https://t.me/mnxcore_bot)
- 👤 **Developer Contact**: [@g0dline](https://t.me/g0dline)

After purchasing the license, you will receive a license key that you need to activate before using Netrix.

### Installation

```bash
wget https://raw.githubusercontent.com/Karrari-Dev/Netrix-/main/netrixcore.py -O /usr/local/bin/netrixcore.py && chmod +x /usr/local/bin/netrixcore.py && echo 'alias netrixcore="python3 /usr/local/bin/netrixcore.py"' >> ~/.bashrc && source ~/.bashrc && netrixcore
```

### Features
- ✅ **Interactive Menu**: Easy-to-use interface for tunnel management
- ✅ **Auto Configuration**: Automatically generates YAML config files
- ✅ **Core Management**: Install/Update/Delete Netrix core binary
- ✅ **Systemd Integration**: Auto-start tunnels on boot with systemd
- ✅ **System Optimizer**: Optimize Linux kernel parameters for high performance
- ✅ **Multi-Transport**: Support for TCP, KCP, WebSocket, and WSS
- ✅ **Certificate Management**: Automatic Let's Encrypt certificate acquisition
- ✅ **Profile Selection**: Choose from 4 performance profiles
- ✅ **Port Mapping**: Easy TCP/UDP port mapping with ranges support
- 🔐 **License Management**: Built-in license activation and validation

### Usage

Run the script and follow the interactive menu:

```bash
netrixcore
```

**Main Menu Options:**
1. **Create Tunnel** - Create Server or Client tunnel with interactive prompts
2. **Status** - View all tunnels and their status (running/stopped)
3. **Stop** - Stop running tunnels
4. **Restart** - Restart tunnels
5. **Delete** - Remove tunnels and their configuration files
6. **Netrix Core Management** - Install/Update/Delete Netrix core binary
7. **System Optimizer** - Optimize Linux kernel parameters for high traffic

### 📞 Support & Contact

**Purchase License:**
- 🤖 **Telegram Bot**: [@mnxcore_bote](https://t.me/mnxcore_bot)

**Developer:**
- 👤 **Telegram**: [@g0dline](https://t.me/g0dline)


---

## Manual Configuration

If you prefer manual configuration, you can create YAML files and run Netrix directly.

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

## Performance Profiles

Netrix provides 4 pre-configured performance profiles optimized for different use cases:

| Profile | Use Case | SMUX Keepalive | SMUX Buffer | KCP Interval | KCP Windows | Best For |
|---------|----------|----------------|-------------|--------------|-------------|----------|
| **balanced** (default) | General purpose | 8s | 8MB | 10ms | 768/768 | Most users, balanced performance |
| **aggressive** | High throughput | 5s | 16MB | 8ms | 1024/1024 | Maximum speed, more CPU usage |
| **latency** | Low latency | 3s | 4MB | 8ms | 768/768 | Gaming, real-time apps |
| **cpu-efficient** | Low CPU usage | 10s | 8MB | 20ms | 512/512 | Resource-constrained servers |

**Profile Details:**

- **balanced**: Best overall performance for most users. Good balance between latency, throughput, and CPU usage.
- **aggressive**: Maximum throughput and speed. Uses more CPU and memory. Best for high-bandwidth applications.
- **latency**: Optimized for low latency. Best for gaming, video calls, and real-time applications (like Instagram).
- **cpu-efficient**: Minimizes CPU usage. Best for servers with limited resources or when running many instances.

---

## Complete Examples for Each Transport

### TCP Multiplexing (tcpmux)

**Server file: server-tcp.yaml**

```yaml
mode: "server"
listen: "0.0.0.0:4000"
transport: "tcpmux"
psk: "your_secret_key_here"
profile: "balanced"  # balanced|aggressive|latency|cpu-efficient

smux:
  keepalive: 8          # seconds
  max_recv: 8388608     # 8MB (bytes)
  max_stream: 8388608   # 8MB (bytes)
  frame_size: 32768     # 32KB (bytes)

advanced:
  # TCP Settings
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

max_sessions: 0      # 0 = unlimited, recommended: 0 or 1000+
heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
```

**Run server:**

```bash
netrix -config server-tcp.yaml
```

**Client file: client-tcp.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"  # balanced|aggressive|latency|cpu-efficient

paths:
  - transport: "tcpmux"
    addr: "SERVER_IP:4000"
    connection_pool: 4        # number of simultaneous tunnels
    aggressive_pool: false    # aggressively re-dial on failure
    retry_interval: 3         # seconds
    dial_timeout: 10          # seconds

smux:
  keepalive: 8          # seconds
  max_recv: 8388608     # 8MB (bytes)
  max_stream: 8388608   # 8MB (bytes)
  frame_size: 32768     # 32KB (bytes)

advanced:
  # TCP Settings
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging
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

smux:
  keepalive: 3
  max_recv: 4194304
  max_stream: 4194304
  frame_size: 32768

kcp:
  nodelay: 1          # 0=disable, 1=enable
  interval: 8         # milliseconds (update interval)
  resend: 2           # fast resend threshold
  nc: 1               # disable congestion control (0=disable, 1=enable)
  sndwnd: 768         # send window size
  rcvwnd: 768         # receive window size
  mtu: 1350           # Maximum Transmission Unit (bytes)

advanced:
  # TCP Settings (for local connections)
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # UDP Settings (for tunnel connection)
  udp_read_buffer: 4194304   # 4MB (bytes)
  udp_write_buffer: 4194304  # 4MB (bytes)
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

max_sessions: 0      # 0 = unlimited, recommended: 0 or 1000+
heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:22"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
```

**Run server:**

```bash
netrix -config server-kcp.yaml
```

**Client file: client-kcp.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "latency"  # balanced|aggressive|latency|cpu-efficient

paths:
  - transport: "kcpmux"
    addr: "SERVER_IP:4001"
    connection_pool: 4        # number of simultaneous tunnels
    aggressive_pool: true     # aggressively re-dial on failure
    retry_interval: 1         # seconds
    dial_timeout: 5           # seconds

smux:
  keepalive: 3          # seconds
  max_recv: 4194304     # 4MB (bytes)
  max_stream: 4194304   # 4MB (bytes)
  frame_size: 32768     # 32KB (bytes)

kcp:
  nodelay: 1          # 0=disable, 1=enable
  interval: 8         # milliseconds (update interval)
  resend: 2           # fast resend threshold
  nc: 1               # disable congestion control (0=disable, 1=enable)
  sndwnd: 768         # send window size
  rcvwnd: 768         # receive window size
  mtu: 1350           # Maximum Transmission Unit (bytes)

advanced:
  # TCP Settings (for local connections)
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # UDP Settings (for tunnel connection)
  udp_read_buffer: 4194304   # 4MB (bytes)
  udp_write_buffer: 4194304  # 4MB (bytes)
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging
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
profile: "balanced"  # balanced|aggressive|latency|cpu-efficient

smux:
  keepalive: 8          # seconds
  max_recv: 8388608     # 8MB (bytes)
  max_stream: 8388608   # 8MB (bytes)
  frame_size: 32768     # 32KB (bytes)

advanced:
  # TCP Settings (for local connections)
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # WebSocket Settings (for tunnel connection)
  websocket_read_buffer: 262144   # 256KB (bytes)
  websocket_write_buffer: 262144  # 256KB (bytes)
  websocket_compression: false    # enable/disable compression
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

max_sessions: 0      # 0 = unlimited, recommended: 0 or 1000+
heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
```

**Run server:**

```bash
netrix -config server-ws.yaml
```

**Client file: client-ws.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"  # balanced|aggressive|latency|cpu-efficient

paths:
  - transport: "wsmux"
    addr: "SERVER_IP:8080"
    connection_pool: 8        # number of simultaneous tunnels
    aggressive_pool: false    # aggressively re-dial on failure
    retry_interval: 3         # seconds
    dial_timeout: 10          # seconds

smux:
  keepalive: 8          # seconds
  max_recv: 8388608     # 8MB (bytes)
  max_stream: 8388608   # 8MB (bytes)
  frame_size: 32768     # 32KB (bytes)

advanced:
  # TCP Settings (for local connections)
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # WebSocket Settings (for tunnel connection)
  websocket_read_buffer: 262144   # 256KB (bytes)
  websocket_write_buffer: 262144  # 256KB (bytes)
  websocket_compression: false    # enable/disable compression
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging
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
profile: "balanced"  # balanced|aggressive|latency|cpu-efficient

# TLS Certificate Files (required for wssmux)
cert_file: "/path/to/server.crt"  # TLS certificate file path
key_file: "/path/to/server.key"   # TLS private key file path

smux:
  keepalive: 8          # seconds
  max_recv: 8388608     # 8MB (bytes)
  max_stream: 8388608   # 8MB (bytes)
  frame_size: 32768     # 32KB (bytes)

advanced:
  # TCP Settings (for local connections)
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # WebSocket Settings (for tunnel connection)
  websocket_read_buffer: 262144   # 256KB (bytes)
  websocket_write_buffer: 262144  # 256KB (bytes)
  websocket_compression: false    # enable/disable compression
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

max_sessions: 0      # 0 = unlimited, recommended: 0 or 1000+
heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging

maps:
  - type: "tcp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
  - type: "udp"
    bind: "0.0.0.0:2066"
    target: "127.0.0.1:2066"
```

**Run server:**

```bash
netrix -config server-wss.yaml
```

**Client file: client-wss.yaml**

```yaml
mode: "client"
psk: "your_secret_key_here"
profile: "balanced"  # balanced|aggressive|latency|cpu-efficient

paths:
  - transport: "wssmux"
    addr: "SERVER_IP:8443"
    connection_pool: 8        # number of simultaneous tunnels
    aggressive_pool: false    # aggressively re-dial on failure
    retry_interval: 3         # seconds
    dial_timeout: 10          # seconds

smux:
  keepalive: 8          # seconds
  max_recv: 8388608     # 8MB (bytes)
  max_stream: 8388608   # 8MB (bytes)
  frame_size: 32768     # 32KB (bytes)

advanced:
  # TCP Settings (for local connections)
  tcp_nodelay: true
  tcp_keepalive: 15     # seconds
  tcp_read_buffer: 4194304   # 4MB (bytes)
  tcp_write_buffer: 4194304  # 4MB (bytes)
  
  # WebSocket Settings (for tunnel connection)
  websocket_read_buffer: 262144   # 256KB (bytes)
  websocket_write_buffer: 262144  # 256KB (bytes)
  websocket_compression: false    # enable/disable compression
  
  # Connection Management
  cleanup_interval: 3      # seconds
  session_timeout: 30      # seconds
  connection_timeout: 60   # seconds
  stream_timeout: 120      # seconds
  max_connections: 2000    # maximum concurrent connections
  
  # UDP Flow Management
  max_udp_flows: 1000      # maximum concurrent UDP flows
  udp_flow_timeout: 300    # seconds (5 minutes)
  
  # Buffer Pool Sizes (optional - 0 = use default)
  buffer_pool_size: 0           # default: 131072 (128KB)
  large_buffer_pool_size: 0     # default: 131072 (128KB)
  udp_frame_pool_size: 0        # default: 65856 (64KB+256)
  udp_data_slice_size: 0        # default: 1500 (MTU)

heartbeat: 10        # seconds (default: 10)
verbose: false       # enable verbose logging
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

---

## 🚀 شروع سریع با اسکریپت مدیریت

برای مدیریت آسان‌تر تانل‌ها، یک اسکریپت مدیریتی پایتون ارائه می‌دهیم که به صورت خودکار تنظیمات، نصب و بهینه‌سازی سیستم را انجام می‌دهد.

### 🔐 خرید لایسنس

**مهم:** برای استفاده از Netrix، ابتدا باید لایسنس خریداری کنید.

**خرید لایسنس:**
- 🤖 **ربات تلگرام**: [@mnxcore_bot](https://t.me/mnxcore_bot)
- 👤 **تماس با سازنده**: [@g0dline](https://t.me/g0dline)

پس از خرید لایسنس، یک کلید لایسنس دریافت خواهید کرد که باید قبل از استفاده از Netrix آن را فعال کنید.

### نصب

```bash
wget https://raw.githubusercontent.com/Karrari-Dev/Netrix-/main/netrixcore.py -O /usr/local/bin/netrixcore.py && chmod +x /usr/local/bin/netrixcore.py && echo 'alias netrixcore="python3 /usr/local/bin/netrixcore.py"' >> ~/.bashrc && source ~/.bashrc && netrixcore
```



### امکانات

- ✅ **منوی تعاملی**: رابط کاربری آسان برای مدیریت تانل‌ها
- ✅ **تنظیمات خودکار**: ساخت خودکار فایل‌های کانفیگ YAML
- ✅ **مدیریت هسته**: نصب/آپدیت/حذف باینری هسته Netrix
- ✅ **یکپارچگی با Systemd**: راه‌اندازی خودکار تانل‌ها با systemd
- ✅ **بهینه‌ساز سیستم**: بهینه‌سازی پارامترهای کرنل لینوکس برای عملکرد بالا
- ✅ **چند Transport**: پشتیبانی از TCP، KCP، WebSocket و WSS
- ✅ **مدیریت گواهینامه**: دریافت خودکار گواهینامه Let's Encrypt
- ✅ **انتخاب پروفایل**: انتخاب از 4 پروفایل عملکردی
- ✅ **نگاشت پورت**: نگاشت آسان پورت‌های TCP/UDP با پشتیبانی از محدوده
- 🔐 **مدیریت لایسنس**: فعال‌سازی و اعتبارسنجی لایسنس داخلی

### نحوه استفاده

اسکریپت را اجرا کنید و از منوی تعاملی استفاده کنید:

```bash
netrixcore
```

**گزینه‌های منوی اصلی:**
1. **ساخت تانل** - ساخت تانل سرور یا کلاینت با راهنمای تعاملی
2. **وضعیت** - مشاهده تمام تانل‌ها و وضعیت آن‌ها (در حال اجرا/متوقف شده)
3. **توقف** - توقف تانل‌های در حال اجرا
4. **راه‌اندازی مجدد** - راه‌اندازی مجدد تانل‌ها
5. **حذف** - حذف تانل‌ها و فایل‌های کانفیگ آن‌ها
6. **مدیریت هسته Netrix** - نصب/آپدیت/حذف باینری هسته Netrix
7. **بهینه‌ساز سیستم** - بهینه‌سازی پارامترهای کرنل لینوکس برای ترافیک بالا

### 📞 پشتیبانی و تماس

**خرید لایسنس:**
- 🤖 **ربات تلگرام**: [@mnxcore_bot]https://t.me/mnxcore_bot)

**سازنده:**
- 👤 **تلگرام**: [@g0dline](https://t.me/g0dline)


</div>

---

<div dir="rtl">

## تنظیمات دستی

اگر تنظیمات دستی را ترجیح می‌دهید، می‌توانید فایل‌های YAML را خودتان بسازید و Netrix را مستقیماً اجرا کنید.

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

## پروفایل‌های عملکرد (Performance Profiles)

Netrix شامل 4 پروفایل از پیش تنظیم شده است که برای موارد استفاده مختلف بهینه شده‌اند:

| پروفایل | کاربرد | SMUX Keepalive | SMUX Buffer | KCP Interval | KCP Windows | بهترین برای |
|---------|--------|----------------|-------------|--------------|-------------|-------------|
| **balanced** (پیش‌فرض) | استفاده عمومی | 8s | 8MB | 10ms | 768/768 | بیشتر کاربران، عملکرد متعادل |
| **aggressive** | سرعت بالا | 5s | 16MB | 8ms | 1024/1024 | حداکثر سرعت، مصرف CPU بیشتر |
| **latency** | تاخیر کم | 3s | 4MB | 8ms | 768/768 | گیمینگ، اپلیکیشن‌های real-time |
| **cpu-efficient** | مصرف CPU کم | 10s | 8MB | 20ms | 512/512 | سرورهای محدود از نظر منابع |

**جزئیات پروفایل‌ها:**

- **balanced**: بهترین عملکرد کلی برای بیشتر کاربران. تعادل خوب بین latency، throughput و مصرف CPU.
- **aggressive**: حداکثر throughput و سرعت. CPU و حافظه بیشتری استفاده می‌کند. بهترین برای اپلیکیشن‌های پهن‌باند.
- **latency**: بهینه شده برای latency پایین. بهترین برای گیمینگ، تماس ویدیویی و اپلیکیشن‌های real-time (مثل اینستاگرام).
- **cpu-efficient**: مصرف CPU را به حداقل می‌رساند. بهترین برای سرورهای محدود یا هنگام اجرای چندین instance.

---



## License

This project is commercial software. Please contact the author for licensing information.

---

Made with ❤️ by Netrix Team

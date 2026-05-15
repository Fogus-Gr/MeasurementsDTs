from bcc import BPF
import time
import socket
import struct
import sys
import ctypes

def log(message, level="INFO"):
    print(f"[{level}] {message}", file=sys.stderr)

def main(poll_interval_s=0.1):
    if len(sys.argv) < 4:
        log("Usage: python3 bcc_rx_bytes.py <streamer_ip> <streamer_port> <hpe_port>", "ERROR")
        sys.exit(1)

    STREAMER_IP = sys.argv[1]
    STREAMER_PORT = int(sys.argv[2])
    HPE_PORT = int(sys.argv[3])
    INTERFACE = "eth0"
    OUTPUT_CSV = "/opt/tracer/output/hpe_video_rx.csv"

    # Convert IP to integer for BPF
    try:
        streamer_ip_int = struct.unpack("!I", socket.inet_aton(STREAMER_IP))[0]
    except:
        log("Invalid IP format", "ERROR")
        exit(1)

    bpf_text = """
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/bpf.h>

BPF_HASH(rx_bytes, u32, u64);

int count_rx(struct __sk_buff *skb) {
    u32 zero = 0;
    u64 len = skb->len;
    int cursor = 0;

    struct ethhdr eth;
    if (bpf_skb_load_bytes(skb, cursor, &eth, sizeof(eth)) < 0)
        return 0;
    cursor += sizeof(eth);

    if (eth.h_proto != htons(ETH_P_IP))
        return 0;

    struct iphdr ip;
    if (bpf_skb_load_bytes(skb, cursor, &ip, sizeof(ip)) < 0)
        return 0;
    cursor += sizeof(ip);

    if (ip.protocol != IPPROTO_TCP)
        return 0;

    struct tcphdr tcp;
    if (bpf_skb_load_bytes(skb, cursor, &tcp, sizeof(tcp)) < 0)
        return 0;

    // Filter: only count packets from the streamer IP on the expected ports
    if (ip.saddr != htonl(%d) || tcp.source != htons(%d) || tcp.dest != htons(%d))
        return 0;

    u64 *val = rx_bytes.lookup_or_init(&zero, &len);
    if (val) (*val) += len;

    return 0;
}
""" % (streamer_ip_int, STREAMER_PORT, HPE_PORT)

    try:
        # BPF setup with additional flags for compatibility
        b = BPF(text=bpf_text,
               cflags=["-Wno-macro-redefined",
                      "-Wno-address-of-packed-member",
                      "-Wno-unused-variable"])
        
        # Try different attachment methods
        try:
                # Fall back to socket filter
                fn = b.load_func("count_rx", BPF.SOCKET_FILTER)
                b.attach_raw_socket(fn, INTERFACE)
                log("Attached via socket filter")
        except Exception as e:
                log(f"Failed to attach BPF program: {str(e)}", "ERROR")
                raise
    

        # Main loop
        with open(OUTPUT_CSV, "w") as f:
            f.write("timestamp_ms,rx_video_bytes_delta,rx_video_bytes_current,rx_video_bytes_prev,dt_ms\n")
            key = ctypes.c_uint(0)
            prev_bytes = 0
            prev_time = int(time.time() * 1000)
            while True:
                try:
                    now_ms = int(time.time() * 1000)
                    val = b["rx_bytes"][key] if key in b["rx_bytes"] else 0
                    bytes = val.value if hasattr(val, 'value') else val
                    delta = bytes - prev_bytes
                    dt = now_ms - prev_time
                    f.write(f"{now_ms},{delta},{bytes},{prev_bytes},{dt}\n")
                    f.flush()
                    prev_bytes = bytes
                    prev_time = now_ms
                    time.sleep(poll_interval_s)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    log(f"Monitoring error: {str(e)}", "ERROR")
                    time.sleep(1)

    except Exception as e:
        log(f"BPF initialization failed: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    # Get polling interval from environment variable, default to 0.01s (10ms)
    poll_interval_s = float(os.getenv("BCC_POLL_INTERVAL_S", "0.01"))
    log(f"Using polling interval of {poll_interval_s * 1000:.0f}ms")
    main(poll_interval_s)
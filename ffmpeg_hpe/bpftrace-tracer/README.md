### Enable Unprivileged BPF: On newer kernels, unprivileged BPF access can be enabled. This is not recommended for 
### production environments due to security implications, but for testing, you can enable it:
```sudo echo 1 > /proc/sys/kernel/unprivileged_bpf_disabled```



```grep BPF /boot/config-$(uname -r)```
output

```
CONFIG_CGROUP_BPF=y
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT_ALWAYS_ON=y
CONFIG_BPF_UNPRIV_DEFAULT_OFF=y
CONFIG_IPV6_SEG6_BPF=y
CONFIG_NETFILTER_XT_MATCH_BPF=m
CONFIG_BPFILTER=y
CONFIG_BPFILTER_UMH=m
CONFIG_NET_CLS_BPF=m
CONFIG_NET_ACT_BPF=m
CONFIG_BPF_JIT=y
CONFIG_BPF_STREAM_PARSER=y
CONFIG_LWTUNNEL_BPF=y
CONFIG_HAVE_EBPF_JIT=y
CONFIG_BPF_EVENTS=y
CONFIG_BPF_KPROBE_OVERRIDE=y
CONFIG_TEST_BPF=m
```


```dmesg | grep -i bpf```
[   16.877104] bpfilter: Loaded bpfilter_umh pid 1028
[   16.877339] Started bpfilter


```grep -E "CONFIG_BPF=|CONFIG_BPF_SYSCALL=|CONFIG_NET_CLS_BPF=|CONFIG_NET_ACT_BPF=" /boot/config-$(uname -r)```

CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_NET_CLS_BPF=m
CONFIG_NET_ACT_BPF=m






python3 main.py --method alphapose --input http://172.18.0.2:8089/stream.h264 --csv --output_dir output/ --device GPU

grep '172.18.0.2.8089 > 172.18.0.3.53778' tcpdump_8089.log |
> awk '{for(i=1; i<=NF; i++) if($i == "length") {print $(i+1); break}}' |
> awk '{sum += $1} END {print sum}'



python3 main.py --method ${HPE_METHOD} --input ${HPE_INPUT} --csv --output_dir /output/ --device ${HPE_DEVICE} --measurement_interval_ms 10



docker logs bcc-tracer | grep "Detected HPE video port"

tail -f ./tracer_output/hpe_video_rx.csv


cat ./tracer_output/logs/bcc-tracer.logdocker logs bcc-tracer | grep "Detected HPE video port"

tail -f ./tracer_output/hpe_video_rx.csv


cat ./tracer_output/logs/bcc-tracer.log
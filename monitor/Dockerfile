FROM ubuntu:20.04
RUN apt-get update && apt-get install -y linux-tools-common linux-tools-$(uname -r) bpftrace
COPY monitor_pid.sh /monitor_pid.sh
RUN chmod +x /monitor_pid.sh
CMD ["/bin/bash"]
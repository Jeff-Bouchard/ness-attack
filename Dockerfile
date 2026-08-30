# Ness Attack Platform container (self-pentest box)
# Base: Debian 13 "trixie" — ships OpenSSL 3.5.x, which has native post-quantum
# ML-KEM / ML-DSA. That removes the reason the old image compiled OpenSSL 3.6
# from source (bookworm was stuck on 3.0.x). Build is now minutes faster and
# every package is distro-signed and security-patched.
#
# Goal: lightweight but useful attacker environment you can run
# against your own Ness stack.
#
# Scope: authorized self-pentest on infrastructure you own/control only.

FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive
# PEP 668 / externally-managed-environment safeguard bypass for container
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Fail the build if any stage of a pipe fails (e.g. a truncated curl into tar),
# so a broken tool binary never ends up in the image.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── System packages ───────────────────────────────────────────────
# openssl/libssl-dev come from trixie = 3.5.x (post-quantum capable), so no
# source build and no LD_LIBRARY_PATH juggling. sslscan below links the system
# libssl directly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl wget git \
       nano vim less file \
       python3 python3-pip python3-venv \
       nmap dnsutils whois traceroute \
       netcat-openbsd tcpdump iproute2 \
       socat jq openssl libssl-dev \
       sqlmap hydra \
    && rm -rf /var/lib/apt/lists/*

# Confirm the base really gives us post-quantum OpenSSL. If a future base image
# regresses below 3.5, this line fails the build loudly instead of silently
# shipping a box that cannot speak ML-KEM.
RUN openssl list -kem-algorithms | grep -qi 'ml-kem' \
    && echo "OpenSSL post-quantum ML-KEM: present" \
    && openssl version

# ── Tools not in the repos — install from source / releases ────────
# nikto — web server scanner
RUN git clone --depth 1 https://github.com/sullo/nikto.git /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && chmod +x /opt/nikto/program/nikto.pl

# testssl.sh — SSL/TLS checker
RUN git clone --depth 1 https://github.com/drwetter/testssl.sh.git /opt/testssl \
    && ln -s /opt/testssl/testssl.sh /usr/local/bin/testssl \
    && chmod +x /opt/testssl/testssl.sh

# sslscan — TLS scanner, built against the system (PQ-capable) OpenSSL 3.5.
# No /usr/local/ssl symlink needed: sslscan links -lssl/-lcrypto, which resolve
# from the system paths where libssl-dev installs them (was only needed when
# OpenSSL lived in /opt/openssl).
RUN apt-get update \
    && apt-get install -y --no-install-recommends make gcc git libc6-dev libssl-dev \
    && git clone --depth 1 https://github.com/rbsec/sslscan.git /tmp/sslscan-src \
    && make -C /tmp/sslscan-src \
    && cp /tmp/sslscan-src/sslscan /usr/local/bin/ \
    && rm -rf /tmp/sslscan-src \
    && apt-get purge -y make gcc git libc6-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ffuf — fast web fuzzer (single Go binary, replaces dirb)
RUN FFUF_VER="2.1.0" \
    && curl -sL "https://github.com/ffuf/ffuf/releases/download/v${FFUF_VER}/ffuf_${FFUF_VER}_linux_amd64.tar.gz" \
       | tar xz -C /usr/local/bin ffuf \
    && chmod +x /usr/local/bin/ffuf

# gobuster — directory/file brute-forcer (Go binary, tar.gz since v3.7+)
RUN GOBUSTER_VER="3.8.2" \
    && curl -sL "https://github.com/OJ/gobuster/releases/download/v${GOBUSTER_VER}/gobuster_Linux_x86_64.tar.gz" \
       | tar xz -C /tmp \
    && cp /tmp/gobuster /usr/local/bin/gobuster \
    && chmod +x /usr/local/bin/gobuster \
    && rm -f /tmp/gobuster

# wordlists for ffuf / gobuster / hydra / sqlmap
RUN mkdir -p /usr/share/wordlists \
    && curl -sL "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" \
       -o /usr/share/wordlists/common.txt \
    && curl -sL "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/darkweb2017-top100.txt" \
       -o /usr/share/wordlists/top100-passwords.txt

# ── Python tooling: exploit scripting, protocol libs, web UI ───────
RUN pip3 install --no-cache-dir \
      pwntools \
      requests httpx \
      ipython \
      flask \
      scapy \
      paramiko cryptography \
      impacket \
      dnspython \
      sslyze \
      beautifulsoup4 \
      python-nmap

WORKDIR /root

# Web UI for orchestrating common self-pentest actions
COPY webui /opt/ness-attack-webui

# Banner so you always know you're in the attack box.
# (printf with one FORMAT and a trailing string arg dropped the second line in
# the old Dockerfile — '%s' consumes each line so both are written.)
RUN printf '%s\n' \
      '' \
      '*** Ness Attack Platform (self-pentest only) ***' \
      'Target this container only at infrastructure you own / control. Do no harm.' \
      '' > /etc/motd

# Flask default inside container; host-side port is chosen by run-console.sh
EXPOSE 18080

CMD ["bash", "-l"]

# ness-attack

A lightweight, self-contained **offensive-security lab container** for testing
your own [PrivateNess](https://ness.cx) stack — recon, web, and TLS tooling in
one Debian image, driven from the shell or a small web console.

> **Scope — read this first.** This box is for **authorized self-pentest only**:
> infrastructure you own or are explicitly permitted to test. The tools inside
> (nmap, sqlmap, hydra, nikto, sslscan, ffuf, gobuster, impacket, …) are
> standard, legal, dual-use security instruments. Pointing them at systems you
> do not control is likely illegal and is not what this project is for.
> **Do no harm.**

## What's inside

| Category | Tools |
|---|---|
| Recon | `nmap`, `dnsutils`, `whois`, `traceroute` |
| Web | `nikto`, `ffuf`, `gobuster`, `sqlmap`, `curl`/`wget` |
| TLS | `sslscan`, `testssl.sh`, `sslyze`, `openssl` (**3.5.x, post-quantum ML-KEM / ML-DSA**) |
| Net | `netcat-openbsd`, `socat`, `tcpdump`, `iproute2` |
| Scripting | `python3` + `pwntools`, `impacket`, `scapy`, `paramiko`, `requests`/`httpx` |
| Console | Flask web UI (`webui/app.py`) — buttons map to a fixed allowlist of commands |

### Post-quantum TLS, without the wait

The base is **Debian 13 "trixie"**, whose `openssl` package is **3.5.x** — it
ships ML-KEM and ML-DSA natively. Earlier revisions compiled OpenSSL 3.6 from
source (minutes per build) because Debian 12 was stuck on 3.0.x. That source
build is gone; the image now installs a distro-signed, security-patched OpenSSL
and **fails the build loudly** if a future base image ever regresses below a
post-quantum-capable version.

## Build & run

```bash
# one-shot: build the image and open the console on a free port
bash ./run-console.sh
```

Or manually:

```bash
docker build -t ness-attack:latest .
docker run --rm -it -p 18080:18080 ness-attack:latest
# inside the container:
python3 /opt/ness-attack-webui/app.py     # console on :18080
# ...or just use the shell and the tools directly
```

The web console defaults its target to `127.0.0.1`. Change it to a host you own.

## Security notes

- The web console runs a **fixed allowlist** of actions and passes the target as
  an `argv` element (no `shell=True`), so there is no shell injection.
- It performs **no authentication** and binds inside the container — do not
  expose its port to an untrusted network. `run-console.sh` publishes it to
  localhost.
- Known minor limitation: a `target` beginning with `-` could be interpreted as
  a flag by the underlying tool (argument injection, not shell injection). Keep
  targets to hostnames / IPs / CIDRs.

## Layout

```
Dockerfile            the lab image (Debian trixie + tools)
run-console.sh        build-and-run helper (chooses a free host port)
webui/
  app.py              Flask console — allowlisted actions only
  *.png *.ico         favicons
```

## License

Released under the MIT License (see `LICENSE`). Swap it for whatever you prefer
before publishing — MIT is a permissive default, not a considered choice for
your project.

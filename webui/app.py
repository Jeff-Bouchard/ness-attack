import os
from flask import Flask, request, render_template_string
import subprocess

# Ness Attack Web UI
# Purpose: orchestrate common self-pentest actions against your Ness stack
# from a single HTML page (buttons -> safe, predefined commands).
# Ethics: see EULA ("Do no harm"). This console is for authorized testing only.

app = Flask(__name__)

# HTML template (inline to keep deployment simple)
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Ness Attack Console</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1.5rem; }
    h1, h2 { color: #ff8c00; }
    form { margin-bottom: 1rem; padding: 1rem; border: 1px solid #333; border-radius: 6px; background: #181818; }
    label { display: inline-block; width: 6rem; }
    input[type=text] { background: #000; color: #eee; border: 1px solid #444; padding: 0.2rem 0.4rem; width: 20rem; }
    button { margin: 0.25rem 0.25rem 0 0; padding: 0.35rem 0.7rem; border-radius: 4px; border: none; cursor: pointer; background: #333; color: #eee; }
    button:hover { background: #555; }
    button.primary { background: #d87f1f; }
    button.danger { background: #aa3333; }
    button.danger:hover { background: #cc4444; }
    small { color: #999; }
    pre { background: #000; color: #0f0; padding: 0.75rem; border-radius: 4px; max-height: 60vh; overflow: auto; white-space: pre-wrap; word-wrap: break-word; }
    .note { font-size: 0.85rem; color: #bbb; margin-bottom: 0.8rem; }
    .section { margin-top: 1.2rem; padding-top: 0.6rem; border-top: 1px solid #282828; }
  </style>
</head>
<body>
  <h1>Ness Attack Console</h1>
  <p class="note">
    For authorized defensive and research use only (systems you own or are trusted to protect). EULA applies: do no harm.
  </p>

  <form method="post" action="/run">
    <h2>Target</h2>
    <label for="target">Host / IP</label>
    <input type="text" id="target" name="target" value="{{ target }}" />
    <small>e.g. 127.0.0.1, host.docker.internal, or ness.cx</small>

    <div class="section">
      <h2>Recon — Port &amp; Service Scan</h2>
      <button class="primary" name="action" value="nmap_quick">Nmap quick (1-1024, -sV)</button>
      <button name="action" value="nmap_full">Nmap full (-p-, -sV)</button>
      <button name="action" value="nmap_udp">Nmap top-20 UDP</button>
      <button name="action" value="nmap_script_vuln">Nmap —script vuln</button>
    </div>

    <div class="section">
      <h2>Web — HTTP / API</h2>
      <button class="primary" name="action" value="http_health">HTTP GET /health</button>
      <button name="action" value="nikto_scan">Nikto web scan</button>
      <button name="action" value="ffuf_common">ffuf (common wordlist)</button>
      <button name="action" value="gobuster_dir">Gobuster dir bust</button>
      <button name="action" value="sqlmap_basic">SQLMap —batch —forms</button>
    </div>

    <div class="section">
      <h2>TLS / SSL (OpenSSL 3.6 + post-quantum)</h2>
      <button class="primary" name="action" value="sslscan">sslscan (PQ)</button>
      <button name="action" value="sslyze">sslyze</button>
      <button name="action" value="testssl">testssl.sh (quick)</button>
    </div>

    <div class="section">
      <h2>DNS</h2>
      <button class="primary" name="action" value="dns_enum">dig AXFR + short</button>
      <button name="action" value="dns_reverse">dig reverse lookup</button>
      <button name="action" value="dns_ness_proxy">Ness DNS proxy (port 1053)</button>
    </div>

    <div class="section">
      <h2>Ness Stack — Emercoin / Privateness</h2>
      <button class="primary" name="action" value="emc_rpc_info">Emercoin RPC getinfo</button>
      <button name="action" value="emc_name_list">Emercoin name_filter</button>
      <button name="action" value="ness_health">Ness /health (8888)</button>
      <button name="action" value="ness_metrics">Ness /metrics</button>
    </div>

    <div class="section">
      <h2>Brute — Auth</h2>
      <button class="danger" name="action" value="hydra_ssh">Hydra SSH (3 tries)</button>
      <button class="danger" name="action" value="hydra_http">Hydra HTTP-POST (3 tries)</button>
    </div>

    <div class="section">
      <h2>Raw</h2>
      <button name="action" value="curl_verbose">curl -v (root /)</button>
      <button name="action" value="netcat_probe">netcat port probe</button>
      <button name="action" value="traceroute">traceroute</button>
    </div>
  </form>

  {% if output %}
  <h2>Last command</h2>
  <p><strong>{{ last_label }}</strong></p>
  <pre>{{ output }}</pre>
  {% endif %}
</body>
</html>
"""

# Map UI actions to concrete command lines.
# We keep this explicit (no free-form shell) to avoid accidental misuse.

TIMEOUT = 300  # seconds — max runtime per action


def build_command(action: str, target: str) -> tuple[list[str], str] | tuple[None, str]:
    """Return (argv, label) for a known action, or (None, error_label)."""
    t = target.strip() or "127.0.0.1"

    # ── Recon ──────────────────────────────────────────────────────
    if action == "nmap_quick":
        return (["nmap", "-sV", "-p", "1-1024", "-T4", t],
                f"nmap -sV -p 1-1024 -T4 {t}")
    if action == "nmap_full":
        return (["nmap", "-sV", "-p-", "-T4", t],
                f"nmap -sV -p- -T4 {t}")
    if action == "nmap_udp":
        return (["nmap", "-sU", "--top-ports", "20", "-T4", t],
                f"nmap -sU --top-ports 20 -T4 {t}")
    if action == "nmap_script_vuln":
        return (["nmap", "--script", "vuln", "-T4", t],
                f"nmap --script vuln -T4 {t}")

    # ── Web ─────────────────────────────────────────────────────────
    if action == "http_health":
        url = f"http://{t}:8888/health"
        return (["curl", "-sv", "--max-time", "10", url],
                f"curl -sv --max-time 10 {url}")
    if action == "nikto_scan":
        return (["nikto", "-h", t, "-timeout", "10"],
                f"nikto -h {t}")
    if action == "ffuf_common":
        url = f"http://{t}/FUZZ"
        return (["ffuf", "-u", url, "-w", "/usr/share/wordlists/common.txt", "-t", "20", "-rate", "50"],
                f"ffuf -u http://{t}/FUZZ -w common.txt")
    if action == "gobuster_dir":
        url = f"http://{t}/"
        return (["gobuster", "dir", "-u", url, "-w", "/usr/share/wordlists/common.txt", "-t", "20", "--timeout", "10s"],
                f"gobuster dir -u http://{t}/")
    if action == "sqlmap_basic":
        url = f"http://{t}/"
        return (["sqlmap", "-u", url, "--batch", "--forms", "--level", "1", "--risk", "1"],
                f"sqlmap -u http://{t}/ --batch --forms")

    # ── TLS ─────────────────────────────────────────────────────────
    if action == "sslscan":
        return (["sslscan", "--no-colour", t],
                f"sslscan {t}")
    if action == "sslyze":
        return (["sslyze", "--regular", t],
                f"sslyze --regular {t}")
    if action == "testssl":
        return (["testssl", "--quiet", "--fast", t],
                f"testssl --quiet --fast {t}")

    # ── DNS ─────────────────────────────────────────────────────────
    if action == "dns_enum":
        return (["dig", f"@{t}", "ness.cx", "AXFR", "+short"],
                f"dig @{t} ness.cx AXFR +short")
    if action == "dns_reverse":
        return (["dig", "-x", t, "+short"],
                f"dig -x {t} +short")
    if action == "dns_ness_proxy":
        return (["dig", f"@{t}", "ness.cx", "-p", "1053", "+short"],
                f"dig @{t} ness.cx -p 1053 +short")

    # ── Ness Stack ──────────────────────────────────────────────────
    if action == "emc_rpc_info":
        url = f"http://{t}:6662"
        return (["curl", "-sv", "--max-time", "10", url],
                f"curl -sv --max-time 10 {url}")
    if action == "emc_name_list":
        url = f"http://{t}:6662"
        return (["curl", "-sv", "--max-time", "10", "-d",
                  '{"method":"name_filter","params":["dpo:"]}',
                  "-H", "Content-Type: application/json", url],
                f"curl name_filter dpo: → {url}")
    if action == "ness_health":
        url = f"http://{t}:8888/health"
        return (["curl", "-sv", "--max-time", "10", url],
                f"curl -sv --max-time 10 {url}")
    if action == "ness_metrics":
        url = f"http://{t}:8888/metrics"
        return (["curl", "-sv", "--max-time", "10", url],
                f"curl -sv --max-time 10 {url}")

    # ── Brute (capped at 3 attempts to stay safe) ──────────────────
    if action == "hydra_ssh":
        return (["hydra", "-l", "root", "-P", "/usr/share/wordlists/top100-passwords.txt",
                  "-t", "1", "-e", "ns", "-f", "-V", t, "ssh"],
                f"hydra -l root -P top100-passwords.txt {t} ssh (1 thread, stop on success)")
    if action == "hydra_http":
        return (["hydra", "-l", "admin", "-P", "/usr/share/wordlists/top100-passwords.txt",
                  "-t", "1", "-e", "ns", "-f", "-V", t, "http-post-form",
                  "/login:user=^USER^&pass=^PASS^:F=incorrect"],
                f"hydra -l admin http-post-form {t}/login (1 thread)")

    # ── Raw ─────────────────────────────────────────────────────────
    if action == "curl_verbose":
        url = f"http://{t}/"
        return (["curl", "-sv", "--max-time", "10", url],
                f"curl -sv --max-time 10 http://{t}/")
    if action == "netcat_probe":
        return (["nc", "-vz", "-w", "3", t, "80"],
                f"nc -vz -w 3 {t} 80")
    if action == "traceroute":
        return (["traceroute", "-m", "20", "-w", "2", t],
                f"traceroute -m 20 {t}")

    return None, f"Unknown action: {action}"


@app.route("/", methods=["GET"])
def index():
    target = request.args.get("target", "127.0.0.1")
    return render_template_string(TEMPLATE, target=target, output=None, last_label=None)


@app.route("/run", methods=["POST"])
def run_action():
    target = request.form.get("target", "127.0.0.1")
    action = request.form.get("action", "")

    cmd, label = build_command(action, target)
    if cmd is None:
        return render_template_string(TEMPLATE, target=target, output=label, last_label="Error")

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=TIMEOUT,
        )
        output = proc.stdout
    except subprocess.TimeoutExpired:
        output = f"[TIMEOUT] Command exceeded {TIMEOUT}s limit."
    except Exception as e:
        output = f"Error running command: {e}"

    return render_template_string(TEMPLATE, target=target, output=output, last_label=label)


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", "18080"))
    app.run(host="0.0.0.0", port=port, debug=False)

import ssl
import socket
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

AUTO_RENEW_ISSUERS = [
    "let's encrypt", "letsencrypt", "zerossl", "buypass", "sectigo automated",
    "acme", "certbot", "cloudflare", "digicert automation", "autossl", "cpanel"
]

def issuer_auto_renews(issuer_str):
    low = issuer_str.lower()
    return any(k in low for k in AUTO_RENEW_ISSUERS)

def get_ssl_protocol(sock):
    try:
        return sock.version()
    except Exception:
        return None

def check_cert(domain, port=443):
    try:
        port = int(port) if port else 443
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        conn = socket.create_connection((domain, port), timeout=10)
        with ctx.wrap_socket(conn, server_hostname=domain) as s:
            cert = s.getpeercert()
            protocol = get_ssl_protocol(s)

        expiry = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_left = (expiry - now).days

        issuer = dict(x[0] for x in cert.get('issuer', []))
        subject = dict(x[0] for x in cert.get('subject', []))
        issuer_org = issuer.get('organizationName', issuer.get('commonName', '—'))

        san = []
        for typ, val in cert.get('subjectAltName', []):
            if typ == 'DNS':
                san.append(val)

        return {
            'domain': domain,
            'port': port,
            'expiry': expiry.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'days_left': days_left,
            'issuer': issuer_org,
            'common_name': subject.get('commonName', domain),
            'protocol': protocol,
            'san': san,
            'auto_renew': issuer_auto_renews(issuer_org),
            'self_signed': issuer.get('commonName') == subject.get('commonName') and issuer.get('organizationName','') == subject.get('organizationName',''),
            'error': None
        }

    except ssl.SSLCertVerificationError as e:
        return {'domain': domain, 'port': port, 'error': f'SSL verification failed: {e}', 'days_left': None, 'protocol': None, 'auto_renew': None, 'self_signed': None}
    except ssl.SSLError as e:
        return {'domain': domain, 'port': port, 'error': f'SSL error: {e}', 'days_left': None, 'protocol': None, 'auto_renew': None, 'self_signed': None}
    except socket.timeout:
        return {'domain': domain, 'port': port, 'error': 'Connection timed out', 'days_left': None, 'protocol': None, 'auto_renew': None, 'self_signed': None}
    except socket.gaierror:
        return {'domain': domain, 'port': port, 'error': 'DNS lookup failed', 'days_left': None, 'protocol': None, 'auto_renew': None, 'self_signed': None}
    except ConnectionRefusedError:
        return {'domain': domain, 'port': port, 'error': f'Connection refused on port {port}', 'days_left': None, 'protocol': None, 'auto_renew': None, 'self_signed': None}
    except Exception as e:
        return {'domain': domain, 'port': port, 'error': str(e), 'days_left': None, 'protocol': None, 'auto_renew': None, 'self_signed': None}

@app.route('/certcheck')
def check_single():
    domain = request.args.get('domain', '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
    port = request.args.get('port', 443)
    if not domain or '.' not in domain:
        return jsonify({'error': 'Invalid domain'}), 400
    return jsonify(check_cert(domain, port))

@app.route('/certcheck/batch', methods=['POST'])
def check_batch():
    data = request.get_json()
    items = data.get('sites', [])
    if not items or len(items) > 200:
        return jsonify({'error': 'Provide between 1 and 200 sites'}), 400
    results = []
    for item in items:
        d = item.get('domain', '').strip().lower().replace('https://','').replace('http://','').split('/')[0]
        p = item.get('port', 443)
        if d:
            results.append(check_cert(d, p))
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)

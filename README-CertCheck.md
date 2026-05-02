# How the Certificate Checker Appication was built

## Resoources used by the application

* Python script (Flask) acting as an API that returns details about a sites Certificate, this script is stored on the TGA nginx
* Nginx configuration to proxy requests between users,  HTML website, and the Python based API.
* The Imatec-NAS-TGA shared folder "webdochidden" this folder is assoicated by NFS to the /mnt dir of the imatec-nginx-tga proxy


This all or the purpose of being able to tell you if a websites certificate is about to expire

## configure the imatec-nas-tga webdocshidden for NFS and files

* webdocshidden should already have a NFS export configured -0 and the imatec-nginx-tga system shulod already have it mounted at /mnt, and then linked as a dir into the nginx webserver.
* create  subfolder called **certcheck**, and paste both the sitestocheck.csv and the index.html into this location. this will then be presented as a webpage at https://certcheck.imatec.co.nz via the nginx's web server.


## add certcheck host to DNS
in 1st domains imatec.co.nz point as a CNAME certcheck to tga.imatec.co.nz (to) 119.224.63.190) (which port forwards to nginx)
inside the FW DNS (imatec.co.nz) as CNAME certcheck to imatec-nginx-tg.imatec.local  (this so the valid certificat is applied)


## add nginx records to the TGA based nginx

```bash
ssh kissadmin@imatec-nginx-tg.imatec.local
```
Only do this bit ONNCE - if the imatec.co.nz file already exists then do not do this, these are the steps requireewd to create the imatec.co.nz file

```bash
 cd /etc/nginx/sites-available/
 #create the imatec conf file
 touch imatec.co.nz

#create a simlink between the source file in 'available' to the site-enabled dir
sudo ln -s /etc/nginx/sites-available/imatec.co.nz /etc/nginx/sites-enabled
```



start with a basic http link to the default nginx site - this is mostllikely the RMM site since that wshuld be configured as default

* this is not the production code - but just lest you test the proxy configuration is working

```bash
cd /etc/nginx/sites-available
sudo nano imatec.co.nz
```

```bash
server {
    listen 80 ;
    server_name certcheck.imatec.co.nz;
    root /var/www/html;
    index index.html;
}


```

### enable nginx configuration and test

```bash
sudo nginx -t

#and if the above worked then enable it
sudo systemctl reload nginx
```

try visiting (ands the defaul/rmm site should display)

```bash
http://certcheck.imatec.co.nz
```

### Configure certbot to create and renew ssl certificates for this site

```bash
sudo certbot --nginx -d certcheck.imatec.co.nz
```

And edit the imatec.co.nz fil again: adding in allows for specific site, and deny all so that user from in side our network can use the app - and only specific locations elsewhere can

and if the above worked then reload nginx again - to be sure

```bash
sudo systemctl reload nginx
```
Check the <https://certcheck.imatec.co.nz> and this should now present a secure version of the defauly site.
the relevant nginx config (in imatec.co.nz) should look like

```bash
server {
    server_name certcheck.imatec.co.nz;
#    root /opt/certcheck/static;
# the site is actually on the TGS NAS\webdocshiiden share, and is mounted via NFS
# this allows the sitestocheck.csv to be easily edited/updated
    root /mnt/webdocshidden/certcheck;
    index index.html;

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/certcheck.imatec.co.nz/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/certcheck.imatec.co.nz/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot


location /certcheck {
  # Optional: restrict to LAN only
    # allow 192.168.0.0/16;
    # deny all;


       # ── Internal access only ──────────────────────────────
        allow 127.0.0.0/8;       # localhost
        allow 10.0.0.0/8;        # RFC1918 class A
        allow 172.16.0.0/12;     # RFC1918 class B
        allow 192.168.0.0/16;    # RFC1918 class C
        allow 108.128.247.33; # Yo Deck serers
        allow 52.210.76.69;  #Yo Deck Servers
        allow 222.153.39.200;   # SEan Home
        allow 161.29.171.101;

        allow 125.236.231.136;  # imatec FW for Yodeck
        allow 119.224.63.190;  #tga fw for yodeck
        #reapply this below when you want to disable access from the wider world
                deny all;                # block everything else
        # ─────────────────────────────────────────────────────





    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 30s;

    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
}
    # Serve the webpage itself
#    location /certcheck-ui {
#        alias /opt/certcheck/static/;
#        index index.html;
#    }

}



server {
    if ($host = certcheck.imatec.co.nz) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    server_name certcheck.imatec.co.nz;
    return 404; # managed by Certbot


}
```

change the line  of  ```root /var/www/html;```  to ```/mnt/webdocshidden/certcheck``` this will redirect the site to the actual website rather than the default site we tested on.


add a location direction to certcheck python that will run on the nginx. we will try passing this at the root later. this needs to be added within and at the end of the 443 (SSL) server definition

```bash
    location /certcheck {
    # Optional: restrict to LAN only
        # allow 192.168.0.0/16;
        # deny all;

        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;

        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type";

    }


```

```bash
sudo nginx -t

#and if the above worked then enable it
sudo systemctl reload nginx
```


## install python script

install python and dependancies

```bash
#sudo apt install python3-pip
apt install python3.12-venv
sudo python3.12 -m venv /opt/certcheck/venv
sudo /opt/certcheck/venv/bin/pip install flask flask-cors

#verify that flask is installed
/opt/certcheck/venv/bin/python -c "import flask; print(flask.__version__)"

```

create the python app  ```sudo nano /opt/certcheck/app.py```

and past the below in it

```python
import ssl
import socket
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def check_cert(domain):
    try:
        ctx = ssl.create_default_context()
        conn = socket.create_connection((domain, 443), timeout=10)
        with ctx.wrap_socket(conn, server_hostname=domain) as s:
            cert = s.getpeercert()

        expiry = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_left = (expiry - now).days

        issuer = dict(x[0] for x in cert.get('issuer', []))
        subject = dict(x[0] for x in cert.get('subject', []))

        return {
            'domain': domain,
            'expiry': expiry.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'days_left': days_left,
            'issuer': issuer.get('organizationName', '—'),
            'common_name': subject.get('commonName', domain),
            'error': None
        }
    except ssl.SSLCertVerificationError as e:
        return {'domain': domain, 'error': f'SSL verification failed: {e}', 'days_left': None}
    except socket.timeout:
        return {'domain': domain, 'error': 'Connection timed out', 'days_left': None}
    except socket.gaierror:
        return {'domain': domain, 'error': 'DNS lookup failed', 'days_left': None}
    except Exception as e:
        return {'domain': domain, 'error': str(e), 'days_left': None}

@app.route('/certcheck')
def check_single():
    domain = request.args.get('domain', '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
    if not domain or '.' not in domain:
        return jsonify({'error': 'Invalid domain'}), 400
    return jsonify(check_cert(domain))

@app.route('/certcheck/batch', methods=['POST'])
def check_batch():
    data = request.get_json()
    domains = data.get('domains', [])
    if not domains or len(domains) > 200:
        return jsonify({'error': 'Provide between 1 and 200 domains'}), 400
    results = [check_cert(d.strip().lower().replace('https://','').replace('http://','').split('/')[0]) for d in domains if d.strip()]
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```

###

run the python script int he background as service. ```sudo nano /etc/systemd/system/certcheck.service```

```ini
[Unit]
Description=SSL Certificate Checker API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/certcheck
ExecStart=/opt/certcheck/venv/bin/python /opt/certcheck/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Now enable that service

```bash
sudo systemctl daemon-reload
sudo systemctl enable certcheck
sudo systemctl start certcheck
```

## install HTML webpage

you will need to create the static dir
cd /opt/certcheck/
sudo mkdir static

use winscp to copy the html to /opt/certcheck/static/index.html

## test the installation

<https://certcheck.imatec.co.nz/certcheck?domain=example.com> should reply with something like

```json
{"common_name":"example.com","days_left":79,"domain":"example.com","error":null,"expiry":"2026-07-01T21:24:46Z","issuer":"CLOUDFLARE, INC."}
```

and then t3est the actual web aplication <https://certcheck.imatec.co.nz>

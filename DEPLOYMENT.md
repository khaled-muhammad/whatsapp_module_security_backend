# Nginx & Gunicorn Deployment Guide

This guide describes how to deploy the Security Backend application using Nginx as a reverse proxy and Gunicorn as the application server.

## 1. Prerequisites

Update your system and install the necessary packages.

```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx
```

## 2. Project Setup

Assuming your project is located at `/path/to/security_backend`.
Pass into the directory and create a virtual environment:

```bash
cd /path/to/security_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

> **Note:** `gunicorn` is not in the default requirements, so it must be installed manually.

## 3. Gunicorn Systemd Service

Create a systemd service file to manage the Gunicorn process.

**File:** `/etc/systemd/system/security_backend.service`

```ini
[Unit]
Description=Gunicorn instance to serve Security Backend
After=network.target

[Service]
# User running the application (change 'your_user' to actual username)
User=your_user
Group=www-data

# Path to the application root
WorkingDirectory=/path/to/security_backend
Environment="PATH=/path/to/security_backend/venv/bin"

# Environment Variables (Ensure these match your config)
Environment="SECURITY_PORT=5501"
Environment="SECURITY_HOST=0.0.0.0"

# Gunicorn Command
# -w 4: 4 worker processes
# -b 127.0.0.1:5501: Bind to localhost on port 5501
ExecStart=/path/to/security_backend/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5501 app:app

[Install]
WantedBy=multi-user.target
```

### Start and Enable the Service

```bash
sudo systemctl start security_backend
sudo systemctl enable security_backend
sudo systemctl status security_backend
```

## 4. Nginx Configuration

Create an Nginx server block to proxy requests to Gunicorn.

**File:** `/etc/nginx/sites-available/security_backend`

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        proxy_pass http://127.0.0.1:5501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/security_backend/static;
        expires 30d;
    }
}
```

### Enable Nginx Config

```bash
sudo ln -s /etc/nginx/sites-available/security_backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 5. SSL / HTTPS (Optional but Recommended)

Secure your deployment using Certbot (Let's Encrypt).

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain_or_ip
```

Follow the prompts to redirect HTTP to HTTPS.

---

## Troubleshooting

- **Check Gunicorn logs:** `sudo journalctl -u security_backend`
- **Check Nginx logs:** `sudo tail -f /var/log/nginx/error.log`

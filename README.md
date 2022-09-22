# solar-monitor

## Installation on Raspberry Pi

Install python requirements

```
sudo pip3 install -r requirements.txt
```

Install NGinx

```
sudo apt-get install nginx
```

Configure Nginx

Either create or modify the file `/etc/nginx/sites-enabled/default` with:

```
server {
    listen 80;
    server_name example.org;
    access_log  /var/log/nginx/example.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
  }
```

# solar-monitor

## Installation on Raspberry Pi

### If a new OS

Check the system is up to date:
```
sudo apt update
sudo apt upgrade
```

Remove apache

```
sudo apt remove apache2
```

### Install code

Install python requirements

```
sudo pip3 install virtualenv
virtualenv venv
source venv/bin/activate
git clone https://github.com/zemogle/solar-monitor.git
cd solar-monitor
pip install -r requirements.txt
```

If `pip` is not installed, install with `sudo apt install python3-pip`

### Install Nginx

```
sudo apt install nginx
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

You can test it is working with `sudo systemctl start nginx`

We will use `systemd` to manage starting the site up on reboot. In the folder:

```
/usr/lib/systemd/system
```

create a file called `solarmonitor.service` and add this to it:

```
[Unit]
Description=Solar Monitor
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/solar-monitor
ExecStart=/home/pi/venv/bin/gunicorn app:app &

[Install]
WantedBy=multi-user.target
```

We already have a `gunicorn_config.py` file which sets the port and number of workers in this project.

Start the service with `sudo systemctl start solarmonitor.service` and add it to `systemd` with:

```
sudo systemctl enable solarmonitor.service
```

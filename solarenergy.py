import requests
import secret_values as secrets
from datetime import datetime, timedelta
from base64 import b64encode
import json
import time
import colorsys
import argparse
import time

import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

BASEURL = "https://pv.inteless.com"

resource = f"{BASEURL}/oauth/token"
currentstats = f"{BASEURL}/api/v1/plant/energy/35186/flow?date="
daystats = f"{BASEURL}/api/v1/plant/energy/35186/day?lan=en&id=35186&date="

def auth_sunsynk():
    r = requests.post(resource, json={"username": secrets.username,"password": secrets.password,"grant_type": "password"})
    if r.status_code == 200 and r.json()['msg'] == 'Success':
        return r.json()['data']['access_token']
    else:
        return False

def stats_sunsynk(token):
    headers = {'Authorization': f'Bearer {token}'}
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        r = requests.get(currentstats+today, headers=headers)
    except requests.exceptions.ConnectionError:
        logging.error('Too many connections')
        return {'battery':0, 'grid':0,'export':0}
    logging.info(f"Battery - {r.json()['data']['soc']} %")
    logging.info(f"Grid Use - {r.json()['data']['gridOrMeterPower']} W")
    return {'battery':r.json()['data']['soc'], 'grid':r.json()['data']['gridOrMeterPower']/1000,'export':r.json()['data']['toGrid']}


def auth_octopus():
    today = datetime.utcnow()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    baseurl = f"https://api.octopus.energy/v1/electricity-meter-points/{secrets.octopus_mpan}/meters/{secrets.octopus_serial}/consumption/"
    total = f"{baseurl}?period_from={yesterday}T00:00:00&group_by=day"
    r = requests.get(total, auth=(secrets.octopus_key,''))
    if not r.status_code == 200:
        return False
    try:
        logging.info(f"Yesterday export - {r.json()['results'][0]['consumption']} KWh")
        return r.json()['results'][0]['consumption']
    except IndexError:
        return "API error"

def save_tokens(token, refresh_token):
    with open('token.json','w') as fp:
        data = {'token':token, 'refresh' : refresh_token}
        fp.write(json.dumps(data))
    return

def auth_enphase(key=None, refresh_token=None):
    if not key and not refresh_token:
        return False
    EBASEURL = "https://api.enphaseenergy.com/oauth"
    authurl = f"{EBASEURL}/authorize?response_type=code&client_id={secrets.enphase_client_id}&redirect_uri=https://www.zemogle.net"

    message = f'{secrets.enphase_client_id}:{secrets.enphase_client_secret}'
    message_bytes = message.encode('ascii')
    authcode = b64encode(message_bytes)
    m = authcode.decode('ascii')
    headers = {'Authorization': f'Basic {m}'}
    if refresh_token:
        url = f"{EBASEURL}/token?grant_type=refresh_token&refresh_token={refresh_token}"
    else:
        url = f"{EBASEURL}/token?grant_type=authorization_code&redirect_uri=https://www.zemogle.net&code={key}"
    r = requests.post(url, headers=headers)
    if not r.status_code == 200:
        return False
    token = r.json()['access_token']
    refresh_token = r.json()['refresh_token']
    if token and refresh_token:
        save_tokens(token, refresh_token)
    return {'token':token, 'refresh' : refresh_token}

def get_enphase_tokens():
    with open('token.json','r') as fp:
        data = json.loads(fp.read())
    return data

def enphase_summary(token):
    headers = {'Authorization': f'Bearer {token}'}
    summaryurl = f"https://api.enphaseenergy.com/api/v4/systems/{secrets.enphase_system_id}/summary?key={secrets.enphase_api_key}"
    r = requests.get(summaryurl, headers=headers)
    if r.status_code != 200:
        logging.error(r.content)
        return {'today':"N/A", 'current' :"Rate limited" }
    logging.info(f"Production today {r.json()['energy_today']/1000:.2f} KWh")
    logging.info(f"Current power {r.json()['current_power']/1000:.2f} KW")
    return {'today':r.json()['energy_today']/1000, 'current' : r.json()['current_power']/1000}

def enphase_aggregate(token):
    headers = {'Authorization': f'Bearer {token}'}
    summaryurl = f"https://api.enphaseenergy.com/api/v4/systems/{secrets.enphase_system_id}/telemetry/production_micro?key={secrets.enphase_api_key}"
    r = requests.get(summaryurl, headers=headers)
    logging.info(r.json())
    return

def summary(panels=False):
    tokens = get_enphase_tokens()
    sstoken = auth_sunsynk()
    if sstoken:
        battery = stats_sunsynk(sstoken)
    tokens = get_enphase_tokens()
    if panels:
        panelsummary = enphase_summary(token=tokens['token'])
        if not panelsummary:
            tokens = auth_enphase(refresh_token=tokens['refresh'])
            panelsummary = enphase_summary(token=tokens['token'])
    else:
        panelsummary = {'today':'N/A', 'current':'N/A'}
    exported = auth_octopus()
    return battery, panelsummary, exported

def display_inky():
    import inkyphat
    battery, panels, exported = summary()

    verb = ""
    if battery['export']:
        verb = "Export"
    else:
        verb = "Use"
    data = [
        f"Battery {battery['battery']} %",
        f"Grid {verb} {battery['grid']} KW",
        f"Export {exported} KWh",
        f"{datetime.now().strftime('%-d %b %H:%M')}"
    ]

    inkyphat.set_colour("black")
    inkyphat.set_border(inkyphat.BLACK)
    inkyphat.set_rotation(180)
    inkyphat.rectangle((0, 0, inkyphat.WIDTH, inkyphat.HEIGHT), fill=inkyphat.WHITE)
    font = inkyphat.ImageFont.truetype(inkyphat.fonts.FredokaOne, 16)

    offset_x, offset_y = 10, 0
    for text in data:
        inkyphat.text((offset_x, offset_y), text, inkyphat.BLACK, font=font)
        offset_y += font.getlength(text)[1] + 2
    inkyphat.show()
    return

def battery_display(battery):
    rainbow = False
    number = round(battery['battery']/100 * 32)

    if battery['export'] and battery['grid'] > 0.5:
        rainbow = True
        colour = 0
    else:
        if battery['battery'] < 20 or (battery['battery'] < 50 and not battery['export'] and battery['grid'] < 0.1):
            colour = (231, 76, 60)
        elif battery['battery'] < 30 and not battery['export'] and battery['grid'] < 0.1:
            colour = (241, 196, 15)
        elif battery['battery'] < 60:
            colour = (93, 173, 226)
        elif battery['battery'] < 80:
            colour = (118, 215, 196)
        else:
            colour = (34, 153, 84)

    return number, colour, rainbow

def unicorn():
    import unicornhat as uh
    while True:
        sstoken = auth_sunsynk()
        if sstoken:
            battery = stats_sunsynk(sstoken)
        number, colour, rainbow = battery_display(battery)
        if not rainbow:
            r,g,b = colour
        uh.set_layout(uh.PHAT)
        uh.brightness(0.5)
        spacing = 360.0 / 16.0
        uh.clear()
        for x in range(8):
            if rainbow:
                offset = x * spacing
                h = ((colour + offset) % 360) / 360.0
                r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
            for y in range(4):
                uh.set_pixel(x, y, r, g, b)
                if (x*4 +y) == number:
                    break
            else:
                continue
            break
        uh.show()
        time.sleep(600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Battery and Power monitor')
    parser.add_argument('-i', '--inky', action='store_true', help='eInk display')
    parser.add_argument('-u', '--unicorn', action='store_true', help='Unicorn pHat display')
    parser.add_argument('-t', '--term', action='store_true', help='Terminal output only')
    args = parser.parse_args()
    if args.term:
        summary()
    elif args.inky:
        display_inky()
    elif args.unicorn:
        unicorn()

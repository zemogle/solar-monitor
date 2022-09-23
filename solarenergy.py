import requests
import secret_values as secrets
from datetime import datetime, timedelta
from base64 import b64encode
import json

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

def stats_sunsynk(headers):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = requests.get(currentstats+today, headers=headers)
    logging.info(f"Battery - {r.json()['data']['soc']} %")
    logging.info(f"Grid Use - {r.json()['data']['gridOrMeterPower']} W")
    return {'battery':r.json()['data']['soc'], 'grid':r.json()['data']['gridOrMeterPower']}


def auth_octopus():
    today = datetime.utcnow()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    baseurl = f"https://api.octopus.energy/v1/electricity-meter-points/{secrets.octopus_mpan}/meters/{secrets.octopus_serial}/consumption/"
    total = f"{baseurl}?period_from={yesterday}T00:00:00&group_by=day"
    r = requests.get(total, auth=(secrets.octopus_key,''))
    if not r.status_code == 200:
        return False
    try:
        logging.info(f"Yesterday export - {r.json()['results'][1]['consumption']} KWh")
        return r.json()['results'][1]['consumption']
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
        return False
    logging.info(f"Production today {r.json()['energy_today']/1000:.2f} KWh")
    logging.info(f"Current power {r.json()['current_power']/1000:.2f} KW")
    return {'today':r.json()['energy_today']/1000, 'current' : r.json()['current_power']/1000}

def enphase_aggregate(token):
    headers = {'Authorization': f'Bearer {token}'}
    summaryurl = f"https://api.enphaseenergy.com/api/v4/systems/{secrets.enphase_system_id}/telemetry/production_micro?key={secrets.enphase_api_key}"
    r = requests.get(summaryurl, headers=headers)
    logging.info(r.json())
    return

def summary():
    tokens = get_enphase_tokens()
    sstoken = auth_sunsynk()
    if sstoken:
        headers = {'Authorization': f'Bearer {sstoken}'}
        battery = stats_sunsynk(headers)
    tokens = get_enphase_tokens()
    panels = enphase_summary(token=tokens['token'])
    if not panels:
        tokens = auth_enphase(refresh_token=tokens['refresh'])
        panels = enphase_summary(token=tokens['token'])
    exported = auth_octopus()
    return battery, panels, exported

def display_inky():
    import inkyphat
    battery, panels, exported = summary()

    data = [
        f"Battery {battery['battery']} %",
        f"Grid Use {battery['grid']} KW",
        f"Current {panels['current']} KW",
        f"Total {panels['today']} KWh",
        f"Export {exported} KWh"
    ]

    inkyphat.set_colour("black")
    inkyphat.set_border(inkyphat.BLACK)
    inkyphat.set_rotation(180)
    inkyphat.rectangle((0, 0, inkyphat.WIDTH, inkyphat.HEIGHT), fill=inkyphat.WHITE)
    font = inkyphat.ImageFont.truetype(inkyphat.fonts.FredokaOne, 14)

    offset_x, offset_y = 10, 0
    for text in data:
        inkyphat.text((offset_x, offset_y), text, inkyphat.BLACK, font=font)
        offset_y += font.getsize(text)[1] + 2
    inkyphat.show()
    return


if __name__ == '__main__':
    display_inky()

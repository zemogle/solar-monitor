import requests
import secrets
from datetime import datetime, timedelta
from base64 import b64encode

# ENPHASE_APP_KEY = os.environ['ENPHASE_APP_KEY']
# ENPHASE_USER_ID = os.environ['ENPHASE_USER_ID']
# ENPHASE_SYSTEM_ID = os.environ['ENPHASE_SYSTEM_ID']


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
    print(f"Battery - {r.json()['data']['soc']} %")
    print(f"Grid Use - {r.json()['data']['gridOrMeterPower']} W")
    return


def auth_octopus():
    today = datetime.utcnow()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    baseurl = f"https://api.octopus.energy/v1/electricity-meter-points/{secrets.octopus_mpan}/meters/{secrets.octopus_serial}/consumption/"
    total = f"{baseurl}?period_from={yesterday}T00:00:00&group_by=day"
    r = requests.get(total, auth=(secrets.octopus_key,''))
    print(f"Yesterday export - {r.json()['results'][1]['consumption']} KWh")
    return

def auth_enphase(refresh_token=None):
    BASEURL = "https://api.enphaseenergy.com/oauth"
    authurl = f"{EBASEURL}/authorize?response_type=code&client_id={secrets.enphase_client_id}&redirect_uri=https://www.zemogle.net"

    message = f'{secrets.enphase_client_id}:{secrets.enphase_client_secret}'
    message_bytes = message.encode('ascii')
    authcode = b64encode(message_bytes)
    m = authcode.decode('ascii')
    headers = {'Authorization': f'Basic {m}'}
    if refresh_token:
        url = f"{EBASEURL}/token?grant_type=refresh_token&refresh_token={refresh_token}"
    else:
        url = f"{EBASEURL}/token?grant_type=authorization_code&redirect_uri=https://www.zemogle.net&code=h5kRbI"
    r = requests.post(url, headers=headers)
    token = r.json()['access_token']
    refresh_token = r.json()['refresh_token']
    return token, refresh_token

def enphase_summary(token):
    headers = {'Authorization': f'Bearer {token}'}
    summaryurl = f"https://api.enphaseenergy.com/api/v4/systems/{secrets.enphase_system_id}/summary?key={secrets.enphase_api_key}"
    r = requests.get(summaryurl, headers=headers)
    print(f"Production today {r.json()['energy_today']/1000:.2f} KWh")
    print(f"Current power {r.json()['current_power']/1000:.2f} KW")
    return

def main():
    token = auth_sunsynk()
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        stats_sunsynk(headers)
    enphase_summary(token=secrets.enphase_token)
    auth_octopus()

if __name__ == '__main__':
    main()

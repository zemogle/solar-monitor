from flask import Flask, render_template, request, url_for, flash, redirect
from solarenergy import auth_enphase, summary
from secret_values import enphase_client_id

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

enphase_key = ''

@app.route('/')
def index():
    battery, panels, exported = summary(panels=True)
    # if not panels:
    #     return redirect(url_for('set_key'))
    return render_template('index.html', battery=battery, panels=panels, exported=exported)

@app.route('/demo/')
def demo():
    # battery, panels, exported = summary()
    # if not panels:
    #     return redirect(url_for('set_key'))
    return render_template('index.html', battery={"battery":10, "grid":100,'export':True}, panels={"today":300,"current":0.1}, exported=4.1)

@app.route('/key/', methods=('GET', 'POST'))
def set_key():
    global enphase_key
    print(enphase_key)
    EBASEURL = "https://api.enphaseenergy.com/oauth"
    authurl = f"{EBASEURL}/authorize?response_type=code&client_id={enphase_client_id}&redirect_uri=https://www.zemogle.net"

    if request.method == 'POST':
        key = request.form['key']

        if not key:
            flash('Key is required!')
        else:
            enphase_key = key
            auth_enphase(key=key)
            return redirect(url_for('index'))
    return render_template('form.html',link=authurl)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

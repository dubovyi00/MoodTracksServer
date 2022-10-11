from flask import Flask, request, jsonify
from datetime import datetime as dt, timezone
import time
import ephem

app = Flask(__name__)

TIMECLOCK = {
    "Night": [0, 6],
    "EarlyMorning": [6, 9],
    "LateMorning": [9, 12],
    "Midday": [12, 14],
    "Afternoon": [14, 16],
    "LateAfternoon": [16, 18],
    "EarlyEvening": [18, 20],
    "Evening": [20, 22],
    "LateEvening": [22, 24]
}


@app.route("/playlist", methods=["GET", "POST"])
def playlist():
    pass


@app.route("/weather", methods=["GET"])
def weather():
    pass


@app.route("/season", methods=["GET"])
def season():
    pass


@app.route("/timeclock", methods=["GET"])
def timeclock():
    user_time = int(request.args["time"]) # unix-дата в UTC
    user_tz = request.args["tz"] # сдвиг часового пояса "hhmm"
    rez = {}

    current_time = dt.now(timezone.utc)
    current_time_hours = current_time.hour
    current_time_unix = int(time.mktime(current_time.timetuple()))
    delta_tz = int(user_tz[0:2]) * 60 * 60 + int(user_tz[2:4]) * 60
    offset = 600
    
    if abs(user_time - current_time_unix) < offset:
        current_time_unix += delta_tz
        current_time_hours = dt.fromtimestamp(current_time_unix).hour
        for tn, tc in TIMECLOCK.items():
            if tc[0] <= current_time_hours < tc[1]:
                rez["status"] = "OK!"
                rez["timeclock"] = tn
                resp = jsonify(rez)
                resp.status_code = 200
    else:
        rez["status"] = "Invalid time!"
        resp = jsonify(rez)
        resp.status_code = 400

    return resp 


@app.route("/action", methods=["GET"])
def action():
    pass

if __name__ == "__main__":
    app.run(debug=True)
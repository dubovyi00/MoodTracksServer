from datetime import datetime as dt, timezone
import time
import json
from operator import itemgetter
from uuid import uuid4
import requests as rq

from flask import Flask, request, jsonify, send_file
from yandex_music import Client
from mariadb import connect, Error
import stun
from pyowm import OWM

db = connect(
    host="212.193.49.210",
    user="mood_tracks",
    password="u8u78y7au828",
    database="mood_tracks"
)
db.autocommit = False

app = Flask(__name__)

ym = Client("y0_AgAAAAAmuxbHAAG8XgAAAADPAh7kUcBPun1yTdCmZ5c5KEfAUdVHzsg")
ym.init()

owm = OWM('c691d1db53c23015b7c0169398fdda81')
weather_mgr = owm.weather_manager()

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


@app.route("/api/playlist", methods=["GET", "POST"])
@app.route("/api/playlist/<int:id>", methods=["GET", "DELETE"])
def playlist(id=0):
    if id:
        if request.method == "DELETE":
            pass
        else:
            sql = "SELECT `name` FROM `playlist` WHERE `playlist_id` = %s"
            cur = db.cursor(dictionary=True)
            cur.execute(sql, (id,))
            name = cur.fetchone()['name']

            sql = (
                "SELECT  `ym_album_id` AS album_id, `ym_track_id` AS track_id, `artist`, `album`, "
                "`title`, `duration`, `image_url` FROM `track` WHERE `playlist_id` = %s"
            )
            cur = db.cursor(dictionary=True)
            cur.execute(sql, (id,))
            rez = {
                "err": None,
                "data": {
                    "name": name,
                    "tracks": cur.fetchall()
                }
            }
    else:
        if request.method == "POST":
            key = request.json["key"]
            data = request.json["data"]
            
            with open("map.json") as f:
                mood_map = json.loads(f.read())

            station = mood_map[key][data] 
            tracks = ym.rotor_station_tracks(station)

            sql = (
                "INSERT INTO `playlist` (`user_id`, `name`, `image_url`) "
                "VALUES (%s, %s, %s) "
            )
            cur = db.cursor()
            cur.execute(sql, (
                "123e4567-e89b-12d3-a456-426655440000", 
                "test", 
                tracks['sequence'][0]['track']['cover_uri']
            ))
            db.commit() 
            playlist_id = cur.lastrowid

            playlist = []
            for tr in tracks["sequence"]:
                print(tr['track'])
                track_id = int(tr['track']['id'])
                album_id = tr['track']['albums'][0]['id']
                artist = ', '.join([ artist["name"] for artist in tr['track']['artists'] ])
                album = tr['track']['albums'][0]['title']
                title = tr['track']['title']
                duration = int(tr['track']['duration_ms'] / 1000)
                image_url = tr['track']['cover_uri']

                sql = (
                    "INSERT INTO `track` (`track_id`, `playlist_id`, `ym_album_id`, `ym_track_id`, "
                    "`artist`, `album`, `title`, `duration`, `image_url`) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                params = (
                    str(uuid4()),
                    playlist_id,
                    track_id,
                    album_id,
                    artist,
                    album,
                    title,
                    duration,
                    image_url
                )
                cur = db.cursor()
                cur.execute(sql, params)
                db.commit() 
            print(playlist_id)
            rez = {"err": None, "data": {"id": playlist_id}}
        else:
            sql = "SELECT `playlist_id` AS id, `name`, `image_url` FROM `playlist`"
            cur = db.cursor(dictionary=True)
            cur.execute(sql)
            rez = {
                "err": None,
                "data": {
                    "playlists": cur.fetchall()
                }
            }
    resp = jsonify(rez)
    resp.status_code = 200 if not rez["err"] else 400
    return resp

@app.route("/api/track/<int:album_id>/<int:track_id>")
def track(album_id, track_id):
    tr = f"{track_id}:{album_id}"
    try:
        downloads = ym.tracks_download_info(tr)
        downloads.sort(key=itemgetter('bitrate_in_kbps'), reverse=True)
        best_quality = downloads[0]
        fname = tr.replace(':', '.') + '.' + best_quality['codec']
        ym.tracks([tr])[0].download(
            fname,
            best_quality['codec'],
            best_quality['bitrate_in_kbps']
        )
    except Exception:
        rez = {}
        rez["error"] = {"code": 2, "message": "неверные/невалидные параметры"}
        rez["data"] = None
        resp = jsonify(rez)
        resp.status_code = 400
        return resp
    else:
        return send_file(fname)

@app.route("/api/weather", methods=["GET"])
def weather():
    ip = request.remote_addr
    if ip == "127.0.0.1":	
        server_stun = stun.get_ip_info()
        place = rq.get('http://api.sypexgeo.net/ymFwP/json/'+server_stun[1]).json()
    else:
        place = rq.get('http://api.sypexgeo.net/ymFwP/json/'+ip).json()
    place_name = place["city"]["name_en"]
    
    observation = weather_mgr.weather_at_place(place_name)

    rez = {
        "error": None,
        "data": {
            "weather": observation.weather.detailed_status.capitalize()
        }
    }
    resp = jsonify(rez)
    resp.status_code = 200
    return resp

@app.route("/api/season", methods=["GET"])
def season():
    pass


@app.route("/api/timeclock", methods=["GET"])
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
                rez = {
                    "error": None,
                    "data": {
                        "timeclock": tn
                    }
                }
                
                resp = jsonify(rez)
                resp.status_code = 200
    else:
        rez = {
            "error": {
                "code": 2, 
                "message": "неверные/невалидные параметры"
            },
            "data": None
        }
        resp = jsonify(rez)
        resp.status_code = 400

    return resp 


@app.route("/api/action", methods=["GET"])
def action():
    pass

if __name__ == "__main__":
    app.run(debug=True)
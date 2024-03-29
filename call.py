import collections
import csv
import datetime
import sqlite3

import requests
import yaml
from flask import Flask, abort, g, redirect, render_template, request, url_for

DATABASE = "database.sqlite3"

app = Flask(__name__)


# https://flask.palletsprojects.com/en/2.3.x/patterns/sqlite3/
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(_):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()


with open("campaigns.yml") as f:
    campaigns = yaml.safe_load(f)
    for key, campaign in campaigns.items():
        with open(campaign["members_file"]) as f:
            members = list(csv.DictReader(f))

            members_dict = collections.defaultdict(list)
            for mem in members:
                members_dict[mem["ocdid"]].append(mem)

            campaign["members"] = members_dict


def find_ocdids(lat, lng):
    result = requests.get(
        "https://districts.socialism.gay/v1/match.json",
        params={"lat": str(lat), "lon": str(lng)},
    )
    print(result.text)

    return result.json()["ocdids"]


@app.route("/call/")
@app.route("/call/<c>")
@app.route("/call/<c>/")
def do_call(c="contact"):
    if c not in campaigns:
        abort(404)

    if "lat" in request.args and "lng" in request.args:
        lat = request.args["lat"]
        lng = request.args["lng"]

        ocdids = find_ocdids(float(lat), float(lng))
        if not ocdids:
            return redirect(url_for("not_found"))

        return redirect(
            url_for(
                "show_representatives",
                key=c,
                ocdids=",".join(ocdids),
            )
        )

    return render_template("call.html", campaign=campaigns[c], campaigns=campaigns)


@app.route("/call/not_found/")
def not_found():
    return render_template("not_found.html")


@app.route("/call/<key>/reps/")
def show_representatives(key):
    campaign = campaigns[key]

    seen_districts = set()
    reps = campaign["reps"]
    result = []

    ocdids = request.args.get("ocdids", "").split(",")

    query_db(
        "INSERT INTO visits (timestamp, ip, source, campaign, ocdids) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            datetime.datetime.now().isoformat(),
            request.headers.get("X-Forwarded-For", request.remote_addr),
            request.cookies.get("src", ""),
            key,
            ",".join(ocdids),
        ),
    )
    get_db().commit()

    for rep in reps:
        if rep["ocdid"] == "theirs":
            if "ocdid_prefix" in rep:
                dists = [i for i in ocdids if i.startswith(rep["ocdid_prefix"])]

            else:
                dists = ocdids
        else:
            dists = [rep["ocdid"]]

        for dist in dists:
            if dist in seen_districts:
                continue

            seen_districts.add(dist)

            for member in campaign["members"][dist]:
                rep_note = None
                if rep["rep_note"]:
                    for note in member["note"].split("|"):
                        if note in campaign["notes"]:
                            rep_note = campaign["notes"][note]

                note = rep.get("note")

                member["clean_phone"] = "".join(
                    x for x in member["phone"] if x.isnumeric()
                )
                result.append((rep, member, note, rep_note))

    return render_template(
        "legislators.html", key=key, campaign=campaign, result=result
    )


@app.route("/call/click/")
def click():
    query_db(
        "INSERT INTO clicks (timestamp, ip, source, campaign, tag, ocdid) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.datetime.now().isoformat(),
            request.headers.get("X-Forwarded-For", request.remote_addr),
            request.cookies.get("src", ""),
            request.args.get("key"),
            request.args.get("tag"),
            request.args.get("ocdid"),
        ),
    )
    get_db().commit()

    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=8899)

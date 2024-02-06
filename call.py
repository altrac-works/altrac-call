import collections
import csv
import json

import requests
import yaml
from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)

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
def do_call(c="contact"):
    if c not in campaigns:
        abort(404)

    if "lat" in request.args and "lng" in request.args:
        lat = request.args.get("lat")
        lng = request.args.get("lng")

        ocdids = find_ocdids(float(lat), float(lng))
        if not ocdids:
            return redirect(url_for("not_found"))

        return redirect(
            url_for(
                "show_representatives",
                campaign=c,
                ocdids=",".join(ocdids),
            )
        )

    return render_template("call.html", campaign=campaigns[c], campaigns=campaigns)


@app.route("/call/not_found/")
def not_found():
    return render_template("not_found.html")


@app.route("/call/<campaign>/")
def show_representatives(campaign):
    campaign = campaigns[campaign]

    seen_districts = set()
    reps = campaign["reps"]
    result = []

    ocdids = request.args.get("ocdids").split(",")

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
                    if member["note"] in campaign["notes"]:
                        rep_note = campaign["notes"][member["note"]]

                note = rep.get("note")

                member["clean_phone"] = "".join(
                    x for x in member["phone"] if x.isnumeric()
                )
                result.append((rep, member, note, rep_note))

    return render_template("legislators.html", campaign=campaign, result=result)


app.run(debug=False, port=8899)

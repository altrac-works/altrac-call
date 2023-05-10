# ALTRAC Call Tool

* You need `libgeos-dev` on Debian sid (it at least has to be 3.10.1 or newer)
* You need `pip3 install flask requests pyyaml shapely --no-binary shapely`
* You need a Google Maps API key that is not mine lol (edit `templates/call.html`)
* `call.py` will listen on `127.0.0.1:8899`, just proxy `/call/` on your domain to this host

`campaigns.yml` will let you configure a campaign

## TODO

so many things

* change default campaign in config
* links to multiple campaigns
* Google Maps API key is a config item
* support mutliple kinds of districts instead of just sldl
* support other states

## Data

Huge props to [Redistricting Data Hub](https://redistrictingdatahub.org/) (@nonpartisan-redistricting-datahub) for the shapefiles, thank you!!!

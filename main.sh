#!/bin/bash
# developed on jq-1.7
set -e
testing=1
timestamp=${1:-2025-05-22T22:15:18Z}

rawFile="pitniki.raw.json"

if [[ ! -d models ]]; then
	echo "Ups, wrong CWD, bailing out"
	exit 1
fi
mkdir -p cache workdir
if [[ -z $testing ]] && ls workdir |& grep -q "total 0"; then
	now=$(date +%Y-%m-%d-%T)
	echo "Ups, workdir is not empty, moving away to $now/"
	mv workdir "$now"
	mkdir workdir
fi

cd workdir

# pridobi osnovne podatke
echo "Fetching base data"
if [[ -z $testing ]] || [[ ! -s $rawFile ]]; then
	nodejs ../fetcher.js ../models/pitniki.ql > "$rawFile"
fi

echo "Starting data transformations"

# pripravi id-je občin za kasnejšo rabo
# FIXME: cleanup directly or using pick, so we can skip the next step
jq '{ version, generator, osm3s, elements: [.elements | 
	while(length > 0; .[2:])[:2] |
		(.[0] | { id, lat, lon, timestamp, changeset, tags, type, version })
		+ 
		(.[1] | { obcina: .id, obcina2: (.id - 3600000000) })
	]
}' "$rawFile" > pitniki.zdruzen.json

# premakni občine pod "tags", da bo kompatibilno z geojson formatom
jq '{version, generator, osm3s, elements: [.elements[] | walk ( if type == "object" and has("tags") then .tags.obcina = .obcina end)]}' pitniki.zdruzen.json > tmptptppt; mv tmptptppt pitniki.zdruzen.json
jq '{version, generator, osm3s, elements: [.elements[] | walk ( if type == "object" and has("tags") then .tags.obcina2 = .obcina2 end)]}' pitniki.zdruzen.json > tmptptppt; mv tmptptppt pitniki.zdruzen.json

# if update mode, first compare to timestamp and potentially bail
# version=1 means new, higher means an update
if [[ -n $timestamp ]]; then
	echo "Starting comparison mode with timestamp $timestamp"
	jq --arg basestamp "$timestamp" '{ version, generator, osm3s, elements:
		[ .elements[] | select(.timestamp > $basestamp) ] 
	}' pitniki.zdruzen.json > tmptptppt; mv tmptptppt pitniki.zdruzen.json
fi

# imamo že podatke o občinah?
if [[ ! -f ../cache/obcine-id-v-ime.csv ]]; then
	nodejs ../fetcher.js ../models/obcine.ql > obcine.raw.json
	jq ".elements[] | {"id",tags: .tags.name}" obcine.raw.json |
		sed -nr '/^\s+/ { /id/ N; s,^\s+"id": ,,; s/,\n[^:]+:\s/,/p; }' > ../cache/obcine-id-v-ime.csv
	rm obcine.raw.json
fi

# popravi imena občin iz id-jev v dejansko ime
while read line; do
	id="${line%%,*}"
	name="${line#*,}"
	sed -i "s#obcina2\(.\): $id#obcina2\1: $name#" pitniki.zdruzen.json
done < ../cache/obcine-id-v-ime.csv

#  zgeneriraj manjkajoča imena iz občine in naključne številke
jq '{version, generator, osm3s, elements: [.elements[] | walk ( if type == "object" and has("tags") then (if .tags.name == null then .tags.name = .tags.obcina2 + " " + (now * 100000 % 100 |  tostring) end) end)]}' pitniki.zdruzen.json  > tmptptppt; mv tmptptppt pitniki.zdruzen.json

# pretvori v pravi geojson
../node_modules/osmtogeojson/osmtogeojson pitniki.zdruzen.json > pitniki.geojson
echo -n "Zaključena priprava podatkov, končni so v: workdir/"
if [[ -n $timestamp ]]; then
	mv pitniki.geojson pitniki.posodobljeni.geojson
	echo "pitniki.posodobljeni.geojson"
else
	echo "pitniki.geojson"
fi

# TODO: make sure empty timestamps compare falsely
# TODO: handle disused:amenity
# TODO: trigger SQL update mode?
# zaenkrat:
# - dump mjv prek plugin hacka, da so settings/extras/groupmap odprti
# - poženi tole za nov geojson (s timestampom zadnje upoštevane posodobitve)
# - ./geojson2mysql.py workdir/pitniki.posodobljeni.geojson workdir/pitniki-iz-mjv.csv
# - pri dodajanju pazi, če so kje duplikati z obstoječimi vnosi na mjv, ker je bil pri prvem uvozu upoštevan buffer zone

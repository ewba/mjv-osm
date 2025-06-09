#!/usr/bin/python
import csv
import json
import sys

liveFeatures = []

def PrepUpdate():
	global liveFeatures

	with open(sys.argv[2], newline='') as csvFile:
		reader = csv.DictReader(csvFile)
		for row in reader:
			liveFeatures.append(row)

def GetOptionalValue(tags, key):
	if key in tags:
		return tags[key] if tags[key] else ""
	else:
		return ""

GroupMap = {
	25: "Izvir",
	26: "Vodnjak",
	23: "Pipa",
	22: "Fontana",
	24: "Korito",
	21: "Pitnik",
	27: "Za avtodome",
	20: "Drugi vodni viri"
}

# NOTE: dejansko je lahko v večih skupinah
def GetGroup(tags):
	group = None

	# vrstni red je pomemben, ker so lahko prisotne vse tri oznake
	if "man_made" in tags:
		val = tags["man_made"]
		if val == "water_well":
			group = 26 # Vodnjak: man_made=water_well
		elif val == "water_tap":
			group = 23 # Pipa: man_made=water_tap

	if "amenity" in tags:
		val = tags["amenity"]
		if val == "fountain":
			group = 22 # Fontana: amenity=fountain
		elif val == "watering_place":
			group = 24 # Korito: amenity=watering_place
		# elif val == "drinking_water":
		# 	group = 21 # Pitnik: amenity=drinking_water
		elif val == "water_point":
			group = 27 # Za avtodome: amenity=water_point

	if GetOptionalValue(tags, "natural") == "spring":
		group = 25 # Izvir: natural=spring

	# kasneje, da imajo ostali prednost
	if not group and GetOptionalValue(tags, "amenity") == "drinking_water":
		group = 21 # Pitnik: amenity=drinking_water

	if not group and GetOptionalValue(tags, "drinking_water") == "yes":
		group = 20 # Drugi vodni viri: drinking_water=yes (kot zadnja, da je catchall)

	if not group:
		print("SKIPPING incompatibly tagged entry with no group match: ", tags)
		return ""
	return group

def GetGroupMap(tags):
	group = GetGroup(tags)
	if not group:
		return "";
	# meh, format() does not work, since it parses too much
	# at the same time most of the dump is static, so we still want to just insert
	return 'a:1:{i:0;s:2:"' + str(group) +'";}'

def GetDescription(tags, address):
	opombe = GetOptionalValue(tags, "description")

	pitnost = ""
	if "drinking_water:legal" in tags:
		val = tags["drinking_water:legal"]
		if val == "yes":
			pitnost = "Voda je pitna: Da, označeno<br>"
		elif val == "unsigned":
			pitnost = "Voda je pitna: Da<br>"
	elif GetOptionalValue(tags, "drinking_water") == "yes":
		pitnost = "Voda je pitna: Da<br>"
	else:
		pitnost = "Voda je pitna: Ni podatka — sporočite nam<br>"

	stran = GetOptionalValue(tags, "website")
	if stran:
		stran = "<a href='{}' target='_blank'>Spletna stran</a><br>".format(stran)

	if address:
		address = "Lokacija: " + address + "<br>"
	else:
		address = ""
	desc = "<p>{} {} {} Opombe: {}</p>".format(address, pitnost, stran, opombe)

	return desc

def GetSettings(tags):
	image = GetOptionalValue(tags, "image") or "" # url
	base = 'a:4:{s:7:"onclick";s:6:"marker";s:13:"redirect_link";s:0:"";s:14:"featured_image";'
	data = 's:{}:"{}";s:20:"redirect_link_window";s:3:"yes";'

	return base + data.format(len(image), image) + '}",'

def GetExtraFields(tags):
	osmID = tags["id"] # 'node/6521883170'
	timestamp = tags["timestamp"]
	base = 'a:7:{s:13:"spletna-stran";s:0:"";s:6:"opombe";s:0:"";s:5:"stran";s:0:"";s:5:"pitna";s:0:"";s:5:"slika";s:0:"";s:6:"osm_id";s:'
	base2 = '{}:"{}";s:13:"osm_timestamp";s:{}:"{}";'
	return base + base2.format(len(osmID), osmID, len(timestamp), timestamp) + "}"

def InsertFeature(feat):
	tags = feat["properties"]

	nextLocID = "" #lastID + 1 # ima AUTO_INCREMENT
	name = tags["name"]
	address = tags["address"] if "address" in feat else ""
	lat = feat["geometry"]["coordinates"][1]
	lon = feat["geometry"]["coordinates"][0]
	kraj = "" # ni podatka v osm, nihče ne vnaša - itak
	obcina = tags["obcina2"]
	desc = GetDescription(tags, address)
	settings = GetSettings(tags)
	groupMap = GetGroupMap(tags)
	extras = GetExtraFields(tags)

	# TODO: kaj pa embedded delimiterji v desc, extras? '"... ročno esc? SQL Quote()?
	insert = '''
INSERT INTO `wp_map_locations` (`location_title`,`location_address`,`location_animation`,`location_latitude`,`location_longitude`,`location_city`,`location_state`,`location_zoom`,`location_author`,`location_messages`,`location_settings`,`location_group_map`,`location_extrafields`)
VALUES ("{}","{}","BOUNCE","{}","{}","{}","{}","0","5",'{}','{}','{}','{}');'''.format(name, address, lat, lon, kraj, obcina, desc, settings, groupMap, extras)

	print(insert)

	# register the point for the appropriate map
	# use a temporary scratch field somewhere
	# NOTE: the plugin seems to expect a specific order to the structure,
	#   so currently manual additions fail to register. Sort of a feature.
	#   Perhaps we should be prepending instead.
	grr='''
UPDATE `wp_map_locations`
SET `location_author` = (SELECT REGEXP_REPLACE(`map_locations`,'^a:([0-9]+):.*$','\\\\1') FROM `wp_create_map` WHERE `map_id`=7)
WHERE `location_id` = 1;'''
	print(grr)
	grr='''
UPDATE `wp_create_map`
SET `map_locations` = REGEXP_REPLACE(`map_locations`, '^a:[0-9]+:(.*);}$',
	CONCAT(
		'a:', 
		(SELECT `location_author` FROM `wp_map_locations` WHERE `location_id` = 1) + 1,
		':\\\\1;i:',
		(SELECT `location_author` FROM `wp_map_locations` WHERE `location_id` = 1),
		';s:4:"',
		(SELECT max(`location_id`) FROM `wp_map_locations`),
		'";}'
	)
)
WHERE `map_id` = 7;'''
	print(grr)
	# lenobno predvideva, da id nikoli ne bo šel čez 9999

###### MAIN

updateMode = False
if len(sys.argv) < 2:
	print("no input file passed!")
	print("USAGE: geojson2mysql.py source.geojson [currentState.csv]")
	exit(1)

features = None
with open(sys.argv[1] , "r" ) as f:
	features = json.load(f)["features"]

if not features:
	print("bad input file, expecting a geojson!")
	exit(2)

if len(sys.argv) > 2:
	print("Starting update mode")
	updateMode = True
	PrepUpdate()

for feat in features:
	InsertFeature(feat)

# TODO: naši imajo v opisu "Lokacija: ..." - premaknemo pod opombe, ohranimo? Zdaj is osm dodamo naslov, če obstaja

# 38",,,"BOUNCE","46.4980586","13.7164847","Rateče",,,,"0","5","<p>Lokacija: Trg v centru, Rateče</p><p>Voda je pitna: Da, označeno<br>Opombe: </p>","a:4:{s:7:""onclick"";s:6:""marker"";s:13:""redirect_link"";s:0:"""";s:14:""featured_image"";s:67:""https://manjjevec.si/wp-content/uploads/2024/07/ratece-300x225.webp"";s:20:""redirect_link_window"";s:3:""yes"";}","a:1:{i:0;s:2:""24"";}","a:5:{s:13:""spletna-stran"";s:0:"""";s:6:""opombe"";s:0:"""";s:5:""stran"";s:0:"""";s:5:""pitna"";s:0:"""";s:5:""slika"";s:0:"""";}"

# "12","Kobarid 84","",,,"BOUNCE","13.4148101","46.2154002","","Kobarid",,,"0","5","<p>  Opombe: </p>","","a:1:{i:0;s:2:"21";}","a:7:{s:13:"spletna-stran";s:0:"";s:6:"opombe";s:0:"";s:5:"stran";s:0:"";s:5:"pitna";s:0:"";s:5:"slika";s:0:"";s:6:"osm_id";s:15:"node/6521883170";s:13:"osm_timestamp";s:20:"2019-06-04T19:11:29Z";}");

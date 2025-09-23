#!/usr/bin/python
import csv
import sys

# first download same type of csv export as for the updater script

with open(sys.argv[1], newline='') as csvFile:
	reader = csv.DictReader(csvFile)
	for row in reader:
		legal = "TRUE" if "Da, označeno" in row["Message"] else ""
		print('''"","","{}","",{},{},"{}","","In case of data issues, please let us know at manjjevec@ocistimo.si","","","","","FALSE","{}","","","","TRUE","Outdoor Space","FALSE","FALSE","FALSE","FALSE","SI","",""'''.format(row["State"] if row["State"] else row["City"], row["Latitude"], row["Longitude"], row["Title"].replace('"',"'"), legal))

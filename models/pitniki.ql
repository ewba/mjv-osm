[out:json][timeout:8000];
//{{geocodeArea:Slovenia}}->.searchArea;
( area["ISO3166-1"="SI"][admin_level=2]; )->.searchArea;

// izberi točke
(
  (
	node["amenity"="drinking_water"](area.searchArea);
	node["amenity"="water_point"](area.searchArea);
	node["man_made"="water_tap"](area.searchArea);
	node["man_made"="water_well"](area.searchArea);
	node["drinking_water"="yes"](area.searchArea);
  ); -(
	node["drinkable"="no"](area.searchArea);
	node["drinking_water"="no"](area.searchArea);
	node["drinking_water"="boil"](area.searchArea);
	node["drinking_water"="conditional"](area.searchArea);
	node["drinking_water:legal=no"](area.searchArea);
	node["access"="no"](area.searchArea);
	node["access"="private"](area.searchArea);
	node["access"="customers"](area.searchArea);
	node["private"="yes"](area.searchArea);
	node["working"="no"](area.searchArea);
	node["tourism"="camp_site"](area.searchArea);
	node["fixme"](area.searchArea);
  );
)->.results;

// za vsako točko dodaj vnos za občino
foreach.results(
  out meta;
  is_in;
  area._[admin_level="8"];
  out ids;
);

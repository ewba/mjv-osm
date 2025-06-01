[out:json][timeout:50];
( area["ISO3166-1"="SI"][admin_level=2]; )->.searchArea;
rel[type=boundary][admin_level=8][wikipedia~"sl:"](area.searchArea);
out qt center;

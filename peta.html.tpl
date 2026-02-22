<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" /> 
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
<div id="map" style="height: 600px;"></div>
<script>
  var map = L.map('map').setView([ {lat}, {lon} ], 7);
   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
       attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
   }).addTo(map);
   fetch('{geojson_file}')
       .then(response => response.json())
       .then(data => {
           L.geoJSON(data, {
               style: function(feature) {
                   return { color: 'red', weight: 2 };
               }
           }).addTo(map);
       });
</script>
</body>
</html>

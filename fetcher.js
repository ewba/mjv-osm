var fs = require('fs');
var concat = require('concat-stream');

var argv = process.argv.slice(2)

async function getData(ql) {
  var query = ql.toString();

  var result = await fetch(
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    {
      method: "POST",
      body: "data="+ encodeURIComponent(`${ql}`)
    },
  ).then(
    (data) => data.json()
  )
  console.log(JSON.stringify(result , null, 2))
}

((argv[0] && fs.createReadStream(argv[0])) || process.stdin).pipe(concat(getData));

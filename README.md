# Universe
*Universe* makes tens to hundreds billion of procedurally generated suns, planets and moons in a virtually unlimited number of persistent galaxies.

The purpose of this code is first and foremost to optimize the number and length of calls (hence the costs) you make to our serverless back-end, then to provide features like JSON-formatting, per-user throttling and per-user billing (if you have paying customers).

- Celestial bodies are generated as much as possible according to latest astronomical discoveries. The main gaps lie in our lack of spiral star distribution, n-ary systems, stars motion, planetary rings, wandering planets, nebulae and asteroid belts.
- Provides physical characteristics, orbital parameters and rotation (spin) parameters
- Calculates the **real-time state vector** of each planet and each moon
- Galaxies are generated in 2D (meaning that a celestial body's state vector has no *inclination*, and that its rotation and revolution axis are always vertical to the galactic plane)
- Results are cached in Redis 
- Some long running tasks can be shortened with **proof of work** (PoW)

As explained above, this code provides a front-end REST API to the back-end serverless generator hosted in *Azure function* and *Amazon lambda*.

## Getting started
### Installation (Ubuntu)
sudo apt-get update

sudo apt-get install -y redis-server python curl python-redis

Then: clone **Universe** from GitHub and... voila!

### Configuration
In your local clone directory, you need to create a file called localconf.py containing the following:
```python
ASKYOURS='your access key, provided by Freevariable'
SEED='a random string of your liking that is unique for each galaxy'
```

### Run
By default, the server will start on localhost port 14799. You can set the port with option --port. Although you can run it standalone for development purposes, in production you are strongly advised to manage your front-end with UWSGI (ubuntu packages: uwsgi,uwsgi-core,uwsgi-emperor,uwsgi-plugin-python):

```
./universe.py --port=5043 &
* Running on http://127.0.0.1:5043/ (Press CTRL+C to quit)
```

### Get your own key!
If you wish to use our generator, you will need to purchase an access key from **freevariable** to cover at least your *pay-per-use* usage of our serverless backend.

## Design
### Bodies locator
Each galaxy is elliptical, with highest stars density near the core. The galaxy is divided into 1400x1400 sectors, each sector is a square covering 9 light years wide. So the galaxy is roughly 12600 light years wide.

- Galaxies are identified by their seed.
- Within a galaxy, sectors are identified by their cartesian coordinates separated with a column. For example, **345:628** corresponds to the sector located at x=345, y=628. Coordinates origin are the top left corner of the galaxy.
- Suns are identified by their trigram, which is unique within a given sector. For example, **345:628:Apo** corresponds to the Apo sun (if it exists in your galaxy, depending on the seed you have chosen!) within sector 345:628
- Planets are identified by their rank, the first one being closest to their sun. For example, **345:628:Apo:3** is the third planet in system Apo.
- Moons are identified by their rank, the first one being closest to their parent planet. For example, **345:638:Apo:3:6** is the sixth moon of planet 3 in the Apo system.

### Physical characteristics
Notes:
- Bodies out of hydrostatic equilibrium (ie small bodies of about less than 400km diameter) and bodies within Roche limit will not be generated.

### Orbital parameters

### State vectors and spin

## API Documentation
To be completed

### disc
Example:
````
curl 'http://127.0.0.1:14799/v1/list/sector/player4067/400/29'
```

### sun
Example:
```
curl 'http://127.0.0.1:14799/v1/get/su/player4067/400/29/RWh'

{"perStr": 5.705832, "trig": "RWh", "m": 2.0512166010113e+30, "lumiSU": 1.1010247142796168, "per": 3.5505651852343463, "yly": 8.031, "nbPl": 2, "HZcenterAU": 1.303023247848569, "seed": 91106006, "id": "quadrant:400:29:RWh", "xly": 1.423, "y": 29, "x": 400, "revol": 1254697.8796800002, "mSU": 1.026352406, "cls": 3}
```

### real time planetary system map
Example:
```
curl 'http://127.0.0.1:14799/v1/map/su/a/400/29/RWh'

[{"smaAU": 1.478868287777208, "smiAU": 1.4784174519337556, "ano": 3.844677553211314, "period": 55880562.18270369, "per": 3.902947712776953, "revol": 0.09075012880266921, "prettyRevol": "2h10m40s", "epoch": 640352988.859, "rho": 10.0, "prettyPeriod": "1y281d", "progress": "0.93%", "order": 1, "id": "400:29:quadrant:400:29:RWh:1", "cls": "E"}, {"smaAU": 1.6885807858803, "smiAU": 1.6857467288938752, "ano": 0.705111786607528, "period": 68178789.6511691, "per": 3.924651761499844, "revol": 0.05957265940113938, "prettyRevol": "1h25m47s", "epoch": 640352988.859, "rho": 300.0, "prettyPeriod": "2y59d", "progress": "51.24%", "order": 2, "id": "400:29:quadrant:400:29:RWh:2", "cls": "E"}]
```

### planet
Example:
```
curl 'http://127.0.0.1:14799/v1/get/pl/player4067/400/29/RWh/1'

{"rad": 1487500.9533006737, "mEA": 0.010402687467665962, "hasAtm": true, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "longTerraFactor": 1.8987, "revol": 0.09075012880266921, "cycleSpeed": 0.4416999237239964, "id": "400:29:quadrant:400:29:RWh:1", "longTerraAmplifier": 1.0, "maxLvl": 509, "perStr": 4.812696000000001, "shortTerraFactor": 0.578484, "per": 3.902947712776953, "dayProgressAtEpoch": 0.2056876, "isLocked": false, "hill": 466355.68892496126, "smi": 221168103.25853467, "inHZ": true, "sma": 221235547.34088564, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "radEA": 0.23322007389358487, "shortTerraAmplifier": 1.09, "g": 1.873998154697319, "m": 6.212869855126415e+22, "cat": 17, "magnet": 0.901456, "smaAU": 1.478868287777208, "isIrr": false, "den": 4506.422315, "order": 1}
```

### moon
To be completed.

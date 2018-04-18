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

What it will NOT do for you:
- Authenticate your users
- Authorize access for your users (can user X see sun Y if he has not visited it yet ?)
- Provide a GUI
- Persist data in storage (filesystem, database)

## Getting started
### Installation (Ubuntu)
sudo apt-get update

sudo apt-get install -y redis-server python curl python-redis python-flask python-flask-api

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

### State vectors, spin, time of the day

## API Documentation
We have three sets of APIs: procedural generation, realtime elements and management interface.
- Procedural generation is fully cacheable. It is cached in a redis DB called dataPlane.
- Realtime elements are not cached. They are interpolated from procedural generation items.
- Management data are cached in a redis DB called controlPlane.

### Procedural generation
#### Discs
Example: generate a disc of radius 3.4 light years centered arount star 400:29:jmj on behalf of user *player4067*

```
curl 'http://127.0.0.1:14799/v1/list/disc/player4067/400/29/jmj/3.4'
```

#### Suns (without Proof of Work)

Example: generate the physical characteristics of sun RWh in sector 400:29 (on behalf of player4067). Here, we see that this sun has two planets in orbit.
Also notice the proof of work that we may reuse later one.

```
curl 'http://127.0.0.1:14799/v1/get/su/player4067/400/29/RWh'

{"pow": "JRprDMexJidlAbtrgsN7tpIlqOxy4b8lRa7h5hiRqZE=", "trig": "RWh", "perStr": 5.705832, "m": 2.0512166010113e+30, "per": 3.5505651852343463, "lumiSU": 1.1010247142796168, "nbPl": 2, "HZcenterAU": 1.303023247848569, "seed": 91106006, "id": "quadrant:400:29:RWh", "cls": 3, "xly": 1.423, "y": 29, "x": 400, "yly": 8.031, "mSU": 1.026352406, "revol": 1254697.8796800002}
```

#### Suns (with Proof of Work)

Example: same as above, but reusing the proof of work and parameters that we got above in a previous call.

```
curl 'http://127.0.0.1:14799/v1/get/su/player4067/400/29/RWh/91106006/3/1.423/8.031/JRprDMexJidlAbtrgsN7tpIlqOxy4b8lRa7h5hiRqZE='

{"perStr": 5.705832, "trig": "RWh", "m": 2.0512166010113e+30, "lumiSU": 1.1010247142796168, "per": 3.5505651852343463, "yly": 8.031, "nbPl": 2, "HZcenterAU": 1.303023247848569, "seed": "91106006", "id": "quadrant:400:29:RWh", "xly": 1.423, "y": 29, "x": 400, "revol": 1254697.8796800002, "mSU": 1.026352406, "cls": 3}
```

#### Planets (without Proof of Work)

Example: generate the physical characteristics of the first planet orbiting sun RWh. We can see that this planet is in the habitable zone, what's more it has an atmosphere but its gravity is nearly twice as much as earth.

```
curl 'http://127.0.0.1:14799/v1/get/pl/player4067/400/29/RWh/1'

{"rad": 1487500.9533006737, "mEA": 0.010402687467665962, "hasAtm": true, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "revol": 0.09075012880266921, "dayProgressAtEpoch": 0.2056876, "perStr": 4.812696000000001, "per": 3.902947712776953, "isLocked": false, "hill": 466355.68892496126, "smi": 221168103.25853467, "inHZ": true, "sma": 221235547.34088564, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "radEA": 0.23322007389358487, "g": 1.873998154697319, "m": 6.212869855126415e+22, "magnet": 0.901456, "smaAU": 1.478868287777208, "isIrr": false, "den": 4506.422315, "order": 1}
```

#### Planets (with Proof of Work)

Example: Same as above, but this time reusing the PoW and some procedurally generated items obtained above during sun generation.
```
curl 'http://127.0.0.1:14799/v1/get/pl/player4067/400/29/RWh/1/91106006/3/1.423/8.031/JRprDMexJidlAbtrgsN7tpIlqOxy4b8lRa7h5hiRqZE='

{"rad": 1487500.9533006737, "mEA": 0.010402687467665962, "hasAtm": true, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "revol": 0.09075012880266921, "dayProgressAtEpoch": 0.2056876, "perStr": 4.812696000000001, "per": 3.902947712776953, "isLocked": false, "hill": 466355.68892496126, "smi": 221168103.25853467, "inHZ": true, "sma": 221235547.34088564, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "radEA": 0.23322007389358487, "g": 1.873998154697319, "m": 6.212869855126415e+22, "magnet": 0.901456, "smaAU": 1.478868287777208, "isIrr": false, "den": 4506.422315, "order": 1}
```

#### Moons (without Proof of Work)

To be completed.

### Realtime elements API
Calls to this API are cacheable: all dynamic attributes are updated seamlessly.
#### Real time logarithmic planetary system map
Example: dump RWh system map.
```
curl 'http://127.0.0.1:14799/v1/map/su/player4067/400/29/RWh'
[{"revolFormatted": "2h10m40s", "rad": 1487500.9533006737, "mEA": 0.010402687467665962, "radEA": 0.23322007389358487, "hasAtm": false, "m": 6.212869855126415e+22, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "revol": 0.09075012880266921, "dayProgressAtEpoch": 0.2056876, "span": 10.0, "perStr": 4.812696000000001, "per": 3.902947712776953, "isLocked": false, "smi": 221168103.25853467, "progress": "22.95%", "inHZ": true, "sma": 221235547.34088564, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "toPer": "1y133d", "meanAno": 3.8546203774678833, "rho": 225426015.31859565, "theta": 2.46087674772146, "localTime": 5576.811487534919, "g": 1.873998154697319, "fromPer": "148d10h", "dayProgress": 0.7112544092827545, "smaAU": 1.478868287777208, "isIrr": false, "den": 4506.422315, "localTimeFormatted": "1h32m56s", "periodFormatted": "1y281d", "order": 1}, {"revolFormatted": "1h25m47s", "rad": 3795536.541663314, "mEA": 0.32225345578878817, "radEA": 0.59508890447991, "hasAtm": false, "m": 1.9246168717492847e+24, "smiAU": 1.6857467288938752, "ano": 4.52364837694262, "period": 68178789.6511691, "revol": 0.05957265940113938, "dayProgressAtEpoch": 0.26428897, "span": 300.0, "perStr": 4.596186, "per": 3.924651761499844, "isLocked": false, "smi": 252184121.6877379, "progress": "49.85%", "inHZ": true, "sma": 252608090.57919973, "cls": "E", "ecc": 0.057913000000000006, "denEA": 1.5236689999999997, "toPer": "1y30d", "meanAno": 0.713261104417672, "rho": 241923965.38768595, "theta": 0.7924442628839685, "localTime": 2184.3056773722506, "g": 8.9163958854062, "fromPer": "1y28d", "dayProgress": 0.4243778264134948, "smaAU": 1.6885807858803, "isIrr": false, "den": 8403.034534999999, "localTimeFormatted": "36m24s", "periodFormatted": "2y59d", "order": 2}]
```

#### Real time orbital elements of a planet
Example: get orbital elements (and physical characteristics) of planet 1.
```
curl 'http://127.0.0.1:14799/v1/get/pl/elements/player4067/400/29/RWh/1'
{"revolFormatted": "2h10m40s", "rad": 1487500.9533006737, "mEA": 0.010402687467665962, "radEA": 0.23322007389358487, "hasAtm": true, "m": 6.212869855126415e+22, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "revol": 0.09075012880266921, "dayProgressAtEpoch": 0.2056876, "perStr": 4.812696000000001, "per": 3.902947712776953, "isLocked": false, "hill": 466355.68892496126, "smi": 221168103.25853467, "progress": "22.95%", "inHZ": true, "sma": 221235547.34088564, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "toPer": "1y133d", "meanAno": 3.8546507020276994, "rho": 225426015.31859565, "theta": 2.46087674772146, "localTime": 5846.508045580361, "g": 1.873998154697319, "fromPer": "148d10h", "dayProgress": 0.7456509217894006, "magnet": 0.901456, "smaAU": 1.478868287777208, "isIrr": false, "den": 4506.422315, "localTimeFormatted": "1h37m26s", "periodFormatted": "1y281d", "order": 1}
```
### Management API
#### List users
Example: list all users which have been billed so far.
```
curl 'http://127.0.0.1:14799/v1/list/users'
```
#### Show detailed service consumption 
Example: show all billing dots for user player4067
```
curl 'http://127.0.0.1:14799/v1/list/billing/player4067'
["{'verb': 'plGen', 't': 1524054485.730217, 'result': 200}", "{'verb': 'plMap', 't': 1524054216.033575, 'result': 200}"]
```

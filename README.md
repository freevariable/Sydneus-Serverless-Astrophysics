*Sydneus* makes tens to hundreds billion of procedurally generated suns, planets and moons in a virtually unlimited number of persistent galaxies.

This API's purpose is first and foremost to optimize the number and length of calls (hence the costs) you make to our serverless back-end, then to provide features like JSON-formatting, per-user throttling and per-user billing (if you have paying customers).

In a nutshell, we:
- Provide physical characteristics, orbital parameters and rotation (spin) parameters
- Calculate the real-time state vector of each planet and each moon (suns are static in our galaxies)
- Galaxies are generated in 2D (meaning that a celestial body's state vector has no *inclination*, and that its rotation and revolution axis are always vertical to the galactic plane)
- Results are cached in Redis 
- Some long running tasks can be shortened with **proof of work** (PoW, see below)

For that, we have two programs:
- **sydneus.py** is a front-end REST API to the back-end serverless generator hosted in *Azure function* and *Amazon lambda*.
- **app/locator.py** is an optional tool that leverages sydneus.py to help perform operations on celestial bodies: please refer to the **app/** README for more information.

What they will NOT do for you:
- Authenticate your users
- Authorize access for your users (can user X see sun Y if he has not visited it yet ?)
- Be a GUI
- Persist data in storage (filesystem, database)

## Getting started

### Recommended installation modes

We encourage you to consider one of the following installation modes:
- Ubuntu vanilla (for test)
- Ubuntu + HAproxy + UWSGI (for unmanaged production)
- Amazon Fargate (for managed production)
- Azure Kubernetes AKS (for managed production)

### Installation (Ubuntu vanilla)
sudo apt-get update

sudo apt-get install -y redis-server python curl python-redis python-flask python-flask-api

Then: clone **Sydneus** from GitHub and... voila!

### Configuration
In your local clone directory, you need to create a file called localconf.py containing the following:
```python
ASKYOURS='your access key, provided by Freevariable'
SEED='a random string of your liking that is unique for each galaxy'
```

### Run
By default, the server will start on localhost port 5043. You can set the port with option --port. Although you can run it standalone for development purposes, in production you are strongly advised to manage your front-end with UWSGI (ubuntu packages: uwsgi,uwsgi-core,uwsgi-emperor,uwsgi-plugin-python):

```
./sydneus.py --port=5043 &
* Running on http://127.0.0.1:5043/ (Press CTRL+C to quit)
```

### Get your own key
If you wish to use our generator, you will need to purchase an access key from **freevariable** to cover at least your *pay-per-use* usage of our serverless backend.

### Probe your first solar system!
Make the following call to the **list/sector** API; it will dump a list of systems in a JSON file:
```
curl 'http://127.0.0.1:5043/v1/list/sector/player4067/310/224'
```

## Design
### Locators
#### Astronomical bodies
Each galaxy is elliptical, with highest stars density near the core. The galaxy is divided into 1400x1400 sectors, each sector is a square covering 9 light years wide. So the galaxy is roughly 12600 light years wide.

- Galaxies are identified by their seed.
- Within a galaxy, sectors are identified by their cartesian coordinates separated with a column. For example, **345:628** corresponds to the sector located at x=345, y=628. Coordinates origin are the top left corner of the galaxy.
- Suns are identified by their trigram, which is unique within a given sector. For example, **345:628:Apo** corresponds to the Apo sun (if it exists in your galaxy, depending on the seed you have chosen!) within sector 345:628
- Planets are identified by their rank, the first one being closest to their sun. For example, **345:628:Apo:3** is the third planet in system Apo.
- Moons are identified by their rank, the first one being closest to their parent planet. For example, **345:638:Apo:3:6** is the sixth moon of planet 3 in the Apo system.

#### Idle satellites and ships
Artificial bodies are not managed by Sydneus, but the API supports them as a convenience for ease of integration within your code logic.
Each such body must be identified by a unique string of your choice, beginning with upper or lowercase ASCII. You must make sure this string is unique among all your users.

- Vessel *Harfang* orbiting sun Apo is located with **345:628:Apo:Harfang**
- Station *Cromwell* orbiting the fifth moon of planet 2 in the 4FN system is located with **76:578:4FN:2:5:Cromwell**

#### Accelerating ships
We provide no support for bodies under impulsion.

## API Documentation
We have three sets of APIs: procedural generation, realtime elements and management interface.
- Procedural generation is fully cacheable. It is cached in a redis DB called dataPlane.
- Realtime elements are not cached. They are interpolated from procedural generation items.
- Management data are cached in a redis DB called controlPlane.

### Procedural generation 

#### Stars

##### Request parameters

To be completed

##### Response elements

|Key       | Value   | Comment                                            |
|----------|---------|----------------------------------------------------|
|trig      |Apo      | Star name, third component of the star locator     |
|x         |300      | Sector X, first component of the star locator      |
|y         |650      | Sector Y, second component of the star locator     |
|xly       |3.6083   | X location within sector (in light years)          |
|yly       |8.03151  | Y location within sector (in light years)          |
|per       |5.70582  | Periapsis, in radians                              |
|lumiSU    |0.88102  | Solar luminosity (Our sun = 1.0)                   |
|absMag    |-1.6492  | Absolute magnitude                                 |
|mSU       |1.02635  | Solar mass (our sun = 1.0)                         |
|nbPl      |6        | Number of orbiting planets                         |
|HZcenterAU|2.30302  | Radius of the center of the Habitable Zone (in AU) |
|cls       |3        | Spectral class (Sydneus code, see below)           |
|spectral  |K        | Spectral class (see below)                         |
|revol     |1497.87  | Rotation time (in seconds)                         |
|seed      |67403928 | Star seed                                          |
|perStr    |2.047326 | *Reserved parameter*                               |

##### Spectral classes

|cls       | spectral   | Comment                                            |
|----------|------------|----------------------------------------------------|
|1         |M           |                                                    |
|2         |K           |                                                    |
|3         |G           |                                                    |
|4         |F           |                                                    |
|5         |A           |                                                    |
|6         |B           |                                                    |
|7         |O           |                                                    |
|8         |bd          |brown dwarf                                         |
|9         |wd          |white dwarf                                         |
|10        |ns/bh       |Neutron star or black hole                          |


#### Planets

##### Request parameters

To be completed

##### Response elements

|Key       | Value   | Comment                                            |
|----------|---------|----------------------------------------------------|
|order     |11       | Planet rank within system                          |
|cls       |J        | Terran     (E) or Jovian (J)                       |
|g         |12.6057  | Surface gravity  (Earth=9.81)                      |
|mEA       |5.36242  | Earth mass (Earth=1.0)                             |
|radEA     |2.0416   | Earth radius (Earth=1.0)                           |
|denEA     |0.62789  | Earth density (Earth=1.0)                          |
|hasAtm    |True     | Has an atmosphere                                  |
|isLocked  |True     | Spin is locked                                     |
|isIrr     |False    | Is within sun radiation zone                       |
|inHZ      |False    | Is in Habitable Zone                               |
|smiAU     |763.662  | Semi-minor axis in AU                              |
|smaAU     |763.675  | Semi-major axis in AU                              |
|ecc       |0.00574  | Eccentricity                                       |
|per       |0.87874  | Periapsis (in radians)                             |
|ano       |4.42784  | Anomaly at epoch                                   |
|hill      |153...   | Radius of Hill sphere (in km)                      |
|perStr    |4.42784  | Reserved                                           |
|spin      |-0.1901  | Rotation (Earth=1.0=24h). Negative for retrograde  |
|period    |453...   | Orbital period in seconds                          |
|dayProg   |0.89799  | Day progress at epoch (1.0=midnight) ref meridian  |

#### Moons

##### Request parameters

To be completed

##### Response elements

To be completed

Notes: moons out of hydrostatic equilibrium (ie small bodies of about less than 400km diameter) and bodies within Roche limit will not be generated.

### Realtime API

#### Stars
In Sydneus, stars are static.

#### Planets

##### Request parameters

To be completed

##### Response elements

|Key            | Value     | Comment                                            |
|---------------|-----------|----------------------------------------------------|
|spinFormatted  |-4h33m44s  |                                                    |
|dayProgress    |0.89799    |Day progress now (same as at epoch if locked)       |
|localTime      |4h5m49s    |Time now at ref meridian                            |
|fromPer        |2238y      |Time from periapsis                                 |
|to  Per        |12130y     |Time to periapsis                                   |
|progress       |15.58%     |Orbital period progress                             |
|meanAno        |4.436726   |Mean Anomaly (realtime) in radians                  |
|rho            |11442...   |Polar distance from sun (realtime) in km            |
|theta          |1.857695   |Polar angle (realtime) in radians                   |


#### Moons

##### Request parameters

To be completed

##### Response elements

To be completed

### Management API

## Examples 

### Procedural generation

#### Sectors
Exemple: generate all stars in sector 310:224 on behalf of *player4067*:

```
curl 'http://127.0.0.1:5043/v1/list/sector/player4067/310/224'
```

#### Discs
Example: generate a disc of radius 3.4 light years centered arount star 400:29:jmj on behalf of user *player4067*

```
curl 'http://127.0.0.1:5043/v1/list/disc/player4067/400/29/jmj/3.4'
```

#### Suns (without Proof of Work)
Example: generate the physical characteristics of sun RWh in sector 400:29 (on behalf of player4067). Here, we see that this sun has two planets in orbit.
Also notice the proof of work that we may reuse later on.

```
curl 'http://127.0.0.1:5043/v1/get/su/player4067/400/29/RWh'

{"pow": "JRprDMexJidlAbtrgsN7tpIlqOxy4b8lRa7h5hiRqZE=", "trig": "RWh", "perStr": 5.705832, "per": 3.5505651852343463, "lumiSU": 1.1010247142796168, "nbPl": 2, "HZcenterAU": 1.303023247848569, "seed": 91106006, "cls": 3, "xly": 1.423, "y": 29, "x": 400, "yly": 8.031, "mSU": 1.026352406, "revol": 1254697.8796800002}
```

#### Suns (with Proof of Work)
Example: same as above, however here you will need not only the sun locator (400:29:RWh), but also the proof of work, the spectral class code (3), the seed, and the x and y coordinates (in light years) of RWh in sector 400:29. All this can be re-used from the previous call above.

```
curl 'http://127.0.0.1:5043/v1/get/su/player4067/400/29/RWh/91106006/3/1.423/8.031/JRprDMexJidlAbtrgsN7tpIlqOxy4b8lRa7h5hiRqZE='

{"perStr": 5.705832, "trig": "RWh", "lumiSU": 1.1010247142796168, "per": 3.5505651852343463, "yly": 8.031, "nbPl": 2, "HZcenterAU": 1.303023247848569, "seed": "91106006", "xly": 1.423, "y": 29, "x": 400, "revol": 1254697.8796800002, "mSU": 1.026352406, "cls": 3}
```

#### Planets (without Proof of Work)

Example: generate the physical characteristics of the first planet orbiting sun RWh. We can see that this is a small planet (radius 1487.5km) in the habitable zone of RWh, what's more it has an atmosphere but its gravity is low, similar to our good old Moon.

```
curl 'http://127.0.0.1:5043/v1/get/pl/player4067/400/29/RWh/1'

{"mEA": 0.010402687467665962, "hasAtm": true, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "revol": 0.09075012880266921, "dayProgressAtEpoch": 0.2056876, "perStr": 4.812696000000001, "per": 3.902947712776953, "isLocked": false, "hill": 466355.68892496126, "inHZ": true, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "radEA": 0.23322007389358487, "g": 1.873998154697319, "smaAU": 1.478868287777208, "isIrr": false, "order": 1}
```

#### Planets (with Proof of Work)

Example: Same as above, but this time reusing the PoW and the same procedurally generated items obtained above during sun generation.
```
curl 'http://127.0.0.1:5043/v1/get/pl/player4067/400/29/RWh/1/91106006/3/1.423/8.031/JRprDMexJidlAbtrgsN7tpIlqOxy4b8lRa7h5hiRqZE='

{"mEA": 0.010402687467665962, "hasAtm": true, "smiAU": 1.4784174519337556, "ano": 0.9587135469107532, "period": 55880562.18270369, "revol": 0.09075012880266921, "dayProgressAtEpoch": 0.2056876, "perStr": 4.812696000000001, "per": 3.902947712776953, "isLocked": false, "hill": 466355.68892496126, "inHZ": true, "cls": "E", "ecc": 0.024690300000000002, "denEA": 0.817121, "radEA": 0.23322007389358487, "g": 1.873998154697319, "smaAU": 1.478868287777208, "isIrr": false, "order": 1}
```

#### Moons (without Proof of Work)

To be completed.

#### Moons (with Proof of Work)

To be completed.

### Realtime elements API
Calls to this API are not cacheable.

#### Real time orbital elements of a planet
Example: get orbital elements of planet 1.
```
curl 'http://127.0.0.1:5043/v1/get/pl/elements/player4067/400/29/RWh/1'

{"revolFormatted": "2h10m40s", "fromPer": "149d5h", "dayProgress": 0.3178352585976779, "toPer": "1y132d", "meanAno": 3.8622080878729736, "rho": 225397850.12794173, "progress": "23.08%", "localTimeFormatted": "41m32s", "theta": 2.4530273644516596, "periodFormatted": "1y281d", "localTime": 2492.086232658437}
```

### Management API
#### List users
Example: list all users which have been billed so far.
```
curl 'http://127.0.0.1:5043/v1/list/users'
```
#### Show detailed service consumption 
Example: show all billing dots for user player4067
```
curl 'http://127.0.0.1:5043/v1/list/billing/player4067'
["{'verb': 'plGen', 't': 1524054485.730217, 'result': 200}", "{'verb': 'plMap', 't': 1524054216.033575, 'result': 200}"]
```

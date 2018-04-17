# Universe
*Universe* makes tens to hundreds billion of procedurally generated suns, planets and moons in a virtually unlimited number of persistent galaxies.

The purpose of this code is first and foremost to optimize the number and length of calls (hence the costs) you make to our serverless back-end, then to provide features like JSON-formatting, per-user throttling and per-user billing (if you have paying customers).

- Celestial bodies are generated as much as possible according to latest astronomical discoveries. The main gap lies in the lack of n-ary systems.
- Provides physical characteristics, orbital parameters and rotation (spin) parameters
- Calculates the **real-time state vector** of each planet and each moon
- Galaxies are generated in 2D (meaning that a celestial body's state vector has no *inclination*, and that its rotation and revolution axis are always vertical to the galactic plane)
- Results are cached in Redis 
- Some long running tasks can be shortened with **proof of work** (PoW)

As explained above, this code provides a front-end REST API to the back-end serverless generator hosted in *Azure function* and *Amazon lambda*.

## Getting started
### Installation
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

### Orbital parameters

### State vectors and spin

## API Documentation
To be completed

### discGen

### sysGen

### planetGen

### moonGen

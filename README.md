# Universe
*Universe* makes tens to hundreds billion of procedurally generated suns, planets and moons in a virtually unlimited number of persistent galaxies.

- Celestial bodies are generated according to latest astronomical discoveries
- Covers physical characteristics, orbital parameters and spin parameters
- The *state vector* of each planet and moon is dynamic, meaning that it changes in real time
- Galaxies are generated in 2D (meaning that celestial bodies have no inclination)

This code provides a front-end REST API to the back-end serverless generator, locared in *Azure function* and *Amazon lambda*.
The code also manages caching, billing and throttling.

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

#### Access key
If you wish to use this galaxy generator, you will need to purchase an access key from **freevariable** to cover at least your **pay-per-use** usage of the serverless backend.

As of now, *Universe* pricing is aligned with Azure functions: https://azure.microsoft.com/en-us/pricing/details/functions/

## API Documentation
To be completed

### discGen

### sysGen

### planetGen

### moonGen

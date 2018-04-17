#!/usr/bin/python
#Copyright 2018 freevariable (https://github.com/freevariable)

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at

#      http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import redis,random,math,sys,uuid,urllib2
import time,datetime,getopt,flask,json
from flask_api import status
from concurrent.futures import ThreadPoolExecutor
import cPickle as pickle
from localconf import *

class setEncoder(json.JSONEncoder):
  def default(self,obj):
    if isinstance(obj,set):
      return list(obj)
    return json.JSONEncoder.default(self,obj)

stp=0
dataPlaneId=6
controlPlaneId=7
PERIOD=5.0
ENDPOINT="https://erdos.azurewebsites.net"
CODE="code="+ASKYOURS
SIGM=0.2
SHORTFREQ=1 #seconds
SHORTTHRESH=10  #hits
SHORTBAN=5  #seconds

def aGauss():
  return random.gauss(0.0,SIGM)

executor=ThreadPoolExecutor(max_workers=8)
app=flask.Flask(__name__)

@app.route("/v1/list/billing/<p>", methods=["GET"])
def v1listBilling(p):
  global controlPlane
  return json.dumps(controlPlane.smembers(p+':dots'),cls=setEncoder)

@app.route("/v1/list/users", methods=["GET"])
def v1listUsers():
  global controlPlane
  return json.dumps(controlPlane.smembers('users'),cls=setEncoder)

@app.route("/v1/list/sector/<p>/<x>/<y>", methods=["GET"])
def v1getSector(x,y,p):
  return json.dumps(sectorGen(x,y,p))

@app.route("/v1/get/su/<p>/<x>/<y>/<su>", methods=["GET"])
def v1getSun(x,y,su,p):
  return json.dumps(suGen(x,y,su,p))

@app.route("/v1/get/pl/<p>/<x>/<y>/<su>/<pl>", methods=["GET"])
def v1getPl(x,y,su,pl,p):
  return json.dumps(plGen(x,y,su,pl,p))

@app.route("/v1/map/su/<p>/<x>/<y>/<su>", methods=["GET"])
def v1listPl(x,y,su,p):
  return json.dumps(suMap(x,y,su,p))

@app.route("/v1/list/disc/<p>/<x>/<y>/<su>/<r>", methods=["GET"])
def v1getDisc(x,y,su,r,p):
  return json.dumps(discGen(x,y,su,r,p))

try:
  opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "port="])
except getopt.GetoptError as err:
  print(err)
  usage()
  sys.exit(2)

portNum=14799
for o, a in opts:
  if o in ("-h", "--help"):
    usage()
    sys.exit()
  elif o in ("--port"):
    portNum=int(a)
  else:
    assert False, "option unknown"
    sys.exit(2)

def initAll():
  global controlPlane
  global controlPlaneId
  global dataPlane
  global dataPlaneId
  controlPlane=redis.StrictRedis(host='localhost', port=6379, db=controlPlaneId)
  try:
    answ=controlPlane.client_list()
  except redis.ConnectionError:
    print "FATAL: cannot connect to redis."
    sys.exit()
  dataPlane=redis.StrictRedis(host='localhost', port=6379, db=dataPlaneId)
  try:
    answ=dataPlane.client_list()
  except redis.ConnectionError:
    print "FATAL: cannot connect to redis."
    sys.exit()
  controlPlane.flushdb()
  dataPlane.flushdb()

def scheduler(period,f,*args):
  def g_tick():
    t1 = time.time()
    count = 0
    while True:
      count += 1
      yield max(t1 + count*period - time.time(),0)
  g = g_tick()
  while True:
    time.sleep(next(g))
    f(*args)

def step():
  global stp
  global controlPlane
  stp=stp+1
  if (stp%600==0):
    nop=''
  return True

def distance(p0, p1):
  if 'x' in p0:
    return math.sqrt((p0['x'] - p1['x'])**2 + (p0['y'] - p1['y'])**2)
  else:
    return math.sqrt((p0['xly'] - p1['xly'])**2 + (p0['yly'] - p1['yly'])**2)   

def billingDot(p,v,c):
  global controlPlane
  dot={}
  dot['t']=time.time()
  dot['verb']=v
  dot['result']=c
  controlPlane.sadd('users',p)
  controlPlane.sadd(p+':dots',dot)

def suMap(x,y,su,p):
  global dataPlane
  if throttle(p):
    return status.HTTP_503_SERVICE_UNAVAILABLE
  verb='plMap'
  url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&seed='+SEED
  print "URL="+url
  try:
    rs=urllib2.urlopen(url)
    rss=rs.read()
    r1=json.loads(rss)
    billingDot(p,verb,rs.getcode())
    return r1
  except urllib2.HTTPError, e:
    return status  

def plGen(x,y,su,pl,p):
  global dataPlane
  cacheLocator=str(x)+':'+str(y)+':'+su+':'+pl
  res=dataPlane.get(cacheLocator)
  if res is None:
    print 'MISS '+cacheLocator
    if throttle(p):
      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='plGen'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&pl='+pl+'&seed='+SEED
    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      dataPlane.set(cacheLocator,rss)
      billingDot(p,verb,rs.getcode())
      return r1
    except urllib2.HTTPError, e:
      return status  
  else:
    print 'HIT '+cacheLocator
    r1=json.loads(res)
  return r1

def suGen(x,y,su,p):
  global dataPlane
  cacheLocator=str(x)+':'+str(y)+':'+su
  res=dataPlane.get(cacheLocator)
  if res is None:
#    print 'MISS '+cacheLocator
    if throttle(p):
      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='suGen'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&seed='+SEED
#    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      dataPlane.set(cacheLocator,rss)
      billingDot(p,verb,rs.getcode())
      return r1
    except urllib2.HTTPError, e:
      return status  
  else:
    print 'HIT '+cacheLocator
    r1=json.loads(res)
  return r1

def throttle(p):
  global controlPlane
  thr=controlPlane.get(p+':isThrottled?')
  if thr is not None:
    return True
  else:
    controlPlane.incr(p+':shortCounter',1)
    cnt=int(controlPlane.get(p+':shortCounter'))
    if cnt==1: #start SHORTFREQ timer
      controlPlane.expire(p+':shortCounter',SHORTFREQ)
    elif cnt>SHORTTHRESH:
      controlPlane.set(p+':isThrottled?',True)
      controlPlane.expire(p+':isThrottled?',SHORTBAN*(cnt-SHORTTHRESH))
      controlPlane.delete(p+':shortCounter')
      return True
  return False

def sectorGen(x,y,p):
  global dataPlane
  global controlPlane
  cacheLocator=str(x)+':'+str(y)
  res=dataPlane.get(cacheLocator)
  if res is None:
    print 'MISS '+cacheLocator
    if throttle(p):
      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='sectorGen'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&seed='+SEED
    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      dataPlane.set(cacheLocator,rss)
      billingDot(p,verb,rs.getcode())
      return r1
    except urllib2.HTTPError, e:
      return status  
  else:
    print 'HIT '+cacheLocator
    r1=json.loads(res)
  return r1

def R1sectorGen(x,y,p):
  global r1
  global r1done
  r1=sectorGen(x,y,p)
  r1done=True
  return r1done

def R2sectorGen(x,y,p):
  global r2
  global r2done
  r2=sectorGen(x,y,p)
  r2done=True
  return r2done

def R3sectorGen(x,y,p):
  global r3
  global r3done
  r3=sectorGen(x,y,p)
  r3done=True
  return r3done

def R4sectorGen(x,y,p):
  global r4
  global r4done
  r4=sectorGen(x,y,p)
  r4done=True
  return r4done

def R5sectorGen(x,y,p):
  global r5
  global r5done
  r5=sectorGen(x,y,p)
  r5done=True
  return r5done

def discGen(xs,ys,su,r,p):
  global r1
  global r2
  global r3
  global r4
  global r5
  global executor
  global r1done
  global r2done
  global r3done
  global r4done
  global r5done
  r1done=False
  r2done=False
  r3done=False
  r4done=False
  r5done=False
  seed=SEED
  sectorwidth=9
  radius=float(r)
  x=float(xs)
  y=float(ys)
  xi=int(x)
  yi=int(y)
  if radius>float(sectorwidth):
    return '[]'
  found_su=False
  su_ly={}
  xx=float((1+sectorwidth)*x)
  yy=float((1+sectorwidth)*y)
  executor.submit(R5sectorGen,xi,yi-1,p)
  executor.submit(R2sectorGen,xi+1,yi,p)
  executor.submit(R3sectorGen,xi-1,yi,p)
  executor.submit(R4sectorGen,xi,yi+1,p)
  R1sectorGen(xi,yi,p)
  loopEnd=False
  while loopEnd==False:
    loopEnd=(r1done and r2done and r3done and r4done and r5done) 
    time.sleep(0.3)
  for s in r1:
    if (s['trig']==su):
      found_su=True
      su_ly['xly']=float(s['xly'])
      su_ly['yly']=float(s['yly'])
      break
  r=[]
  p0={}
  p0['xly']=0.0
  p0['yly']=0.0
  if found_su==True:
    for s in r1:
      if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
        s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
        s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
        d=distance(s,p0)
        if (d<=radius):
          s['dist']=float("{0:.3f}".format(d))
          r.append(s);
    if ((su_ly['xly']-xx)>(float(sectorwidth)-radius)):
#      print "extend x+1"
#      r2=sectorGen(xi+1,yi)
      for s in r2:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)
    if ((su_ly['xly']-xx)<radius):
#      print "extend x-1"
#      r3=sectorGen(xi-1,yi)  
      for s in r3:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)
    if ((su_ly['yly']-yy)>(sectorwidth-radius)):
#      print "extend y+1"  
#      r4=sectorGen(xi,yi+1)
      for s in r4:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)    
    if ((su_ly['yly']-yy)<radius):
#      print "extend y-1"  
#      r5=sectorGen(xi,yi-1) 
      for s in r5:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)        
  else:  #not found
    return '[]'
  return r

initAll()
executor.submit(scheduler,PERIOD,step)
if __name__=="__main__":
    app.run(host='127.0.0.1',port=portNum,threaded=True)
else:
  nop=''

print "No more tasks to perform. Bye bye!"


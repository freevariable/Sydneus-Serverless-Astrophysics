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
from concurrent.futures import ThreadPoolExecutor
import cPickle as pickle
from localconf import *

redisDB=0
version="148"
minVersion="146"
PERIOD=5.0
ENDPOINT="https://erdos.azurewebsites.net/"
CODE="code="+ASKYOURS
startTime=datetime.datetime.strptime("001d06h30m00s","%jd%Hh%Mm%Ss")
SIGM=0.2

def aGauss():
  return random.gauss(0.0,SIGM)

executor=ThreadPoolExecutor(max_workers=5)
app=flask.Flask(__name__)

@app.route("/v1/describe/status", methods=["GET"])
def v1status():
  status={}
  return json.dumps(str(status))

@app.route("/v1/get/sector/<x>/<y>/", methods=["GET"])
def v1getSector(x,y):
  verb='sectorGen'
  url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+x+'&y='+y
  print "URL="+url
  rs=urllib2.urlopen(url)
  sched=json.loads(rs.read())
  return json.dumps(str(sched))

try:
  opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "port="])
except getopt.GetoptError as err:
  print(err)
  usage()
  sys.exit(2)

portNum=4999
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
  global r
  global redisDB
  r=redis.StrictRedis(host='localhost', port=6379, db=redisDB)
  try:
    answ=r.client_list()
  except redis.ConnectionError:
    print "FATAL: cannot connect to redis."
    sys.exit()

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
  return True

def distance(p0, p1):
  if 'x' in p0:
    return math.sqrt((p0['x'] - p1['x'])**2 + (p0['y'] - p1['y'])**2)
  else:
    return math.sqrt((p0['xly'] - p1['xly'])**2 + (p0['yly'] - p1['yly'])**2)   

def sectorGen(x,y,seed):
  verb='sectorGen'
  url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+x+'&y='+y
  print "URL="+url
  rs=urllib2.urlopen(url)
  r1=json.loads(rs.read())
  return r1

def discGen(x,y,su,radius,seed):
  sectorwidth=9
  found_su=False
  su_ly={}
  xx=(1+sectorwidth)*x
  yy=(1+sectorwidth)*y
  r1=sectorGen(x,y,seed)
  for s in r1:
    if (s['trig']==su):
      found_su=True
      su_ly['xly']=s['xly']
      su_ly['yly']=s['yly']
      break
  r=[]
  p0={}
  p0['xly']=0.0
  p0['yly']=0.0
  if found_su==True:
    print 'yo'
    for s in r1:
      if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
        s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
        s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
        d=distance(s,p0)
        if (d<=radius):
          s['dist']=float("{0:.3f}".format(d))
          r.append(s);
    if ((su_ly['xly']-xx)>(sectorwidth-radius)):
      print "extend x+1"
      r2=sectorGen(x+1,y,seed)
      for s in r2:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)
    if ((su_ly['xly']-xx)<radius):
      print "extend x-1"
      r2=sectorGen(x-1,y,seed)  
      for s in r2:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)
    if ((su_ly['yly']-yy)>(sectorwidth-radius)):
      print "extend y+1"  
      r2=sectorGen(x,y+1,seed)
      for s in r2:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)    
    if ((su_ly['yly']-yy)<radius):
      print "extend y-1"  
      r2=sectorGen(x,y-1,seed) 
      for s in r2:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.3f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.3f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.3f}".format(d))
            r.append(s)        
  return r

initAll()
executor.submit(scheduler,PERIOD,step)
if __name__=="__main__":
    app.run(host='127.0.0.1',port=portNum,threaded=True)
else:
  nop=''

print "No more tasks to perform. Bye bye!"


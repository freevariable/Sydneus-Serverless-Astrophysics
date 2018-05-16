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
TWOPI=6.28318530718
AU2KM=149597871.0

def aGauss():
  return random.gauss(0.0,SIGM)

def ff(f):
  return "%.2f" % f

def prettyDelta(t1,t2):
  delta=int(t2-t1)
  zeroing=False
  ignoredays=False
  ignoresubdays=False
  ignoreminutes=False
  ignoreseconds=False
  p={}
  y=int(delta/31536000)
  if (y>0):
    p['y']=y
    ignoresubdays=True
    if (y>900):
      ignoredays=True
  else:
    zeroing=True
  if (ignoredays):
    return p
  aux=delta-y*31536000
  d=int(aux/86400)
  if (d>0):
    p['d']=d
    zeroing=False
    ignoreseconds=True
    if (d>30):
      ignoreminutes=True
  else:
    if (zeroing==False):
      p['d']=d
  if (ignoresubdays):
    return p
  aux=aux-d*86400
  h=int(aux/3600)
  if (h>0):
    p['h']=h
    zeroing=False
  else:
    if (zeroing==False):
      p['h']=h
  if (ignoreminutes):
    return p
  aux=aux-h*3600
  m=int(aux/60)
  if (m>0):
    p['m']=m
  else:
    if (zeroing==False):
      p['m']=m
  if (ignoreseconds):
    return p
  p['s']=aux-m*60
  return p

def prettyDeltaCompact(t1,t2):
  p=prettyDelta(t1,t2)
  pdc=''
  if ('y' in p):
    pdc=pdc+str(p['y'])+'y'
  if ('d' in p):
    pdc=pdc+str(p['d'])+'d'
  if ('h' in p):
    pdc=pdc+str(p['h'])+'h'
  if ('m' in p):
    pdc=pdc+str(p['m'])+'m'
  if ('s' in p):
    pdc=pdc+str(p['s'])+'s'
  return pdc        

def getEccAno(ano,ecc):
  precision=1000000000000.0
  exitCondition=False
  eccAno=0.0
  maxpre=0.01/precision
  pre=0.5
  while exitCondition==False:
    aux=eccAno-ecc*math.sin(eccAno)
    delta=abs(math.fmod(aux-ano,TWOPI))
    while (delta<pre):
      pre=pre/10.0
    if (delta<=maxpre):
      exitCondition=True
    if (eccAno>TWOPI):
      exitCondition=True
      eccAno=-100.0
    if exitCondition==False:
      eccAno=eccAno+0.5*pre
  return eccAno

def getTheta(eccAno,ecc):
  aux=(1+ecc)*math.tan(eccAno/2.0)*math.tan(eccAno/2.0)/(1-ecc)
  aux=math.sqrt(aux)
  trueAno=2.0*math.atan(aux)
#  print trueAno
  return trueAno

def getRho2(smi,theta,ecc):
  return smi/(math.sqrt(1-(ecc*ecc*math.cos(theta)*math.cos(theta))))

def elements(p,detailed):
  t=time.time()-883612799.0
  if 'epoch' in p:
    epoch=p['epoch']  #satellites and vessels
  else:
    epoch=0.0  #all celestial bodies
  deltat=t-epoch
  deltap=deltat/p['period']
  if p['spin']>0.0:
    deltar=deltat/(p['spin']*86400.0)
  else:
    deltar=0.0
  deltaa=TWOPI*deltap
  deltab=deltar-math.floor(deltar)
#  print "DELTAR "+str(deltar)
#  print "DELTAB "+str(deltab)
  e={}
  e['dayProgress']=p['dayProgressAtEpoch']+deltab
  if e['dayProgress']>1.0:
    e['dayProgress']=e['dayProgress']-1.0
  e['localTime']=abs(e['dayProgress']*p['spin']*86400.0)
  e['localTimeFormatted']=prettyDeltaCompact(0.0,e['localTime'])
  e['meanAno']=(p['ano']+deltaa)%TWOPI
  eccAno=getEccAno(e['meanAno'],p['ecc'])
  e['theta']=getTheta(eccAno,p['ecc'])
#  e['rho']=getRho(p['smaAU']*AU2KM,p['ecc'],eccAno)
  e['rho']=getRho2(p['smiAU']*AU2KM,e['theta'],p['ecc'])
  if (e['theta']>p['per']):
    progress=e['theta']-p['per']
  else:
    progress=p['per']-e['theta']
  timeToPer=p['period']*(TWOPI-progress)/TWOPI
  timeFromPer=p['period']*progress/TWOPI
  dateTimeToPer=prettyDeltaCompact(0.0,timeToPer)
  dateTimeFromPer=prettyDeltaCompact(0.0,timeFromPer)
  e['progress']=str(ff(100*progress/TWOPI))+'%'
  e['toPer']=dateTimeToPer
  e['fromPer']=dateTimeFromPer
  if detailed:
    e['periodFormatted']=prettyDeltaCompact(0.0,p['period'])
    e['spinFormatted']=prettyDeltaCompact(0.0,abs(p['spin']*86400.0))
    if p['spin']<0.0:
      e['spinFormatted']='-'+e['spinFormatted']
    #e.update(p)
  return e

executor=ThreadPoolExecutor(max_workers=8)
app=flask.Flask(__name__)

@app.route("/v1/map/su/<pl>/<pmin>/<pmax>/<x>/<y>/<su>", methods=["GET"])
def v1mapSu(pl,pmin,pmax,x,y,su):
  global controlPlane
  pMi=int(pmin)
  pMa=int(pmax)
  pls=plGen(x,y,su,None,pl)
  p1={}
  p1['minSmaAU']=1E10
  p1['maxSmaAU']=0.0
  for p in pls:
    if (p['smaAU']>p1['maxSmaAU']):
      p1['maxSmaAU']=p['smaAU']
    if (p['smiAU']<p1['minSmaAU']):
      p1['minSmaAU']=p['smaAU']
  if p1['maxSmaAU']==p1['minSmaAU']:
    scalef=1.0
  else:
    scalef=(pMa-pMi)/math.log10(p1['maxSmaAU']/p1['minSmaAU'])
  pR={}
  pR['logScale']=[]
  pR['svg']={}
  for p in pls:
    e={}
    span=p['smaAU']/p1['minSmaAU']
    e['span']=pMi+scalef*math.log10(span)
    e['rank']=p['rank']
    el=elements(p,True)
    pR['logScale'].append(e)     
  return json.dumps(pR)

@app.route("/v1/map/pl/<pl>/<pmin>/<pmax>/<x>/<y>/<su>/<p>", methods=["GET"])
def v1mapPl(pl,pmin,pmax,x,y,su,p):
  global controlPlane
  pMi=int(pmin)
  pMa=int(pmax)
  pls=plGen(x,y,su,None,pl)
  prk=int(p)
  found=False
  for pl in pls:
    if pl['rank']==prk:
      found=True
      break
  if found==False:
    flask.abort(404)
  if len(pl['mo'])<1:
    flask.abort(404)
  m1={}
  m1['minSmaAU']=1E10
  m1['maxSmaAU']=0.0
  for m in pl['mo']:
    if (m['smaAU']>m1['maxSmaAU']):
      m1['maxSmaAU']=m['smaAU']
    if (m['smiAU']<m1['minSmaAU']):
      m1['minSmaAU']=m['smaAU']
  if m1['maxSmaAU']==m1['minSmaAU']:
    scalef=1.0
  else:
    scalef=(pMa-pMi)/math.log10(m1['maxSmaAU']/m1['minSmaAU'])
  mR={}
  mR['logScale']=[]
  mR['svg']='<svg viewBox="0 0 '+pmax+" "+pmax+'" xmlns="http://www.w3.org/2000/svg">'
  pmax2=str(int(pMa/2))
  for m in pl['mo']:
    e={}
    span=m['smaAU']/m1['minSmaAU']
    e['span']=pMi+scalef*math.log10(span)
    e['rank']=m['rank']
    el=elements(m,True)
    mR['logScale'].append(e)     
    eX=str(int(pMa/2+e['span']*0.5*(el['rho']*math.cos(el['theta'])/m['sma'])))
    eY=str(int(pMa/2+e['span']*0.5*(el['rho']*math.sin(el['theta'])/m['sma'])))
#    mR['svg']=mR['svg']+'<ellipse cx="'+pmax2+'" cy="'+pmax2+'" rx="'+eX+'" ry="'+eY+'" />'
    eR=str(int(pMa/2+e['span']*0.5))
    mR['svg']=mR['svg']+'<circle cx="'+pmax2+'" cy="'+pmax2+'" r="'+eR+'" />'
  mR['svg']=mR['svg']+'</svg>'
  return json.dumps(mR)

@app.route("/v1/list/billing/<p>", methods=["GET"])
def v1listBilling(p):
  global controlPlane
  return json.dumps(controlPlane.lrange(p+':dots',0,-1))

@app.route("/v1/list/users", methods=["GET"])
def v1listUsers():
  global controlPlane
  return json.dumps(controlPlane.smembers('users'),cls=setEncoder)

@app.route("/v1/list/sector/<p>/<x>/<y>", methods=["GET"])
def v1getSector(x,y,p):
  return json.dumps(sectorGen(x,y,p))

@app.route("/v1/get/spacecraft/<p>/<x>/<y>/<su>/<sc>", methods=["GET"])
def v1getCraftAtSu(x,y,su,sc,p):
  return json.dumps(getCraftAtSu(x,y,su,sc,p))

@app.route("/v1/get/spacecraft/<p>/<x>/<y>/<su>/<pl>/<sc>", methods=["GET"])
def v1getCraftAtPl(x,y,su,pl,sc,p):
  return json.dumps(getCraftAtPl(x,y,su,pl,sc,p))

@app.route("/v1/get/spacecraft/<p>/<x>/<y>/<su>/<pl>/<mo>/<sc>", methods=["GET"])
def v1getCraftAtMo(x,y,su,pl,mo,sc,p):
  return json.dumps(getCraftAtMo(x,y,su,pl,sc,p))

@app.route("/v1/get/su/<p>/<x>/<y>/<su>", methods=["GET"])
def v1getSun(x,y,su,p):
  return json.dumps(suGen(x,y,su,p))

@app.route("/v1/get/su/<p>/<x>/<y>/<su>/<suseed>/<sucls>/<sux>/<suy>/<proof>", methods=["GET"])
def v1getSunWithPoW(x,y,su,suseed,sucls,sux,suy,proof,p):
  return json.dumps(suGenWithPoW(x,y,su,suseed,sucls,sux,suy,proof,p))

@app.route("/v1/list/pl/<p>/<x>/<y>/<su>", methods=["GET"])
def v1getPl(x,y,su,p):
  pls=plGen(x,y,su,'*',p)
  if len(pls)<1: 
    flask.abort(404)
  for aP in pls:
    aP['nbMo']=len(aP['mo'])
    del aP['mo']
  return json.dumps(pls)

@app.route("/v1/list/mo/<p>/<x>/<y>/<su>/<pl>", methods=["GET"])
def v1getMo(x,y,su,pl,p):
  pls=plGen(x,y,su,'*',p)
  if len(pls)<1: 
    flask.abort(404)
  for aP in pls:
    if aP['rank']==int(pl):
      return json.dumps(aP['mo'])
  abort(404)

@app.route("/v1/list/pl/<p>/<x>/<y>/<su>/<suseed>/<sucls>/<sux>/<suy>/<proof>", methods=["GET"])
def v1getPlWithPoW(x,y,su,pl,suseed,sucls,sux,suy,proof,p):
  return json.dumps(plGenWithPoW(x,y,su,None,suseed,sucls,sux,suy,proof,p))

@app.route("/v1/get/pl/elements/<p>/<x>/<y>/<su>/<pl>", methods=["GET"])
def v1getPlElements(x,y,su,pl,p):
  ap=plGen(x,y,su,pl,p)
  if pl=='*':
    print ap[0]
    print ap[0]['period']
    return json.dumps(elements(ap[0],True))
  else:
    print ap
    print ap['period']
    return json.dumps(elements(ap,True))

@app.route("/v1/get/mo/elements/<p>/<x>/<y>/<su>/<pl>/<mo>", methods=["GET"])
def v1getMoElements(x,y,su,pl,mo,p):
  ap=plGen(x,y,su,pl,p)
  if mo=='*':
    print ap['mo'][0]
    print ap['mo'][0]['period']
    return json.dumps(elements(ap['mo'][0],True))
  else:
    moNum=int(mo)
    print ap['mo']
    for m in ap['mo']:
      if m['rank']==moNum:
        print m['period']
        return json.dumps(elements(m,True))
    abort(404)

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
  controlPlane.lpush(p+':dots',dot)

def plGenWithPoW(x,y,su,pl,suseed,sucls,sux,suy,proof,p):
  global dataPlane
  if pl is None:
    pl='*'
    cacheLocator=str(x)+':'+str(y)+':'+su+':*'
    res=dataPlane.get(cacheLocator)
  else:
    cacheLocator=str(x)+':'+str(y)+':'+su+':'+pl
    res=dataPlane.get(cacheLocator)
  if (res is None):
    print 'MISS '+cacheLocator
    if throttle(p):
      flask.abort(503)
#      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='plGenWithPoW'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&pl='+pl+'&suseed='+suseed+'&cls='+sucls+'&xly='+sux+'&yly='+suy+'&pow='+proof+'&seed='+SEED
    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      if len(rss)>5:
        dataPlane.set(cacheLocator,rss)
      else:
        #return status.HTTP_404_NOT_FOUND
        flask.abort(404)
      billingDot(p,verb,rs.getcode())
      for aP in r1:
        cacheLocator=str(x)+':'+str(y)+':'+su+':'+str(aP['rank'])
        dataPlane.set(cacheLocator,json.dumps(aP))
      return r1
    except urllib2.HTTPError, e:
      flask.abort(503)
#      return status  
  elif (len(res)<5):
#    return status.HTTP_404_NOT_FOUND
     flask.abort(404)
  else:
    print 'HIT '+cacheLocator+' len '+str(len(res))
  return json.loads(res)

def plGen(x,y,su,pl,p):
  global dataPlane
  if pl is None:
    pl='*'
    cacheLocator=str(x)+':'+str(y)+':'+su+':*'
    res=dataPlane.get(cacheLocator)
  else:
    cacheLocator=str(x)+':'+str(y)+':'+su+':'+pl
    res=dataPlane.get(cacheLocator)
  if (res is None):
    print 'MISS '+cacheLocator
    if throttle(p):
      flask.abort(503)
#      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='plGen'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&pl='+pl+'&seed='+SEED
    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      if len(rss)>5:
        if pl=='*':
          dataPlane.set(cacheLocator,rss)
          for aP in r1:
            cacheLocator=str(x)+':'+str(y)+':'+su+':'+str(aP['rank'])
            dataPlane.set(cacheLocator,json.dumps(aP))
        else:
          dataPlane.set(cacheLocator,rss)
      else:
        flask.abort(404)
#        return status.HTTP_404_NOT_FOUND
      billingDot(p,verb,rs.getcode())
      if pl=='*':
        for aP in r1:
          cacheLocator=str(x)+':'+str(y)+':'+su+':'+str(aP['rank'])
          print cacheLocator
          dataPlane.set(cacheLocator,json.dumps(aP))
      else:
        cacheLocator=str(x)+':'+str(y)+':'+su+':'+str(r1['rank'])
        print cacheLocator
        dataPlane.set(cacheLocator,json.dumps(r1))
      return r1
    except urllib2.HTTPError, e:
      flask.abort(503)
#      return status  
  elif len(res)<5:
    flask.abort(404)
#    return status.HTTP_404_NOT_FOUND
  else:
    print 'HIT '+cacheLocator+' len '+str(len(res))
  return json.loads(res)

def suGenWithPoW(x,y,su,suseed,sucls,sux,suy,proof,p):
  global dataPlane
  cacheLocator=str(x)+':'+str(y)+':'+su
  res=dataPlane.get(cacheLocator)
  if (res is None):
    print 'MISS '+cacheLocator
    if throttle(p):
      flask.abort(503)
#      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='suGenWithPoW'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&seed='+SEED+'&suseed='+suseed+'&cls='+sucls+'&xly='+sux+'&yly='+suy+'&pow='+proof
#    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      if 'trig' in rss:
        dataPlane.set(cacheLocator,rss)
      else:
        flask.abort(404)
#        return status.HTTP_404_NOT_FOUND    
      billingDot(p,verb,rs.getcode())
      return r1
    except urllib2.HTTPError, e:
      flask.abort(503) 
#      return status  
  elif 'trig' not in res:
    flask.abort(404)
#    return status.HTTP_404_NOT_FOUND    
  else:
    print 'HIT '+cacheLocator
    #r1=json.loads(res)
  return res

def getCraftAtSu(x,y,su,sc,p):
  global dataPlane
  cacheLocator='spacecraft:'+str(x)+':'+str(y)+':'+su
  res=dataPlane.get(cacheLocator)
  if res is None:
    return '[]'   
  else:
    r1=json.loads(res)
  return r1

def getCraftAtPl(x,y,su,pl,sc,p):
  global dataPlane
  cacheLocator='spacecraft:'+str(x)+':'+str(y)+':'+su+':'+pl
  res=dataPlane.get(cacheLocator)
  if res is None:
    return '[]'   
  else:
    r1=json.loads(res)
  return r1

def getCraftAtMo(x,y,su,pl,mo,sc,p):
  global dataPlane
  cacheLocator='spacecraft:'+str(x)+':'+str(y)+':'+su+':'+pl+':'+mo
  res=dataPlane.get(cacheLocator)
  if res is None:
    return '[]'   
  else:
    r1=json.loads(res)
  return r1

def suGen(x,y,su,p):
  global dataPlane
  cacheLocator=str(x)+':'+str(y)+':'+su
  res=dataPlane.get(cacheLocator)
  if (res is None):
#    print 'MISS '+cacheLocator
    if throttle(p):
      flask.abort(503)
#      return status.HTTP_503_SERVICE_UNAVAILABLE
    verb='suGen'
    url=ENDPOINT+'/api/'+verb+'?'+CODE+'&x='+str(x)+'&y='+str(y)+'&su='+su+'&seed='+SEED
#    print "URL="+url
    try:
      rs=urllib2.urlopen(url)
      rss=rs.read()
      r1=json.loads(rss)
      if 'trig' in rss:
        dataPlane.set(cacheLocator,rss)
      else:
        flask.abort(404)
#        return status.HTTP_404_NOT_FOUND
      billingDot(p,verb,rs.getcode())
      return r1
    except urllib2.HTTPError, e:
      flask.abort(503)
#      return status  
  else:
    if 'trig' not in res:
      flask.abort(404)
#      return status.HTTP_404_NOT_FOUND
    else:
      print 'HIT '+cacheLocator
    return res

def throttle(p):
  global controlPlane
  throttled=False
  thr=controlPlane.get(p+':isThrottled?')
  if thr is not None:
    throttled=True
    controlPlane.incr(p+':shortCounter',1)
    cnt=int(controlPlane.get(p+':shortCounter'))
    auxi=random.randint(0,cnt)
    if auxi==0:
      throttled=False
    else:
      return True
  if thr is None or throttled==False:
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
      flask.abort(503)
#      return status.HTTP_503_SERVICE_UNAVAILABLE
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
      flask.abort(503)
#      return status  
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
    if 'trig' not in s:
      break
    s['sectorX']=xs
    s['sectorY']=ys
  for s in r2:
    if 'trig' not in s:
      break
    s['sectorX']=str(xi+1)
    s['sectorY']=ys
  for s in r3:
    if 'trig' not in s:
      break
    s['sectorX']=str(xi-1)
    s['sectorY']=ys
  for s in r4:
    if 'trig' not in s:
      break
    s['sectorX']=xs
    s['sectorY']=str(yi+1)
  for s in r5:
    if 'trig' not in s:
      break
    s['sectorX']=xs
    s['sectorY']=str(yi-1)
  for s in r1:
    if 'trig' not in s:
      break
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
        s['xly']=float("{0:.5f}".format(s['xly']-su_ly['xly']))
        s['yly']=float("{0:.5f}".format(s['yly']-su_ly['yly']))        
        d=distance(s,p0)
        if (d<=radius):
          s['dist']=float("{0:.5f}".format(d))
          r.append(s);
    if ((su_ly['xly']-xx)>(float(sectorwidth)-radius)):
#      print "extend x+1"
#      r2=sectorGen(xi+1,yi)
      for s in r2:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.5f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.5f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.5f}".format(d))
            r.append(s)
    if ((su_ly['xly']-xx)<radius):
#      print "extend x-1"
#      r3=sectorGen(xi-1,yi)  
      for s in r3:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.5f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.5f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.5f}".format(d))
            r.append(s)
    if ((su_ly['yly']-yy)>(sectorwidth-radius)):
#      print "extend y+1"  
#      r4=sectorGen(xi,yi+1)
      for s in r4:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.5f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.5f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.5f}".format(d))
            r.append(s)    
    if ((su_ly['yly']-yy)<radius):
#      print "extend y-1"  
#      r5=sectorGen(xi,yi-1) 
      for s in r5:
        if ((abs(s['xly']-su_ly['xly'])<=radius) and (abs(s['yly']-su_ly['yly'])<=radius)):
          s['xly']=float("{0:.5f}".format(s['xly']-su_ly['xly']))
          s['yly']=float("{0:.5f}".format(s['yly']-su_ly['yly']))        
          d=distance(s,p0)
          if (d<=radius):
            s['dist']=float("{0:.5f}".format(d))
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


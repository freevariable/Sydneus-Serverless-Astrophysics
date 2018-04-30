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

SYDNEUS='http://127.0.0.1:14799/v1'
SCDEPTH=6
MODEPTH=5
PLDEPTH=4
SUDEPTH=3
SEDEPTH=2
AU2KM=149597871.0  # in km
LY2KM=9.4607E12
LY2AU=63241.0
TWOPI=6.28318530718
SECTORWIDTH=9
SUKG=1.99855E30
EAKG=5.97237E24
PISQUARE=9.86960440109
G=6.67408E-11 

dataPlaneId=6
controlPlaneId=7
user='admin'

import urllib2,redis,sys,json,math,re
import time,uuid

def getOrbPeriod(sma,M):  
  a3=math.pow(sma*1000,3.0) 
  P2=a3*4*PISQUARE/(G*M)
  P=math.sqrt(P2)
  return P

def smi2sma(smi,e):
  return smi/math.sqrt(1-e*e)

def init():
  global dataPlane
  global t
  t=time.time()
  dataPlane=redis.StrictRedis(host='localhost', port=6379, db=dataPlaneId)
  try:
    answ=dataPlane.client_list()
  except redis.ConnectionError:
    print "FATAL: cannot connect to redis."
    sys.exit()

class locator:
  name=''
  static=None
  dynamic=None 
  parent=None
  depth=0
  x=0.0
  y=0.0
  xAU=0.0
  yAU=0.0

  def distanceAU(self,l2):
    d=math.sqrt((self.xAU - l2.xAU)**2 + (self.yAU - l2.yAU)**2)
    return d

  def dist(self,l2):
    d=0.0
    interSector=False
    interSu=False
    ns1=self.name.split(":")
    ns2=l2.name.split(":")
    depthMin=min(self.depth,l2.depth)
    depthDelta=abs(self.depth-l2.depth)
    print "depthMin: "+str(depthMin)
    print "depthDelta: "+str(depthDelta)
    if ((ns1[0]==ns2[0]) and (ns1[1]==ns2[1])):
      print "same sector"
      if (ns1[2]==ns2[2]):
        print "same su"
      else:
        interSu=True
    else:
      interSector=True
    ref='su'
    if interSu:
      ref='se'
    if interSector:
      ref='gx'
    self.cartesianize(ref)
    l2.cartesianize(ref)
    if interSector:
      d=d+self.distanceAU(l2)
    if interSu:
      d=d+self.distanceAU(l2)
    else:
      d=d+self.distanceAU(l2)
    return d

  def initParentAndDepth(self,n):
    ns=n.split(":")
    self.depth=len(ns)
    ns=ns[:-1]
    pl=''
    if (self.depth-1)>1:
      for an in ns:
        pl=pl+an+':'
      pl=pl[:-1]
      self.parent=locator(pl)

  def cartesianize(self,ref):
    print "cartesianizing "+self.name
    coords={}
    if self.dynamic is None:
      if self.static is not None:
        if 'xly' in self.static:
          print "STATIC"
          print self.static
          if ref=='su':
            self.x=0.0
            self.y=0.0
          elif ref=='se':
            self.x=float(self.static['xly'])*LY2KM
            self.y=float(self.static['yly'])*LY2KM
          elif ref=='gx':
            self.x=float(self.static['xly'])*LY2KM+float((self.static['x']-1)*SECTORWIDTH*LY2KM)
            self.y=float(self.static['yly'])*LY2KM+float((self.static['y']-1)*SECTORWIDTH*LY2KM)
          else:
            print "error in ref"
      else:
        coords['x']=0.0
        coords['y']=0.0
        return coords
    elif 'rho' in self.dynamic:
      self.x=self.dynamic['rho']*math.cos(self.dynamic['theta'])
      self.y=self.dynamic['rho']*math.sin(self.dynamic['theta'])
    else:
      coords['x']=0.0
      coords['y']=0.0
      return coords
    if self.parent is not None:
      cs=self.parent.cartesianize(ref)   
      if 'x' in cs:
        coords['x']=self.x+cs['x']
        coords['y']=self.y+cs['y']
      else:
        coords['x']=self.x
        coords['y']=self.y
    self.xAU=self.x/AU2KM
    self.yAU=self.y/AU2KM
    return coords

  def debug(self):
    if self.parent is not None:
      self.parent.debug()   
    print "debugging: "+self.name+" at depth: "+str(self.depth) 
    if self.static is not None:
      print "..static: "+str(self.static)
    if self.dynamic is not None:
      print "..dynamic: "+str(self.dynamic)

  def refreshStack(self):
    global dataPlane
    global user
    if self.depth<=SEDEPTH:
      return None
    if self.parent is not None:
      self.parent.refreshStack()
    res=dataPlane.get(self.name)
    if res is None:  #item was evicted from cache, we put it back
      dataPlane.set(self.name,json.dumps(self.static))
#    res=self.static
    path=self.name
    path=path.replace(":","/")
    if self.depth==PLDEPTH:
      url=SYDNEUS+'/get/pl/elements/'+user+'/'+path
    elif self.depth==MODEPTH:
      url=SYDNEUS+'/get/mo/elements/'+user+'/'+path
    else:
      url=None  
    if (url is not None):
      try:
#        print url
        rs=urllib2.urlopen(url)
        rss=rs.read()
        r1=json.loads(rss)
#        print r1
        self.dynamic=r1
#        print "==="
      except urllib2.HTTPError, e:
        print "error"
        return None      

  def __init__(self,name):
    global dataPlane
    global user
    self.name=name
    self.initParentAndDepth(name)
#    print "my name: "+self.name+" my depth: "+str(self.depth)
    res=dataPlane.get(self.name)
    path=name
    path=path.replace(":","/")
    if self.depth==SUDEPTH:
      url=SYDNEUS+'/get/su/'+user+'/'+path
    elif self.depth==PLDEPTH:
      path0=path.split("/")
      url=SYDNEUS+'/list/pl/'+user+'/'+path0[0]+'/'+path0[1]+'/'+path0[2]
    elif self.depth==MODEPTH:
      path0=path.split("/")
      url=SYDNEUS+'/list/mo/'+user+'/'+path0[0]+'/'+path0[1]+'/'+path0[2]+'/'+path0[3]
    elif self.depth==SCDEPTH:
      url=SYDNEUS+'/get/spacecraft/'+user+'/'+path
    else:
      url=None
#      print "no url..."
    if ((res is None) and (url is not None)):
      try:
#        print url
        rs=urllib2.urlopen(url)
        rss=rs.read()
        r1=json.loads(rss)
#        print r1
        self.static=r1
        dataPlane.set(self.name,rss)
#        print "==="
      except urllib2.HTTPError, e:
        print "error"
        return None      
    elif res is not None:
      #self.static=json.loads(res)
      self.static=json.loads(res)
#      dataPlane.set(self.name,res)

class sc:
  name=''
  loc=locator;

  def __init__(self,name,parentLocatorName,ecc,smi,per,epoch,ano,spin,locked):
    global dataPlane
    global user
    self.name=name
    self.loc=locator(parentLocatorName+':'+name)
    static={}
    static['epoch']=t
    static['dayProgressAtEpoch']=1.0
    static['ano']=ano
    static['ecc']=ecc
    static['spin']=spin
    static['isLocked']=locked
    static['smi']=smi
    static['sma']=smi2sma(smi,ecc)
    if 'mEA' in self.loc.parent.static:
      static['period']=getOrbPeriod(static['sma'],self.loc.parent.static['mEA']*EAKG)
    elif 'mSU' in self.loc.parent.static:
      static['period']=getOrbPeriod(static['sma'],self.loc.parent.static['mSU']*SUKG)
    self.loc.static=static
#   regex=r":([a-zA-Z0-9\-]+)$"
#   match=re.search(regex,name)
#   self.name=match.group(1)
#   parentLocator=name.replace(match.group(0),"")
#   print parentLocator
   #self.loc=locator(self.name)

init()
art1=sc('Harfang','198:145:9w3',0.0,150000,0.0,t,0.0,0.0,True)
art2=sc('Cromwell','600:140:vFT:1',0.0,200000,0.0,t,0.0,0.0,True)
print art2.loc.static
sys.exit()
#a1=locator('600:140:4FN')
a1=locator('198:145:9w3')
a1.refreshStack()
#a1.debug()
a2=locator('600:140:vFT:1')
a2.refreshStack()
a2.debug()
d=a1.dist(a2)
print d
print d/LY2AU

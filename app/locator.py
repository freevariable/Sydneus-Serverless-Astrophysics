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
SHDEPTH=6
MODEPTH=5
PLDEPTH=4
SUDEPTH=3
SEDEPTH=2
AU2KM=149597871.0  # in km
LY2KM=9.4607E15
TWOPI=6.28318530718

dataPlaneId=6
controlPlaneId=7
user='admin'

import urllib2,redis,sys,json,math

def init():
  global dataPlane
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

  def distance(self,l2):
    d={}
    d['au']=math.sqrt((self.xAU - l2.xAU)**2 + (self.yAU - l2.yAU)**2)
    d['ly']=d['au']/63241.0
    return d

  def dSector(self,l2,depthDelta):
    return 0.0

  def dSu(self,l2,depthDelta):
    if depthDelta==0:
      return self.distance(l2)

  def dPl(self,l2,depthDelta):
    if depthDelta==0:
      return self.distance(l2)

  def dMo(self,l2,depthDelta):
    if depthDelta==0:
      return self.distance(l2)

  def dist(self,l2):
    d=0.0
    print self.cartesianize()
    print l2.cartesianize()
    interSector=False
    interSu=False
    interPl=False
    interMo=False
    ns1=self.name.split(":")
    ns2=l2.name.split(":")
    depthMin=min(self.depth,l2.depth)
    depthDelta=abs(self.depth-l2.depth)
#    print depthMin
    if ((ns1[0]==ns2[0]) and (ns1[1]==ns2[1])):
      print "same sector"
      if (ns1[2]==ns2[2]):
        print "same su"
        if depthMin>3:
         if (ns1[3]==ns2[3]):
           print "same pl"        
           if depthMin>4:
             if (ns1[4]==ns2[4]):
               print "same mo"        
             else:
               interMo=True 
         else:
           interPl=True
      else:
        interSu=True
    else:
      interSector=True
    if interSector:
      d=d+self.dSector(l2,depthDelta)['au']
    if interSu:
      d=d+self.dSu(l2,depthDelta)['au']
    if interPl:
      d=d+self.dPl(l2,depthDelta)['au']
    if interMo:
      d=d+self.dMo(l2,depthDelta)['au']
    d1={}
    d1['au']=d
    d1['ly']=d/63241
    return d1

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

  def cartesianize(self):
    coords={}
    if self.dynamic is None:
      if self.static is not None:
        if 'xly' in self.static:
          self.x=self.static['xly']*LY2KM
          self.y=self.static['yly']*LY2KM
      else:
        coords['x']=0.0
        coords['y']=0.0
        return coords
    elif 'rho' in self.dynamic:
      self.x=self.dynamic['rho']*math.cos(self.dynamic['theta'])
      self.y=self.dynamic['rho']*math.sin(self.dynamic['theta'])
#      print "***"
#      print self.name
#      print self.x
#      print self.y
    else:
      coords['x']=0.0
      coords['y']=0.0
      return coords
    if self.parent is not None:
      cs=self.parent.cartesianize()   
      if cs is not None:
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
    if self.parent is not None:
      self.parent.refreshStack()
    res=dataPlane.get(self.name)
    if res is None:  #item was evicted from cache, we put it back
      dataPlane.set(self.name,json.dumps(self.static))
    res=self.static
    path=self.name
    path=path.replace(":","/")
#    print "refreshing: "+self.name+" at depth: "+str(self.depth)
    if self.depth==PLDEPTH:
      url=SYDNEUS+'/get/pl/elements/'+user+'/'+path
#      print "..."+str(url)
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
      url=SYDNEUS+'/get/pl/'+user+'/'+path
    elif self.depth==MODEPTH:
      url=SYDNEUS+'/get/mo/'+user+'/'+path
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
#        print "==="
      except urllib2.HTTPError, e:
        print "error"
        return None      
    elif res is not None:
      self.static=json.loads(res)
      dataPlane.set(self.name,res)

init()
#a1=locator('400:29:RWh:1')
a1=locator('400:29:RWh')
a1.refreshStack()
#a1.debug()
#a2=locator('400:29:RWh:2')
a2=locator('400:29:jmj')
a2.refreshStack()
#a2.debug()
print a1.dist(a2)

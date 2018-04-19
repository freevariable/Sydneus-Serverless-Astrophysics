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

dataPlaneId=6
controlPlaneId=7
user='admin'

import urllib2,redis,sys,json

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

  def debug(self):
    print "debugging: "+self.name+" at depth: "+str(self.depth) 
    if self.parent is not None:
      self.parent.debug()   
    if self.static is not None:
      print "..static: "+str(self.static)
    if self.dynamic is not None:
      print "..dynamic: "+str(self.dynamic)

  def refreshStack(self):
    global dataPlane
    global user
    print "refreshing: "+self.name+" at depth: "+str(self.depth)
    if self.parent is not None:
      self.parent.refreshStack()
    res=dataPlane.get(self.name)
    if res is None:  #item was evicted from cache, we put it back
      dataPlane.set(self.name,json.dumps(self.static))
    path=self.name
    path=path.replace(":","/")
    if self.depth==PLDEPTH:
      url=SYDNEUS+'/get/pl/elements/'+user+'/'+path
    else:
      url=None  
    if ((res is None) and (url is not None)):
      try:
        print url
        rs=urllib2.urlopen(url)
        rss=rs.read()
        r1=json.loads(rss)
        print r1
        self.dynamic=r1
        print "==="
      except urllib2.HTTPError, e:
        print "error"
        return None      
    elif res is not None:
      self.dynamic=res 

  def __init__(self,name):
    global dataPlane
    global user
    self.name=name
    self.initParentAndDepth(name)
    print "my name: "+self.name+" my depth: "+str(self.depth)
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
      print "no url..."
    if ((res is None) and (url is not None)):
      try:
        print url
        rs=urllib2.urlopen(url)
        rss=rs.read()
        r1=json.loads(rss)
        print r1
        self.static=r1
        print "==="
      except urllib2.HTTPError, e:
        print "error"
        return None      
    elif res is not None:
      self.static=json.loads(res)
      dataPlane.set(self.name,res)

init()
aL=locator('400:29:RWh:1')
aL.refreshStack()
aL.debug()

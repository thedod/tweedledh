#!/usr/bin/python
WEBPORT='8933' # twee on cellular :)
STATIC_PATH='static'

### Diffie-Hellman session
import os, sys, time, marshal, base64, urllib, re, mimetypes

SECRET_DIGITS=24 # Number of chars to use as a shared secret
PUBLIC_DIGITS=6 # Number of chars for public verification

# P is the 768 bit prime from rfc 2412 (e.g. http://www.faqs.org/rfcs/rfc2412.html)
# BEWARE!!! it's easy to attack this script by modifying P. If you're not sure, check!
P = 1552518092300708935130918131258481755631334049434514313202351194902966239949102107258669453876591642442910007680288864229150803718918046342632727613031282983744380820890196288509170691316593175367469551763119843371637221007210577919

class DHSession:
    def __init__(self):
        try:
            import hashlib
            self.hash = hashlib.new('ripemd160')
            self.hash.update(str(time.time()))
        except ImportError: # python V<2.5
            import sha
            self.hash = sha.new(str(time.time()))
    
        try: # Windoze needs keyboard entropy
            import msvcrt # would fail on linux
            print "Need to generate random data. Please type randomly on the keyboard."
            junk = 'x'*128
            for keys in range(20):
                while not msvcrt.kbhit():
                    self.hash.update(junk)
                self.hash.update(msvcrt.getch())
            print "Got enough entropy. Thanks :-)"
        except ImportError: # linux and mac are easy
            self.hash.update(open('/dev/urandom').read(20))
        # Create private and public key
        self.priv=eval('0x'+self.hash.hexdigest())
        self.pub=pow(2,self.priv,P)
        self.pubstr=base64.encodestring(marshal.dumps(self.pub)).strip()
        self.tweedled,self.tweedleh=[urllib.quote(x) for x in self.pubstr.split('\n')]
        self.peertweedled=None
        self.peertweedleh=None
        self.peerpub=None
        self.dh=None
        self.sharedsecret=None
        self.pubverify=None
        self.peer_twitter=None
        self.use_dm=None

    def do_dh(self):
        try:
            self.peerpub=marshal.loads(base64.decodestring(self.peertweedled+self.peertweedleh))
            self.dh=str(pow(self.peerpub, self.priv, P))
            self.sharedsecret=self.dh[:SECRET_DIGITS]
            self.pubverify=self.dh[-PUBLIC_DIGITS:]
            return True
        except: # make sure shared secret becomes null
            self.sharedsecret=None
            self.pubverify=None
            return False

### Web server

import web
urls = (
    '/([dh])/(.+)','GetTweedle',
    '/peer_twitter','SetPeerTwitter',
    '/favicon.ico','FavIcon',
    '/static/(.+)','Static',
    '/','Index',
)

render = web.template.render('templates/')

dh = DHSession()

class Index:
    def GET(self):
        peer=dh.peer_twitter and '@'+dh.peer_twitter or None
        return render.index(WEBPORT,peer,dh.use_dm,dh.tweedled,dh.tweedleh,urllib.quote(dh.tweedled),urllib.quote(dh.tweedleh),dh.peertweedled,dh.peertweedleh,dh.sharedsecret,dh.pubverify)

class GetTweedle:
    def GET(self,tweedle,value):
        if tweedle=='d':
                dh.peertweedled=value
        elif tweedle=='h':
                dh.peertweedleh=value
        if dh.peertweedled and dh.peertweedleh:
                dh.do_dh()
        raise web.seeother('/')

TWITTER_PAT=re.compile('^[_0-9a-zA-z]{1,32}$')
class SetPeerTwitter:
    def POST(self):
        i=web.input(peer='',dm='')
        account=i.peer
        if TWITTER_PAT.match(account):
            dh.peer_twitter=account
            dh.use_dm=i.dm
        raise web.seeother('/')

class Static:
    def GET(self,filename):
        filename=os.path.basename(filename) # No ../ hanky panky
        web.header('Content-Type',mimetypes.guess_type(filename))
        return file(os.path.join((STATIC_PATH,filename))).read()

class FavIcon:
    def GET(self):
        raise web.seeother('/static/favicon.ico')

def NotFound():
    raise web.seeother('/')

if __name__ == "__main__":
    app = web.application(urls, globals())
    if len(sys.argv)==1:
        sys.argv.append('127.0.0.1:'+WEBPORT) # web.py has a funny way of doing business :)
    app.notfound = NotFound
    app.run()


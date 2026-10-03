"""Playful soundtrack for flow_v2 (8s): marimba-ish plucks, boings on hops, shutter, pops, ta-da."""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
SR=48000;DUR=8.0;N=int(SR*DUR);out=np.zeros((N,2));rng=np.random.default_rng(11)
def ar(n):return np.arange(int(n))/SR
def hz(m):return 440*2**((m-69)/12)
def bp(x,a,b):return sosfilt(butter(2,[a,b],'band',fs=SR,output='sos'),x)
def lp(x,f):return sosfilt(butter(2,f,'low',fs=SR,output='sos'),x)
def put(s,t0,g=1,pan=0):
    i=int(t0*SR);n=min(len(s),N-i)
    if n<=0:return
    l,r=np.cos((pan+1)*np.pi/4),np.sin((pan+1)*np.pi/4);out[i:i+n,0]+=s[:n]*g*l;out[i:i+n,1]+=s[:n]*g*r
def mar(m,d=.5):  # marimba-ish
    x=ar(d*SR);f=hz(m);return (np.sin(2*np.pi*f*x)+.3*np.sin(2*np.pi*f*4*x)*np.exp(-x*30))*np.exp(-x*9)*np.minimum(1,x*500)
def pop(f=900):
    x=ar(.09*SR);return np.sin(2*np.pi*(f+f*2*np.exp(-x*60))*x)*np.exp(-x*45)
def boing(up=True):
    x=ar(.35*SR);f=300+(500 if up else -150)*x/.35+40*np.sin(2*np.pi*14*x);return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*6)
def shutter():
    x=ar(.18*SR);n=bp(rng.standard_normal(len(x)),2000,9000);return n*(np.exp(-x*80)+.7*np.exp(-np.abs(x-.07)*200))
# bouncy bassline + plucky chords at 120bpm (C major-ish, happy)
prog=[(48,[60,64,67]),(53,[60,65,69]),(55,[59,62,67]),(48,[60,64,67])]
for bar in range(4):
    root,ch=prog[bar]
    for k in range(4):
        t0=bar*2+k*.5
        if t0>=7.6:break
        put(mar(root-12+(7 if k%2 else 0),.4)*1.0,t0,.35)
        if k in(1,3):
            for j,m in enumerate(ch):put(mar(m,.35),t0+j*.012,.16,pan=(j-1)*.4)
    # light shaker on 8ths
    for k in range(8):
        x=ar(.05*SR);put(bp(rng.standard_normal(len(x)),5000,11000)*np.exp(-x*70),bar*2+k*.25,.06 if k%2 else .1,pan=.3)
# title + sparkles pops
put(pop(700),.1,.5);[put(pop(1200+i*300),.35+i*.12,.3,pan=(i-1)*.5) for i in range(3)]
# stations pop in
for i in range(4):put(pop(600+i*150),.8+i*.25,.45,pan=-.6+i*.4);put(mar(72+[0,2,4,7][i],.3),.8+i*.25,.2)
# mascot drop + hops + landings
put(boing(False),1.4,.4);put(pop(250),1.9,.6)
for s in range(3):
    put(boing(True),2.4+s,.35,pan=-.3+s*.3);put(pop(260),2.9+s,.55)
# station events
for i,m in enumerate([76,79,83,88]):put(mar(m,.6),1.9+i*.25*0+[0,0,0,0][i]+0,0)  # placeholder no-op
put(mar(84,.6),1.95,.3);put(mar(88,.6),2.05,.25)                     # heart appears
put(shutter(),2.9,.7)                                                 # 咔嚓
for i in range(4):put(pop(900+i*120),3.0+i*.08,.3,pan=-.4+i*.25)      # frames fly out
for i,m in enumerate([79,83,86,91,88]):put(mar(m,.5),3.95+i*.07,.28,pan=(i-2)*.3)  # notes burst
# ta-da + confetti crackle at 4.9
for j,m in enumerate([72,76,79,84]):put(mar(m,1.2),4.9+j*.04,.3,pan=(j-1.5)*.3)
x=ar(1.0*SR);cr=bp(rng.standard_normal(len(x)),3000,10000)*(rng.random(len(x))<.02)*np.exp(-x*3);put(cr*8,4.95,.25)
# cheer bounces + caption
for k in range(4):put(pop(500),5.3+k*.5,.25)
put(pop(800),5.6,.5);put(mar(84,.8),5.65,.25)
wet=np.zeros_like(out)
for d,g in[(.029,.3),(.053,.22),(.083,.16)]:
    k=int(d*SR);wet[k:,0]+=lp(out[:-k,1],6000)*g;wet[k:,1]+=lp(out[:-k,0],6000)*g
out=np.tanh((out+wet*.5)*1.2);out*=np.clip((DUR-ar(N))/0.4,0,1)[:,None];out/=np.max(np.abs(out))/0.88
wavfile.write("out/flow_v2.wav",SR,(out*32767).astype(np.int16));print("ok")

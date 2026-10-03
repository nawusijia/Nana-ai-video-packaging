"""120bpm hit-driven soundtrack for nausicaa_v2 (6s). Every sound sits on an animation event."""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
SR=48000; DUR=6.0; N=int(SR*DUR)
out=np.zeros((N,2)); rng=np.random.default_rng(3)
def lp(x,f): return sosfilt(butter(2,f,'low',fs=SR,output='sos'),x)
def hp(x,f): return sosfilt(butter(2,f,'high',fs=SR,output='sos'),x)
def bp(x,a,b): return sosfilt(butter(2,[a,b],'band',fs=SR,output='sos'),x)
def ar(n): return np.arange(n)/SR
def put(sig,t0,g=1,pan=0):
    i=int(t0*SR); n=min(len(sig),N-i)
    if n<=0: return
    l,r=np.cos((pan+1)*np.pi/4),np.sin((pan+1)*np.pi/4)
    out[i:i+n,0]+=sig[:n]*g*l; out[i:i+n,1]+=sig[:n]*g*r
def kick(n=0.6):
    x=ar(int(n*SR)); return np.tanh(2.2*np.sin(2*np.pi*(48*x+140/28*(1-np.exp(-x*28))))*np.exp(-x*5.5))
def snare():
    x=ar(int(.35*SR)); return bp(rng.standard_normal(len(x)),1500,9000)*np.exp(-x*16)+np.sin(2*np.pi*190*x)*np.exp(-x*25)*.6
def hat(d=30):
    x=ar(int(.08*SR)); return hp(rng.standard_normal(len(x)),7000)*np.exp(-x*d)
def whoosh(dur,up=True):
    x=ar(int(dur*SR)); n=rng.standard_normal(len(x)); k=x/dur
    s=np.zeros_like(x)
    for i,(a,b) in enumerate([(200,700),(700,2000),(2000,6000),(6000,12000)]):
        w=np.clip(1-abs((k if up else 1-k)*4-i-0.5)/1.2,0,1); s+=bp(n,a,b)*w
    return s*np.sin(np.pi*k)
def hz(m): return 440*2**((m-69)/12)
def stab(notes,dur=1.2,bright=3000):
    x=ar(int(dur*SR)); s=np.zeros_like(x)
    for m in notes:
        for d in(-.1,0,.1): s+=2*((x*hz(m+d))%1)-1
    return lp(s/len(notes)/3,bright)*np.exp(-x*3)
def sub(dur=1.6):
    x=ar(int(dur*SR)); return np.sin(2*np.pi*(38+30*np.exp(-x*6))*x)*np.exp(-x*1.6)

# intro: dot drop (falling pitch blip), impact at .38, line stretch zip, wipe-open whoosh
x=ar(int(.38*SR)); put(np.sin(2*np.pi*(1400-1100*x/.38)*x)*.3*np.minimum(1,x*40),0.0,.5)
put(kick(.4),.38,.7); put(hat(60),.38,.6)
put(whoosh(.35),.42,.5); put(whoosh(.45,up=False),.55,.45)
# beat grid 120bpm from 1.0: kick every beat, hats on 8ths, snare on 2 & 4
for i in range(8):
    tb=1.0+i*.5
    if tb>=4.5: break
    put(kick(),tb,.85)
    put(hat(),tb+.25,.35,pan=.3); put(hat(45),tb,.25,pan=-.3)
    if i%2==1: put(snare(),tb,.55)
# word slams: short tonal stab on each word entrance
for t0,ch in [(1.0,[57,64]),(1.5,[60,67,72]),(2.0,[55,62]),(2.5,[57,64]),(2.75,[59,66])]:
    put(stab(ch,.5,2600),t0,.22)
# riser into 包装
x=ar(int(.75*SR)); r=bp(rng.standard_normal(len(x)),800,9000)*(x/.75)**2
r+=np.sin(2*np.pi*(200*x+900*x*x))*(x/.75)**2*.3; put(r,2.75,.35)
# drop at 3.5: sub + big chord + crash
put(sub(),3.5,.9); put(kick(),3.5,1.0)
put(stab([45,52,57,61,64,69],1.8,4200),3.5,.4)
x=ar(int(1.6*SR)); put(hp(rng.standard_normal(len(x)),5000)*np.exp(-x*2.4),3.5,.35)
# 4.45 circle swallow: reverse-ish whoosh + low thump
put(whoosh(.5),4.2,.5); put(kick(.8),4.7,.7)
# 4.75 lockup: orange block swipe + reveal tick, then airy chord tail
put(whoosh(.25),4.75,.4); put(whoosh(.25,up=False),5.0,.35)
for i,m in enumerate([81,86,88,93]):
    x=ar(int(1.2*SR)); b=sum(a*np.sin(2*np.pi*hz(m)*k*x)*np.exp(-x*d) for k,a,d in [(1,1,3),(2.01,.4,5),(3.02,.2,7)])
    put(b,5.15+i*.06,.09,pan=(i-1.5)*.3)
put(stab([57,64,69,73,76],1.0,2000),5.15,.2)
# glue: short room + soft clip + tail fade
wet=np.zeros_like(out)
for dly,g in [(.023,.3),(.041,.25),(.067,.2),(.109,.15)]:
    k=int(dly*SR); wet[k:,0]+=lp(out[:-k,1],5000)*g; wet[k:,1]+=lp(out[:-k,0],5000)*g
out=np.tanh((out+wet*.5)*1.1)
out*=np.clip((DUR-ar(N))/0.3,0,1)[:,None]
out/=np.max(np.abs(out))/0.9
wavfile.write("out/nausicaa_v2.wav",SR,(out*32767).astype(np.int16)); print("ok")

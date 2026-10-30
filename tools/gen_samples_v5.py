# -*- coding: utf-8 -*-
"""v5: NumPy gradient engine + PIL compositing / blur / font"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os, math

OUT = r"F:\mini api\shots"
CELL, PAD = 56, 24
GRID_W, GRID_H = 10, 8
W = CELL * GRID_W + PAD * 2
H = CELL * GRID_H + PAD * 2
SS = 2

MAP_DATA = [
    (1,1,"lowland"),(1,2,"lowland"),(1,3,"highland"),(1,4,"highland"),(1,5,"road"),(1,6,"road"),(1,7,"lowland"),(1,8,"lowland"),
    (2,1,"lowland"),(2,2,"wall"),(2,3,"wall"),(2,4,"lowland"),(2,5,"road"),(2,6,"road"),(2,7,"highland"),(2,8,"highland"),
    (3,1,"highland"),(3,2,"wall"),(3,3,"hole"),(3,4,"lowland"),(3,5,"lowland"),(3,6,"lowland"),(3,7,"highland"),(3,8,"highland"),
    (4,1,"highland"),(4,2,"lowland"),(4,3,"lowland"),(4,4,"deepwater"),(4,5,"deepwater"),(4,6,"lowland"),(4,7,"lowland"),(4,8,"wall"),
    (5,1,"highland"),(5,2,"highland"),(5,3,"lowland"),(5,4,"deepwater"),(5,5,"deepwater"),(5,6,"lowland"),(5,7,"lowland"),(5,8,"wall"),
    (6,1,"lowland"),(6,2,"highland"),(6,3,"highland"),(6,4,"lowland"),(6,5,"lowland"),(6,6,"highland"),(6,7,"hole"),(6,8,"lowland"),
    (7,1,"lowland"),(7,2,"lowland"),(7,3,"highland"),(7,4,"highland"),(7,5,"wall"),(7,6,"wall"),(7,7,"lowland"),(7,8,"lowland"),
]
SPAWNS=[(1,1,5),(8,1,3)]
GOALS=[(8,6,None)]
ROUTES=[
    [(1,1),(1,2),(1,3),(2,3),(3,3),(3,4),(3,5),(4,5),(5,5),(6,5),(6,6),(7,6),(8,6)],
    [(8,1),(8,2),(8,3),(8,4),(8,5),(7,5),(6,5),(5,5),(4,5),(3,5),(3,4),(3,3),(2,3),(1,3),(1,2),(1,1)],
]
MECHANISMS=[(3,5,"box"),(5,3,"trap"),(7,4,"heal"),(4,7,"damage"),(2,6,"portal"),(6,2,"support")]

def px(c,r): return PAD+(c-1)*CELL, PAD+(GRID_H-r)*CELL
def ppx(c,r): return px(c,r)[0]*SS, px(c,r)[1]*SS

def fnt(sz,bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc",sz) if bold else ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",sz)
    except:
        try: return ImageFont.truetype("C:/Windows/Fonts/simhei.ttf",sz)
        except: return ImageFont.load_default()

# ── Numpy Gradient Engine ──
def grad_box(w,h,tl,tr,bl,br):
    ys=np.linspace(0,1,h)[:,None]; xs=np.linspace(0,1,w)[None,:]
    top=tl[:,None]*(1-xs)+tr[:,None]*xs; bot=bl[:,None]*(1-xs)+br[:,None]*xs
    img=top[:,:,None]*(1-ys)+bot[:,:,None]*ys
    return np.clip(np.round(np.transpose(img,(2,1,0))),0,255).astype(np.uint8)

def grad_bevel(w,h,base,hi,sh,bv):
    ba=np.array(base,np.float64); hi_a=np.array(hi,np.float64); sh_a=np.array(sh,np.float64)
    res=np.full((h,w,3),ba)
    if bv>0 and h>bv*2:
        for i in range(bv):
            t=(bv-i)/bv; row=hi_a*t+ba*(1-t); res[i,:]=row
        for i in range(bv):
            t=(bv-i)/bv; col=hi_a*t+ba*(1-t); res[:,i]=col
        for i in range(bv):
            t=(i+1)/(bv+1); row=ba*(1-t)+sh_a*t; res[h-1-i,:]=row
        for i in range(bv):
            t=(i+1)/(bv+1); col=ba*(1-t)+sh_a*t; res[:,w-1-i]=col
    return np.clip(np.round(res),0,255).astype(np.uint8)

def add_noise(arr,strng,seed):
    rng=np.random.RandomState(seed)
    n=rng.randint(-strng,strng+1,arr.shape,np.int16)
    return np.clip(arr.astype(np.int16)+n,0,255).astype(np.uint8)

# ── Palette ──
PAL={
    "lowland":((52,48,44),(62,58,52),(42,38,34)),
    "highland":((68,64,56),(80,76,68),(56,52,46)),
    "wall":((40,38,34),(50,48,42),(32,30,26)),
    "deepwater":((28,54,72),(40,70,92),(20,40,54)),
    "hole":((16,14,12),(24,22,18),(10,8,6)),
    "road":((60,56,50),(72,68,60),(48,44,40)),
}

def make_tile(ttype,sz,seed_val):
    p=PAL.get(ttype,PAL["lowland"])
    arr=grad_box(sz,sz,np.array(p[0]),np.array(p[1]),np.array(p[2]),np.array(p[2]))
    arr=add_noise(arr,8,seed_val)
    img=Image.fromarray(arr,"RGB")
    d=ImageDraw.Draw(img); b=p[0]
    d.line([(0,0),(sz-1,0)],fill=tuple(min(255,v+10)for v in b),width=1)
    d.line([(0,0),(0,sz-1)],fill=tuple(min(255,v+10)for v in b),width=1)
    d.line([(0,sz-1),(sz-1,sz-1)],fill=tuple(max(0,v-14)for v in b),width=1)
    d.line([(sz-1,0),(sz-1,sz-1)],fill=tuple(max(0,v-14)for v in b),width=1)
    return img

# ── 3D Door ──
def make_door(sz,is_red=True,count=None):
    m=6; dsz=sz-m*2; bv=min(9,dsz//5)
    if is_red:
        base=(200,55,45);hi_t=(255,140,120);hi_l=(255,160,140);sh_b=(140,32,24);sh_r=(130,28,22)
        go_o=(140,30,18);go_i=(220,80,60)
    else:
        base=(50,110,210);hi_t=(130,180,255);hi_l=(150,200,255);sh_b=(28,68,140);sh_r=(24,58,120)
        go_o=(30,65,140);go_i=(80,150,255)
    tot=dsz+20; cvs=Image.new("RGBA",(tot,tot),(0,0,0,0))
    ox=(tot-dsz)//2; oy=(tot-dsz)//2
    # Glow
    gl=Image.new("RGBA",(dsz+12,dsz+12),(0,0,0,0)); gd=ImageDraw.Draw(gl)
    gd.rounded_rectangle([0,0,dsz+11,dsz+11],radius=bv+6,fill=(*go_o,180))
    gd.rounded_rectangle([4,4,dsz+7,dsz+7],radius=bv+4,fill=(*go_i,160))
    cvs.paste(gl.filter(ImageFilter.GaussianBlur(radius=7)),(ox-6,oy-6),gl)
    # Face
    face_arr=grad_bevel(dsz,dsz,base,hi_l,sh_r,bv)
    face=Image.fromarray(face_arr,"RGB")
    fd=ImageDraw.Draw(face); ih=tuple(min(255,v+35)for v in base)
    if bv+2<dsz-bv-2:
        fd.line([(bv+2,bv+2),(dsz-bv-3,bv+2)],fill=ih,width=1)
        fd.line([(bv+2,bv+2),(bv+2,dsz-bv-3)],fill=ih,width=1)
    mk=Image.new("L",(dsz,dsz),0); md=ImageDraw.Draw(mk)
    md.rounded_rectangle([0,0,dsz-1,dsz-1],radius=bv,fill=255)
    cvs.paste(face,(ox,oy),mk)
    # Text
    if count is not None:
        ti=Image.new("RGBA",(dsz,dsz),(0,0,0,0)); td=ImageDraw.Draw(ti); bf=fnt(dsz//3,True)
        txt=str(count); bb=bf.getbbox(txt)
        tw=bb[2]-bb[0]if bb else dsz//3; th=bb[3]-bb[1]if bb else dsz//4
        tx=(dsz-tw)//2-bb[0]if bb else dsz//4; ty=(dsz-th)//2-bb[1]if bb else dsz//4
        td.text((tx+2,ty+2),txt,fill=(0,0,0,180),font=bf)
        td.text((tx,ty),txt,fill=(255,255,255,255),font=bf)
        cvs.paste(ti,(ox,oy),ti)
    return cvs

# ── Devices ──
def dev_box(sz):
    m=7;b=sz-m*2;t=b+16;cvs=Image.new("RGBA",(t,t),(0,0,0,0)); ox=(t-b)//2;oy=(t-b)//2
    sh=Image.new("L",(b+4,b+4),0); sd=ImageDraw.Draw(sh); sd.rounded_rectangle([2,2,b+2,b+2],radius=6,fill=100)
    cvs.paste((0,0,0,120),(ox+2,oy+2),sh.filter(ImageFilter.GaussianBlur(radius=4)))
    fa=grad_bevel(b,b,(165,125,78),(215,172,120),(115,80,48),5); fa=add_noise(fa,12,42)
    fp=Image.fromarray(fa,"RGB"); fd=ImageDraw.Draw(fp); tc=tuple(max(0,v-25)for v in(165,125,78))
    for i in range(b):
        if b//3<i<2*b//3: fd.point((b//3,i),fill=tc); fd.point((2*b//3,i),fill=tc)
        if b//3<i<2*b//3: fd.point((i,b//3),fill=tc); fd.point((i,2*b//3),fill=tc)
    mk=Image.new("L",(b,b),0); md=ImageDraw.Draw(mk); md.rounded_rectangle([0,0,b-1,b-1],radius=5,fill=255)
    cvs.paste(fp,(ox,oy),mk); return cvs

def dev_trap(sz):
    m=8;ts=sz-m*2;t=ts+16;cvs=Image.new("RGBA",(t,t),(0,0,0,0)); ox=(t-ts)//2;oy=(t-ts)//2
    sh=Image.new("L",(ts+4,ts+4),0); sd=ImageDraw.Draw(sh); sd.ellipse([1,1,ts+3,ts+3],fill=90)
    cvs.paste((0,0,0,100),(ox+2,oy+2),sh.filter(ImageFilter.GaussianBlur(radius=3)))
    cx,cy=ts//2,ts//2; y,x=np.ogrid[:ts,:ts]
    dist=np.sqrt((x-cx)**2+(y-cy)**2)/(ts*0.5); dist=np.clip(dist,0,1)
    ring=1-np.abs(dist-0.5)*2; val=(155*ring+100*(1-ring)).clip(0,255).astype(np.uint8)
    face=np.stack([val,val,val+2],axis=-1); fp=Image.fromarray(face,"RGB"); d=ImageDraw.Draw(fp)
    d.ellipse([4,4,ts-5,ts-5],outline=(100,100,105),width=2)
    d.ellipse([8,8,ts-9,ts-9],outline=(170,170,175),width=1)
    for ang in range(0,360,45):
        rad=math.radians(ang-90)
        for r in range(ts//2-8,ts//3,-1):
            spx=cx+int(r*math.cos(rad)); spy=cy+int(r*math.sin(rad))
            if 0<=spx<ts and 0<spy<ts: fp.putpixel((spx,spy),(200,200,205))
    d.ellipse([cx-5,cy-5,cx+5,cy+5],fill=(230,55,45)); d.ellipse([cx-2,cy-2,cx+2,cy+2],fill=(255,180,170))
    mk=Image.new("L",(ts,ts),0); md=ImageDraw.Draw(mk); md.ellipse([0,0,ts-1,ts-1],fill=255)
    cvs.paste(fp,(ox,oy),mk); return cvs

def dev_heal(sz):
    m=6;hs=sz-m*2;t=hs+16;cvs=Image.new("RGBA",(t,t),(0,0,0,0)); ox=(t-hs)//2;oy=(t-hs)//2
    gl=Image.new("RGBA",(hs+8,hs+8),(0,0,0,0)); gd=ImageDraw.Draw(gl)
    gd.rounded_rectangle([-2,-2,hs+6,hs+6],radius=hs//3+4,fill=(40,180,90,55))
    cvs.paste(gl.filter(ImageFilter.GaussianBlur(radius=6)),(ox-4,oy-4),gl)
    fa=grad_bevel(hs,hs,(48,155,85),(90,210,130),(30,100,52),4)
    fp=Image.fromarray(fa,"RGB"); d=ImageDraw.Draw(fp)
    cw,ch=hs//4,hs//2; cx1,cy2=hs//4,3*hs//4; cy1=hs//4
    d.rectangle([cx1,cy2-ch//2,cx1+cw,cy2+ch//2],fill=(255,255,255))
    d.rectangle([cy2-ch//2,cy1,cy2+ch//2,cy1+ch],fill=(255,255,255))
    mk=Image.new("L",(hs,hs),0); md=ImageDraw.Draw(mk); md.rounded_rectangle([0,0,hs-1,hs-1],radius=hs//3,fill=255)
    cvs.paste(fp,(ox,oy),mk); return cvs

def dev_damage(sz):
    m=6;ds=sz-m*2;t=ds+16;cvs=Image.new("RGBA",(t,t),(0,0,0,0)); ox=(t-ds)//2;oy=(t-ds)//2
    gl=Image.new("RGBA",(ds+8,ds+8),(0,0,0,0)); gd=ImageDraw.Draw(gl)
    gd.rounded_rectangle([-2,-2,ds+6,ds+6],radius=ds//3+4,fill=(200,50,30,45))
    cvs.paste(gl.filter(ImageFilter.GaussianBlur(radius=6)),(ox-4,oy-4),gl)
    fa=grad_bevel(ds,ds,(185,55,45),(240,100,80),(120,30,22),4)
    fp=Image.fromarray(fa,"RGB"); d=ImageDraw.Draw(fp)
    mx,my=ds//2,ds//2; tr=ds//3
    d.polygon([(mx,my-tr),(mx-tr,my+int(tr/1.5)),(mx+tr,my+int(tr/1.5))],fill=(255,225,100))
    d.polygon([(mx,my-tr+4),(mx-tr+4,my+int(tr/1.5)-2),(mx+tr-4,my+int(tr/1.5)-2)],fill=(180,50,35))
    mk=Image.new("L",(ds,ds),0); md=ImageDraw.Draw(mk); md.rounded_rectangle([0,0,ds-1,ds-1],radius=ds//3,fill=255)
    cvs.paste(fp,(ox,oy),mk); return cvs

def dev_portal(sz):
    m=5;ps=sz-m*2;t=ps+20;cvs=Image.new("RGBA",(t,t),(0,0,0,0)); ox=(t-ps)//2;oy=(t-ps)//2
    for gr,ga,gc in[(14,35,(70,30,130)),(10,65,(100,50,170)),(6,110,(140,80,210))]:
        g=Image.new("RGBA",(ps,ps),(0,0,0,0)); gd=ImageDraw.Draw(g)
        gd.ellipse([gr,gr,ps-gr,ps-gr],fill=(*gc,ga))
        cvs.paste(g.filter(ImageFilter.GaussianBlur(radius=gr//2+2)),(ox,oy),g)
    face=Image.new("RGBA",(ps,ps),(0,0,0,0)); d=ImageDraw.Draw(face)
    d.ellipse([2,2,ps-2,ps-2],fill=(55,25,100,230))
    d.ellipse([6,6,ps-6,ps-6],outline=(100,55,180),width=2)
    d.ellipse([10,10,ps-10,ps-10],outline=(140,90,210),width=2)
    cr=ps//3
    d.ellipse([ps//2-cr,ps//2-cr,ps//2+cr,ps//2+cr],fill=(190,150,255,255))
    d.ellipse([ps//2-cr//2,ps//2-cr//2,ps//2+cr//2,ps//2+cr//2],fill=(230,210,255,255))
    d.arc([4,4,ps-4,ps-4],start=30,end=150,fill=(170,120,240,200),width=2)
    d.arc([8,8,ps-8,ps-8],start=210,end=330,fill=(170,120,240,200),width=2)
    cvs.paste(face,(ox,oy),face); return cvs

def dev_support(sz):
    m=6;ss=sz-m*2;t=ss+16;cvs=Image.new("RGBA",(t,t),(0,0,0,0)); ox=(t-ss)//2;oy=(t-ss)//2
    d=ImageDraw.Draw(cvs)
    px_o,py_o=ox,oy
    d.rectangle([px_o+ss//2+3,py_o+7,px_o+ss//2+6,py_o+ss-2],fill=(15,22,32,160))
    ph=ss-12
    for row in range(ph):
        f=row/ph if ph>0 else 0; c=tuple(int(v+f*40)for v in(180,188,195))
        d.rectangle([px_o+ss//2-2,py_o+5+row,px_o+ss//2+1,py_o+6+row],fill=c)
    fh=ss//3; flag=Image.new("RGBA",(ss//2,fh+4),(0,0,0,0)); fd=ImageDraw.Draw(flag)
    fd.polygon([(2,0),(ss//2-2,fh//2),(2,fh)],fill=(50,130,230,255))
    fd.polygon([(2,1),(ss//2-4,fh//2-1),(2,fh-1)],fill=(100,175,255,180))
    cvs.paste(flag,(px_o+ss//2,py_o+2),flag)
    d.rectangle([px_o+ss//5,py_o+ss-6,px_o+4*ss//5,py_o+ss-2],fill=(95,100,112))
    d.line([(px_o+ss//5,py_o+ss-6),(px_o+4*ss//5,py_o+ss-6)],fill=(140,148,160),width=1)
    return cvs

DEVS={"box":dev_box,"trap":dev_trap,"heal":dev_heal,"damage":dev_damage,"portal":dev_portal,"support":dev_support}

# ── Routes ──
def draw_routes(layer,routes,scale=1):
    d=ImageDraw.Draw(layer)
    for ri,rt in enumerate(routes):
        co=(70,155,255)if ri==0 else(255,90,80); gl=tuple(v//3 for v in co)
        pts=[(px(a,b)[0]*scale,px(a,b)[1]*scale)for a,b in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=(*gl,90),width=7*scale)
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=co,width=3*scale)
        for cc,rr in rt:
            xx,yy=px(cc,rr)[0]*scale,px(cc,rr)[1]*scale
            d.ellipse([xx-4*scale,yy-4*scale,xx+4*scale,yy+4*scale],fill=(*gl,110))
            d.ellipse([xx-2*scale,yy-2*scale,xx+2*scale,yy+2*scale],fill=co)

# ── Paste helper ──
def paste_on(img_rgba,overlay,col,row):
    xx,yy=ppx(col,row)
    dw,dh=overlay.size
    dx=xx-(dw-CELL*SS)//2; dy=yy-(dh-CELL*SS)//2
    tmp=Image.new("RGBA",(img_rgba.size[0],img_rgba.size[1]),(0,0,0,0))
    tmp.paste(overlay,(dx,dy),overlay)
    return Image.alpha_composite(img_rgba,tmp)

# ── Main render ──
def render(name,bg,title,sub,tf,sf,bar):
    WW,HH=W*SS,H*SS
    base=Image.new("RGB",(WW,HH),bg)
    # Tiles
    for r,c,t in MAP_DATA:
        tile=make_tile(t,CELL*SS,seed_val=r*100+c)
        x,y=ppx(c,r)
        base.paste(tile,(x,y))
        d=ImageDraw.Draw(base)
        d.text((x+6,y+4),f"{chr(64+c)},{r}",fill=(110,105,98),font=fnt(11*SS))
    # Overlay layer (routes + doors + devices)
    ovl=Image.new("RGBA",(WW,HH),(0,0,0,0))
    draw_routes(ovl,ROUTES,scale=SS)
    for c,r,n in SPAWNS: ovl=paste_on(ovl,make_door(CELL*SS,is_red=True,count=n),c,r)
    for c,r,_ in GOALS: ovl=paste_on(ovl,make_door(CELL*SS,is_red=False,count=None),c,r)
    for c,r,mt in MECHANISMS:
        fn=DEVS.get(mt)
        if fn: ovl=paste_on(ovl,fn(CELL*SS),c,r)
    # Composite
    cvs=base.convert("RGBA")
    cvs=Image.alpha_composite(cvs,ovl)
    cvs=cvs.convert("RGB")
    # Title bar
    d=ImageDraw.Draw(cvs)
    d.rectangle([0,0,WW,36*SS],fill=bar)
    d.text((12*SS,8*SS),title,fill=tf,font=fnt(16*SS))
    d.text((W*SS-250*SS,12*SS),sub,fill=sf,font=fnt(11*SS))
    # Downsample
    out=cvs.resize((W,H),Image.LANCZOS)
    fname=os.path.join(OUT,f"sample_{name.lower()}.png")
    out.save(fname,quality=95)
    print(f"[OK] {name} -> {fname} ({os.path.getsize(fname)} bytes)")

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    render("G",(20,22,26),
        "Style G: Numpy Engine / Flat Tiles / Real 3D Doors + Devices",
        "numpy gradients / gaussian glow / noise texture / 2x AA",
        (210,205,198),(110,105,98),(26,28,32))
    print("Done!")
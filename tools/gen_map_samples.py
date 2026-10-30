# -*- coding: utf-8 -*-
"""Map canvas PRTS style sample generator"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"F:\mini api\shots"
CELL, PAD = 56, 24
GRID_W, GRID_H = 10, 8
W = CELL * GRID_W + PAD * 2
H = CELL * GRID_H + PAD * 2

MAP_DATA = [
    (1,1,'lowland'),(1,2,'lowland'),(1,3,'highland'),(1,4,'highland'),(1,5,'road'),(1,6,'road'),(1,7,'lowland'),(1,8,'lowland'),
    (2,1,'lowland'),(2,2,'wall'),(2,3,'wall'),(2,4,'lowland'),(2,5,'road'),(2,6,'road'),(2,7,'highland'),(2,8,'highland'),
    (3,1,'highland'),(3,2,'wall'),(3,3,'hole'),(3,4,'lowland'),(3,5,'lowland'),(3,6,'lowland'),(3,7,'highland'),(3,8,'highland'),
    (4,1,'highland'),(4,2,'lowland'),(4,3,'lowland'),(4,4,'deepwater'),(4,5,'deepwater'),(4,6,'lowland'),(4,7,'lowland'),(4,8,'wall'),
    (5,1,'highland'),(5,2,'highland'),(5,3,'lowland'),(5,4,'deepwater'),(5,5,'deepwater'),(5,6,'lowland'),(5,7,'lowland'),(5,8,'wall'),
    (6,1,'lowland'),(6,2,'highland'),(6,3,'highland'),(6,4,'lowland'),(6,5,'lowland'),(6,6,'highland'),(6,7,'hole'),(6,8,'lowland'),
    (7,1,'lowland'),(7,2,'lowland'),(7,3,'highland'),(7,4,'highland'),(7,5,'wall'),(7,6,'wall'),(7,7,'lowland'),(7,8,'lowland'),
]
SPAWNS = [(1,1,5),(8,1,3)]
GOALS = [(8,6,None)]
ROUTES = [
    [(1,1),(1,2),(1,3),(2,3),(3,3),(3,4),(3,5),(4,5),(5,5),(6,5),(6,6),(7,6),(8,6)],
    [(8,1),(8,2),(8,3),(8,4),(8,5),(7,5),(6,5),(5,5),(4,5),(3,5),(3,4),(3,3),(2,3),(1,3),(1,2),(1,1)],
]

def px(c,r): return PAD+(c-1)*CELL, PAD+(GRID_H-r)*CELL
def crect(c,r):
    x,y=px(c,r); return [x,y,x+CELL,y+CELL]

def font(sz,bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc",sz) if bold else ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",sz)
    except:
        try: return ImageFont.truetype("C:/Windows/Fonts/simhei.ttf",sz)
        except: return ImageFont.load_default()

def draw_current():
    im=Image.new('RGB',(W,H),(23,27,34)); d=ImageDraw.Draw(im)
    P={'lowland':((58,72,94),(74,90,116)),'highland':((104,122,150),(128,148,178)),
       'wall':((104,100,98),(128,124,122)),'deepwater':((26,62,84),(36,82,108)),
       'hole':((8,10,14),(12,15,20)),'road':((70,84,112),(86,102,134))}
    for r,c,t in MAP_DATA:
        b,h=P.get(t,P['lowland']); cr=crect(c,r); d.rectangle(cr,fill=b)
        d.line([cr[0],cr[1],cr[2]-1,cr[1]],fill=h,width=2)
        d.line([cr[0],cr[1],cr[0],cr[3]-1],fill=h,width=2)
        dk=tuple(max(0,v-30) for v in b)
        d.line([cr[0],cr[3]-1,cr[2]-1,cr[3]-1],fill=dk,width=2)
        d.line([cr[2]-1,cr[1],cr[2]-1,cr[3]-1],fill=dk,width=2)
        x,y=px(c,r); d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(120,132,154))
    for ri,rt in enumerate(ROUTES):
        co=(92,176,255) if ri==0 else (231,76,60)
        pts=[px(a,b) for a,b in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=co,width=3)
        for c,r in rt:
            x,y=px(c,r); d.ellipse([x+24-5,y+24-5,x+24+5,y+24+5],outline=co,width=2)
    for c,r,n in SPAWNS:
        x,y=px(c,r); d.ellipse([x+8,y+8,x+CELL-8,y+CELL-8],outline=(214,68,56),width=3)
        if n: d.text((x+24-6,y+24-8),str(n),fill=(214,68,56))
    for c,r,_ in GOALS:
        x,y=px(c,r); d.rectangle([x+8,y+8,x+CELL-8,y+CELL-8],outline=(56,132,224),width=3)
    d.rectangle([0,0,W,32],fill=(17,21,28))
    d.text((12,6),"Current Style (Blue-grey 3D)",fill=(232,236,241),font=font(16))
    im.save(os.path.join(OUT,"sample_current.png"),quality=95); print("[OK] current")

def draw_prts_light():
    im=Image.new('RGB',(W,H),(245,243,235)); d=ImageDraw.Draw(im)
    P={'lowland':((224,220,208),(240,236,228)),'highland':((188,182,172),(210,204,194)),
       'wall':((148,140,130),(168,160,150)),'deepwater':((164,196,212),(188,216,232)),
       'hole':((100,96,92),(120,116,112)),'road':((208,204,196),(224,220,212))}
    for r,c,t in MAP_DATA:
        b,h=P.get(t,P['lowland']); cr=crect(c,r); d.rectangle(cr,fill=b)
        sh=tuple(max(0,v-25) for v in b)
        d.line([cr[0]+1,cr[3]-1,cr[2]-1,cr[3]-1],fill=sh,width=1)
        d.line([cr[2]-1,cr[1]+1,cr[2]-1,cr[3]-2],fill=sh,width=1)
        x,y=px(c,r); d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(140,132,122))
    for ri,rt in enumerate(ROUTES):
        co=(66,135,245) if ri==0 else (234,67,53)
        pts=[px(a,b) for a,b in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=co,width=4)
        for c,r in rt:
            x,y=px(c,r); d.ellipse([x+24-5,y+24-5,x+24+5,y+24+5],fill=co)
    for c,r,n in SPAWNS:
        x,y=px(c,r)
        d.rounded_rectangle([x+6,y+6,x+CELL-6,y+CELL-6],radius=10,fill=(234,67,53),outline=(180,40,30),width=2)
        if n: d.text((x+24-6,y+24-12),str(n),fill=(255,255,255),font=font(20,True))
    for c,r,_ in GOALS:
        x,y=px(c,r)
        d.rounded_rectangle([x+6,y+6,x+CELL-6,y+CELL-6],radius=10,fill=(66,135,245),outline=(40,100,200),width=2)
    d.rectangle([0,0,W,32],fill=(220,215,205))
    d.text((12,6),"PRTS Light (Warm flat + rounded)",fill=(60,55,48),font=font(16))
    im.save(os.path.join(OUT,"sample_prts_light.png"),quality=95); print("[OK] prts_light")

def draw_prts_dark():
    im=Image.new('RGB',(W,H),(22,24,28)); d=ImageDraw.Draw(im)
    P={'lowland':((48,44,40),(62,58,54)),'highland':((68,64,58),(84,78,72)),
       'wall':((42,38,36),(56,52,48)),'deepwater':((28,48,62),(40,64,82)),
       'hole':((18,16,14),(26,24,22)),'road':((56,52,48),(70,66,60))}
    for r,c,t in MAP_DATA:
        b,h=P.get(t,P['lowland']); cr=crect(c,r); d.rectangle(cr,fill=b)
        eg=tuple(min(255,v+12) for v in b)
        d.line([cr[0],cr[1],cr[2]-1,cr[1]],fill=eg,width=1)
        d.line([cr[0],cr[1],cr[0],cr[3]-1],fill=eg,width=1)
        dk=tuple(max(0,v-10) for v in b)
        d.line([cr[0],cr[3]-1,cr[2]-1,cr[3]-1],fill=dk,width=1)
        d.line([cr[2]-1,cr[1],cr[2]-1,cr[3]-1],fill=dk,width=1)
        x,y=px(c,r); d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(100,96,90))
    for ri,rt in enumerate(ROUTES):
        co=(80,160,255) if ri==0 else (255,100,90); gl=tuple(v//3 for v in co)
        pts=[px(a,b) for a,b in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=gl,width=7); d.line([pts[i],pts[i+1]],fill=co,width=3)
        for c,r in rt:
            x,y=px(c,r); d.ellipse([x+24-7,y+24-7,x+24+7,y+24+7],fill=gl); d.ellipse([x+24-4,y+24-4,x+24+4,y+24+4],fill=co)
    for c,r,n in SPAWNS:
        x,y=px(c,r)
        d.rounded_rectangle([x+4,y+4,x+CELL-4,y+CELL-4],radius=12,fill=(80,20,16))
        d.rounded_rectangle([x+6,y+6,x+CELL-6,y+CELL-6],radius=10,fill=(220,60,50),outline=(255,120,110),width=2)
        if n: d.text((x+24-6,y+24-12),str(n),fill=(255,255,255),font=font(20,True))
    for c,r,_ in GOALS:
        x,y=px(c,r)
        d.rounded_rectangle([x+4,y+4,x+CELL-4,y+CELL-4],radius=12,fill=(20,50,100))
        d.rounded_rectangle([x+6,y+6,x+CELL-6,y+CELL-6],radius=10,fill=(60,130,230),outline=(120,180,255),width=2)
    d.rectangle([0,0,W,32],fill=(28,30,36))
    d.text((12,6),"PRTS Dark (Warm dark + glow)",fill=(220,215,210),font=font(16))
    im.save(os.path.join(OUT,"sample_prts_dark.png"),quality=95); print("[OK] prts_dark")

def draw_game():
    im=Image.new('RGB',(W,H),(32,28,24)); d=ImageDraw.Draw(im)
    P={'lowland':((160,152,140),(180,172,160)),'highland':((140,132,120),(164,156,144)),
       'wall':((100,92,84),(124,116,108)),'deepwater':((80,120,148),(112,156,184)),
       'hole':((40,36,32),(60,56,52)),'road':((148,140,130),(168,160,150))}
    for r,c,t in MAP_DATA:
        b,h=P.get(t,P['lowland']); cr=crect(c,r); d.rectangle(cr,fill=b)
        d.line([cr[0]+2,cr[1]+2,cr[2]-3,cr[1]+2],fill=h,width=2)
        d.line([cr[0]+2,cr[1]+2,cr[0]+2,cr[3]-3],fill=h,width=2)
        tx=tuple(min(255,v+8) for v in b)
        d.line([cr[0]+4,cr[3]-4,cr[2]-4,cr[1]+4],fill=tx,width=1)
        x,y=px(c,r); d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(100,92,84))
    for ri,rt in enumerate(ROUTES):
        co=(220,70,60) if ri==0 else (70,140,220)
        pts=[px(a,b) for a,b in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=(40,32,28),width=6); d.line([pts[i],pts[i+1]],fill=co,width=3)
        for c,r in rt:
            x,y=px(c,r); d.ellipse([x+24-6,y+24-6,x+24+6,y+24+6],fill=(40,32,28)); d.ellipse([x+24-4,y+24-4,x+24+4,y+24+4],fill=co)
    for c,r,n in SPAWNS:
        x,y=px(c,r); d.rectangle([x+6,y+6,x+CELL-6,y+CELL-6],fill=(160,40,32),outline=(200,80,70),width=2)
        if n: d.text((x+24-5,y+24-10),str(n),fill=(255,220,200),font=font(18,True))
    for c,r,_ in GOALS:
        x,y=px(c,r); d.rectangle([x+6,y+6,x+CELL-6,y+CELL-6],fill=(40,80,160),outline=(80,140,220),width=2)
    d.rectangle([0,0,W,32],fill=(44,38,32))
    d.text((12,6),"In-Game Style (Warm brown + stroke)",fill=(220,210,200),font=font(16))
    im.save(os.path.join(OUT,"sample_game_style.png"),quality=95); print("[OK] game")

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    draw_current(); draw_prts_light(); draw_prts_dark(); draw_game()
    print("Done!")

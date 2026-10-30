# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT = r"F:\mini api\shots"
CELL, PAD = 56, 24
GRID_W, GRID_H = 10, 8
W = CELL * GRID_W + PAD * 2
H = CELL * GRID_H + PAD * 2

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

def px(c,r): return PAD+(c-1)*CELL, PAD+(GRID_H-r)*CELL
def crect(c,r):
    x,y=px(c,r); return [x,y,x+CELL,y+CELL]

def font(sz,bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc",sz) if bold else ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",sz)
    except:
        try: return ImageFont.truetype("C:/Windows/Fonts/simhei.ttf",sz)
        except: return ImageFont.load_default()

def draw_tile_3d(d, rect, base, highlight, shadow, bevel=4):
    x0,y0,x1,y1=rect
    d.rectangle(rect, fill=base)
    for i in range(bevel):
        alpha=(bevel-i)/bevel
        c=tuple(int(highlight[j]*alpha + base[j]*(1-alpha)) for j in range(3))
        d.line([(x0+i,y0+i),(x1-i,y0+i)],fill=c,width=1)
        d.line([(x0+i,y0+i),(x0+i,y1-i)],fill=c,width=1)
    for i in range(bevel):
        alpha=i/bevel
        c=tuple(int(base[j]*alpha + shadow[j]*(1-alpha)) for j in range(3))
        d.line([(x0+i,y1-i),(x1-i,y1-i)],fill=c,width=1)
        d.line([(x1-i,y0+i),(x1-i,y1-i)],fill=c,width=1)

def draw_tile_isometric(d, rect, base, top_color, left_color, right_color, depth=6):
    x0,y0,x1,y1=rect
    tw,th=x1-x0,y1-y0
    d.rectangle([x0,y0,x1,y1],fill=base)
    for i in range(min(depth, th//3)):
        alpha=(depth-i)/depth
        c=tuple(int(top_color[j]*alpha + base[j]*(1-alpha)) for j in range(3))
        d.line([(x0+i,y0+i),(x1-i,y0+i)],fill=c,width=1)
        d.line([(x0+i,y0+i),(x0+i,y1-i)],fill=c,width=1)
    for i in range(min(depth, th//3)):
        alpha=(i+1)/(depth+1)*0.6
        c=tuple(max(0,int(base[j]*(1-alpha))) for j in range(3))
        d.line([(x0+depth,y1-i),(x1-i,y1-i)],fill=c,width=1)
        d.line([(x1-i,y0+depth),(x1-i,y1-depth)],fill=c,width=1)
    diag_c=tuple(min(255,b+18) for b in base)
    d.line([(x0+3,y1-3),(x0+th//2,y0+th//2)],fill=diag_c,width=1)

def draw_routes(d, routes, style="glow"):
    for ri,rt in enumerate(routes):
        co=(80,160,255) if ri==0 else (255,100,90)
        pts=[px(a,b) for a,b in rt]
        if style=="glow":
            gl=tuple(v//3 for v in co)
            for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=gl,width=7); d.line([pts[i],pts[i+1]],fill=co,width=3)
            for c,r in rt:
                xx,yy=px(c,r); d.ellipse([xx+24-7,yy+24-7,xx+24+7,yy+24+7],fill=gl); d.ellipse([xx+24-4,yy+24-4,xx+24+4,yy+24+4],fill=co)
        elif style=="stroke":
            dk=(30,24,20)
            for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=dk,width=6); d.line([pts[i],pts[i+1]],fill=co,width=3)
            for c,r in rt:
                xx,yy=px(c,r); d.ellipse([xx+24-6,yy+24-6,xx+24+6,yy+24+6],fill=dk); d.ellipse([xx+24-4,yy+24-4,xx+24+4,yy+24+4],fill=co)
        else:
            for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=co,width=3)
            for c,r in rt:
                xx,yy=px(c,r); d.ellipse([xx+24-5,yy+24-5,xx+24+5,yy+24+5],outline=co,width=2)

def draw_spawns(d, spawns, style="rounded"):
    for c,r,n in spawns:
        x,y=px(c,r)
        if style=="rounded":
            d.rounded_rectangle([x+4,y+4,x+CELL-4,y+CELL-4],radius=12,fill=(80,20,16))
            d.rounded_rectangle([x+6,y+6,x+CELL-6,y+CELL-6],radius=10,fill=(220,60,50),outline=(255,120,110),width=2)
        elif style=="square":
            d.rectangle([x+6,y+6,x+CELL-6,y+CELL-6],fill=(180,45,35),outline=(255,100,85),width=2)
        else:
            d.ellipse([x+8,y+8,x+CELL-8,y+CELL-8],outline=(220,60,50),width=3)
        if n: d.text((x+24-6,y+24-12),str(n),fill=(255,255,255),font=font(20,True))

def draw_goals(d, goals, style="rounded"):
    for c,r,_ in goals:
        x,y=px(c,r)
        if style=="rounded":
            d.rounded_rectangle([x+4,y+4,x+CELL-4,y+CELL-4],radius=12,fill=(20,50,100))
            d.rounded_rectangle([x+6,y+6,x+CELL-6,y+CELL-6],radius=10,fill=(60,130,230),outline=(120,180,255),width=2)
        elif style=="square":
            d.rectangle([x+6,y+6,x+CELL-6,y+CELL-6],fill=(40,80,170),outline=(100,160,240),width=2)
        else:
            d.rectangle([x+8,y+8,x+CELL-8,y+CELL-8],outline=(60,130,230),width=3)

def draw_style_a():
    im=Image.new("RGB",(W,H),(20,22,26)); d=ImageDraw.Draw(im)
    P={
        "lowland": ((48,46,42),(78,74,68),(28,26,24)),
        "highland":((64,60,54),(98,92,84),(38,34,32)),
        "wall":    ((36,34,32),(62,58,54),(20,18,16)),
        "deepwater":((28,52,68),(48,82,108),(16,32,44)),
        "hole":    ((14,12,10),(26,24,22),(6,4,4)),
        "road":    ((56,54,48),(86,82,74),(32,30,28)),
    }
    for r,c,t in MAP_DATA:
        b,hi,sh=P.get(t,P["lowland"])
        cr=crect(c,r)
        draw_tile_3d(d,cr,b,hi,sh,bevel=5)
        x,y=px(c,r)
        d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(100,96,88))
    draw_routes(d,ROUTES,"glow")
    draw_spawns(d,SPAWNS,"rounded")
    draw_goals(d,GOALS,"rounded")
    d.rectangle([0,0,W,34],fill=(26,28,32))
    d.text((12,7),"Style A: PRTS Dark + Smooth Bevel 3D",fill=(210,205,198),font=font(16))
    d.text((W-230,11),"Warm dark / gradient bevel / route glow",fill=(110,105,98),font=font(11))
    im.save(os.path.join(OUT,"sample_style_a.png"),quality=95); print("[OK] style_a")

def draw_style_b():
    im=Image.new("RGB",(W,H),(36,32,28)); d=ImageDraw.Draw(im)
    P={
        "lowland": ((152,144,136),(192,184,172),(96,88,80)),
        "highland":((132,124,116),(172,164,152),(80,72,64)),
        "wall":    ((96,88,80),(136,128,118),(56,48,42)),
        "deepwater":((76,116,144),(116,162,196),(48,76,96)),
        "hole":    ((36,32,28),(64,58,52),(16,14,12)),
        "road":    ((140,132,124),(180,172,160),(86,78,70)),
    }
    for r,c,t in MAP_DATA:
        b=P.get(t,P["lowland"])[0]
        top=tuple(min(255,v+28) for v in b)
        lef=tuple(min(255,v+16) for v in b)
        rig=tuple(max(0,v-20) for v in b)
        cr=crect(c,r)
        draw_tile_isometric(d,cr,b,top,lef,rig,depth=7)
        x,y=px(c,r)
        d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(90,84,76))
    draw_routes(d,ROUTES,"stroke")
    draw_spawns(d,SPAWNS,"square")
    draw_goals(d,GOALS,"square")
    d.rectangle([0,0,W,34],fill=(44,40,36))
    d.text((12,7),"Style B: In-Game Warm + Isometric 3D",fill=(212,206,198),font=font(16))
    d.text((W-240,11),"Game warm brown / isometric highlight / stroked routes",fill=(130,122,114),font=font(11))
    im.save(os.path.join(OUT,"sample_style_b.png"),quality=95); print("[OK] style_b")

def draw_style_c():
    im=Image.new("RGB",(W,H),(18,20,24)); d=ImageDraw.Draw(im)
    P={
        "lowland": ((52,48,44),(88,82,74),(26,24,22)),
        "highland":((70,64,58),(112,104,94),(36,32,28)),
        "wall":    ((40,36,34),(72,66,60),(18,16,14)),
        "deepwater":((32,56,72),(56,96,120),(18,36,48)),
        "hole":    ((16,14,12),(30,28,24),(6,4,2)),
        "road":    ((60,56,50),(96,90,82),(30,28,24)),
    }
    for r,c,t in MAP_DATA:
        b,hi,sh=P.get(t,P["lowland"])
        cr=crect(c,r)
        draw_tile_3d(d,cr,b,hi,sh,bevel=8)
        d.rectangle([cr[0]+2,cr[1]+2,cr[2]-2,cr[3]-2],outline=tuple(max(0,v-8) for v in b),width=1)
        x,y=px(c,r)
        d.text((x+4,y+3),f"{chr(64+c)},{r}",fill=(104,100,92))
    draw_routes(d,ROUTES,"glow")
    draw_spawns(d,SPAWNS,"rounded")
    draw_goals(d,GOALS,"rounded")
    d.rectangle([0,0,W,34],fill=(24,26,30))
    d.text((12,7),"Style C: PRTS Dark + Thick Bevel 3D (Strong)",fill=(210,205,198),font=font(16))
    d.text((W-240,11),"Warm dark / thick gradient bevel / strong 3D feel",fill=(110,105,98),font=font(11))
    im.save(os.path.join(OUT,"sample_style_c.png"),quality=95); print("[OK] style_c")

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    draw_style_a(); draw_style_b(); draw_style_c()
    print("Done!")
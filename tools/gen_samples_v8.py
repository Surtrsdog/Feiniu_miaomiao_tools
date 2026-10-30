# -*- coding: utf-8 -*-
"""Style L: Back to practical flat tiles.
   Clean grayscale / grid borders / continuous routes /
   square doors / light gray-white floor / centered coords.
   NO 3D extrusion, NO wireframe, NO gaps."""
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
ENEMIES=[(3,4,3.5),(4,5,2.0),(5,5,4.0),(6,5,1.5),(3,5,2.5)]
MECHANISMS=[(3,5,"box"),(5,3,"trap")]

def px(c,r): return PAD+(c-1)*CELL, PAD+(GRID_H-r)*CELL
def ppx(c,r): return px(c,r)[0]*SS, px(c,r)[1]*SS

def fnt(sz,bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc",sz) if bold else ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",sz)
    except:
        try: return ImageFont.truetype("C:/Windows/Fonts/simhei.ttf",sz)
        except: return ImageFont.load_default()

def fnt_mono(sz):
    for name in ["C:/Windows/Fonts/consola.ttf","C:/Windows/Fonts/arial.ttf"]:
        try: return ImageFont.truetype(name,sz)
        except: pass
    return fnt(sz)

# PALETTE
C_BG=(18,20,24)
C_HIGHLAND =(210,214,222)
C_LOWLAND  =(148,152,160)
C_WALL     =(34,36,42)
C_DEEPWATER=(44,56,76)
C_HOLE     =(14,15,18)
C_ROAD     =(140,144,152)
C_GRID     =(40,44,52)

C_SPAWN=(180,45,38); C_SPAWN_HI=(230,80,70); C_SPAWN_SH=(120,28,22)
C_GOAL=(38,90,180); C_GOAL_HI=(70,130,220); C_GOAL_SH=(26,60,130)
C_ROUTE=(255,55,45); C_ROUTE_GLOW=(255,30,20); C_ROUTE_DOT=(255,80,60)
C_ENEMY_RING=(220,40,30); C_ENEMY_TEXT=(255,255,255)
C_COORD=(90,94,102)

TILE_COLORS={
    "highland": C_HIGHLAND, "lowland": C_LOWLAND,
    "wall": C_WALL, "deepwater": C_DEEPWATER,
    "hole": C_HOLE, "road": C_ROAD,
}


# FLAT TILE WITH GRID BORDER
def make_tile(ttype, sz):
    base = TILE_COLORS.get(ttype, C_LOWLAND)
    img = Image.new("RGB", (sz, sz), base)
    d = ImageDraw.Draw(img)
    arr = np.array(img, dtype=np.float64)
    rng = np.random.RandomState(hash(ttype) % 2**31)
    noise = rng.randint(-3, 4, (sz, sz, 3), dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, sz-1, sz-1], outline=C_GRID, width=1)
    if ttype == "hole":
        d.rectangle([2, 2, sz-2, sz-2], fill=(10,11,14))
    # Subtle bevel on highland only (no 3D, just a hint of raised)
    if ttype == "highland":
        d.line([(1,1),(sz-2,1)], fill=(225,229,235), width=1)
        d.line([(1,1),(1,sz-2)], fill=(225,229,235), width=1)
        d.line([(1,sz-2),(sz-2,sz-2)], fill=(185,189,197), width=1)
        d.line([(sz-2,1),(sz-2,sz-2)], fill=(185,189,197), width=1)
    # Thick border on highland & wall to make them pop
    if ttype in ("highland", "wall"):
        d.rectangle([0, 0, sz-1, sz-1], outline=C_GRID, width=2)
    return img


# STRICT SQUARE DOOR
def make_door_3d(sz, is_red=True, count=None):
    m=8; dsz=sz-m*2; ext=dsz//4
    total_w=dsz+ext+16; total_h=dsz+ext+16
    cvs=Image.new("RGBA",(total_w,total_h),(0,0,0,0))
    fc=C_SPAWN if is_red else C_GOAL; fhi=C_SPAWN_HI if is_red else C_GOAL_HI
    ox,oy,ex,ey=8,8,ext,ext; d=ImageDraw.Draw(cvs)
    back_c=tuple(max(0,v-80)for v in fc); back_e=tuple(max(0,v-100)for v in fc)
    d.rectangle([ox+ex,oy+ey,ox+ex+dsz-1,oy+ey+dsz-1],fill=(*back_c,140),outline=(*back_e,160),width=1)
    side_c=tuple(max(0,v-50)for v in fc)
    d.polygon([(ox+ex,oy+ey),(ox+ex+dsz-1,oy+ey),(ox+dsz-1,oy),(ox,oy)],fill=(*side_c,120))
    d.polygon([(ox+ex,oy+ey),(ox+ex,oy+ey+dsz-1),(ox,oy+dsz-1),(ox,oy)],fill=(*side_c,100))
    d.rectangle([ox,oy,ox+dsz-1,oy+dsz-1],fill=(*fc,230),outline=(*fhi,255),width=2)
    d.rectangle([ox+3,oy+3,ox+dsz-4,oy+dsz-4],outline=(*fhi,100),width=1)
    if count is not None:
        bf=fnt(dsz//3,bold=True); txt=str(count); bb=bf.getbbox(txt)
        tw=bb[2]-bb[0]if bb else dsz//3; th=bb[3]-bb[1]if bb else dsz//4
        tx=ox+(dsz-tw)//2-(bb[0]if bb else 0); ty=oy+(dsz-th)//2-(bb[1]if bb else 0)
        d.text((tx+2,ty+2),txt,fill=(0,0,0,180),font=bf)
        d.text((tx,ty),txt,fill=(255,255,255,255),font=bf)
    return cvs


# CONTINUOUS RED ROUTES
def draw_routes(layer,routes,scale=1):
    d=ImageDraw.Draw(layer)
    for ri,rt in enumerate(routes):
        pts=[(px(c,r)[0]*scale,px(c,r)[1]*scale)for c,r in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=(*C_ROUTE_GLOW,40),width=11*scale)
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=(*C_ROUTE_GLOW,70),width=7*scale)
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=(*C_ROUTE,255),width=2*scale)
        for idx,(cc,rr)in enumerate(rt):
            xx,yy=px(cc,rr)[0]*scale,px(cc,rr)[1]*scale
            is_turn=(idx>0 and idx<len(rt)-1 and(rt[idx][0]-rt[idx-1][0],rt[idx][1]-rt[idx-1][1])!=(rt[idx+1][0]-rt[idx][0],rt[idx+1][1]-rt[idx][1]))
            if is_turn:
                dot_r=5*scale; glow_r=dot_r+4*scale
                d.ellipse([xx-glow_r,yy-glow_r,xx+glow_r,yy+glow_r],fill=(*C_ROUTE_GLOW,60))
                d.ellipse([xx-dot_r-2,yy-dot_r-2,xx+dot_r+2,yy+dot_r+2],fill=C_ROUTE_DOT)
                d.ellipse([xx-dot_r//2,yy-dot_r//2,xx+dot_r//2,yy+dot_r//2],fill=(255,150,140))
            else:
                d.ellipse([xx-2*scale,yy-2*scale,xx+2*scale,yy+2*scale],fill=C_ROUTE)


# ENEMY MARKER
def make_enemy_marker(sz,stop_time):
    r=sz//2; cvs=Image.new("RGBA",(sz,sz),(0,0,0,0)); d=ImageDraw.Draw(cvs); cx,cy=r,r
    gr=r+4; glow=Image.new("RGBA",(gr*2,gr*2),(0,0,0,0)); gd=ImageDraw.Draw(glow)
    gd.ellipse([0,0,gr*2-1,gr*2-1],fill=(*C_ENEMY_RING,35))
    cvs.paste(glow.filter(ImageFilter.GaussianBlur(radius=4)),(cx-gr,cy-gr),glow)
    d.ellipse([3,3,sz-4,sz-4],outline=C_ENEMY_RING,width=3)
    d.ellipse([6,6,sz-7,sz-7],fill=(*C_ENEMY_RING,50))
    txt=str(stop_time)if isinstance(stop_time,int)else f"{stop_time:.1f}"
    bf=fnt(int(sz*0.48),bold=True); bb=bf.getbbox(txt)
    tw=bb[2]-bb[0]if bb else sz//3; th=bb[3]-bb[1]if bb else sz//4
    tx=(sz-tw)//2-(bb[0]if bb else 0); ty=(sz-th)//2-(bb[1]if bb else 0)
    d.text((tx+1,ty+1),txt,fill=(0,0,0,180),font=bf)
    d.text((tx,ty),txt,fill=C_ENEMY_TEXT,font=bf)
    return cvs

# DEVICES
def dev_box(sz):
    m=8;b=sz-m*2;t=b+12;cvs=Image.new("RGBA",(t,t),(0,0,0,0));ox=(t-b)//2;oy=(t-b)//2
    sh=Image.new("L",(b+4,b+4),0);sd=ImageDraw.Draw(sh);sd.rounded_rectangle([2,2,b+2,b+2],radius=5,fill=80)
    cvs.paste((0,0,0,100),(ox+2,oy+2),sh.filter(ImageFilter.GaussianBlur(radius=3)))
    d=ImageDraw.Draw(cvs)
    d.rounded_rectangle([ox,oy,ox+b-1,oy+b-1],radius=5,fill=(160,145,115,230),outline=(200,185,155,255),width=2)
    tc=(120,105,80);cx2,cy2=ox+b//4,oy+3*b//4;cy=oy+b//4;cw,ch=b//4,b//2
    d.rectangle([cx2,cy2-ch//2,cx2+cw,cy2+ch//2],fill=(*tc,200))
    d.rectangle([cy2-ch//2,cy,cy2+ch//2,cy+ch],fill=(*tc,200))
    return cvs

def dev_trap(sz):
    m=8;ts=sz-m*2;t=ts+12;cvs=Image.new("RGBA",(t,t),(0,0,0,0));ox=(t-ts)//2;oy=(t-ts)//2
    d=ImageDraw.Draw(cvs);cx,cy=ox+ts//2,oy+ts//2;tr=ts//3
    gl=Image.new("RGBA",(ts+8,ts+8),(0,0,0,0));gd=ImageDraw.Draw(gl)
    gd.ellipse([2,2,ts+5,ts+5],fill=(*C_ENEMY_RING,40))
    cvs.paste(gl.filter(ImageFilter.GaussianBlur(radius=4)),(ox-4,oy-4),gl)
    d.ellipse([ox+3,oy+3,ox+ts-4,oy+ts-4],fill=(60,58,56,230),outline=(100,96,92,255),width=2)
    d.ellipse([ox+8,oy+8,ox+ts-9,oy+ts-9],outline=(140,136,130,180),width=1)
    for ang in range(0,360,45):
        rad=math.radians(ang-90)
        for r2 in range(ts//2-6,ts//3,-1):
            spx=cx+int(r2*math.cos(rad));spy=cy+int(r2*math.sin(rad))
            if ox<=spx<ox+ts and oy<=spy<oy+ts: d.point((spx,spy),fill=(180,176,170))
    d.ellipse([cx-4,cy-4,cx+4,cy+4],fill=C_ENEMY_RING)
    d.ellipse([cx-2,cy-2,cx+2,cy+2],fill=(255,120,110))
    return cvs

DEVS={"box":dev_box,"trap":dev_trap}

def paste_on(img_rgba,overlay,col,row):
    xx,yy=ppx(col,row); dw,dh=overlay.size
    dx=xx-(dw-CELL*SS)//2; dy=yy-(dh-CELL*SS)//2
    tmp=Image.new("RGBA",img_rgba.size,(0,0,0,0))
    tmp.paste(overlay,(dx,dy),overlay)
    return Image.alpha_composite(img_rgba,tmp)


def render(style_name,bg,title,sub,tf,sf,bar):
    WW,HH=W*SS,H*SS; base=Image.new("RGB",(WW,HH),bg)
    for r,c,t in MAP_DATA:
        tile=make_tile(t,CELL*SS); x,y=ppx(c,r); base.paste(tile,(x,y))
        d=ImageDraw.Draw(base); lbl=f"{chr(64+c)},{r}"; bf=fnt_mono(13*SS)
        bb=bf.getbbox(lbl); tw=bb[2]-bb[0]if bb else CELL*SS//4; th=bb[3]-bb[1]if bb else CELL*SS//6
        tx=x+(CELL*SS-tw)//2-(bb[0]if bb else 0); ty=y+(CELL*SS-th)//2-(bb[1]if bb else 0)
        d.text((tx,ty),lbl,fill=C_COORD,font=bf)
    ovl=Image.new("RGBA",(WW,HH),(0,0,0,0))
    draw_routes(ovl,ROUTES,scale=SS)
    for c,r,n in SPAWNS: ovl=paste_on(ovl,make_door_3d(CELL*SS,is_red=True,count=n),c,r)
    for c,r,_ in GOALS: ovl=paste_on(ovl,make_door_3d(CELL*SS,is_red=False,count=None),c,r)
    for c,r,mt in MECHANISMS:
        fn=DEVS.get(mt)
        if fn: ovl=paste_on(ovl,fn(CELL*SS),c,r)
    for c,r,st in ENEMIES: ovl=paste_on(ovl,make_enemy_marker(int(CELL*SS*0.65),st),c,r)
    cvs=base.convert("RGBA"); cvs=Image.alpha_composite(cvs,ovl); cvs=cvs.convert("RGB")
    d=ImageDraw.Draw(cvs)
    d.rectangle([0,0,WW,34*SS],fill=bar)
    d.text((12*SS,8*SS),title,fill=tf,font=fnt(15*SS))
    d.text((W*SS-240*SS,10*SS),sub,fill=sf,font=fnt(10*SS))
    out=cvs.resize((W,H),Image.LANCZOS)
    fname=os.path.join(OUT,f"sample_{style_name.lower()}.png")
    out.save(fname,quality=95)
    print(f"[OK] {style_name} -> {fname} ({os.path.getsize(fname)} bytes)")


if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    render("L",C_BG,
        "Style L: Clean Flat / Practical",
        "flat tiles + grid border + continuous routes + square doors + centered coords",
        (200,204,212),(100,104,112),(24,26,32))
    print("Done!")

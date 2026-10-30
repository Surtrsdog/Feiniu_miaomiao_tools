# -*- coding: utf-8 -*-
"""Map v3: Flat tiles + 3D doors + 3D mechanisms"""
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

# Mechanisms to place: (col, row, type)
# types: box, trap, heal, damage, portal, support, turret
MECHANISMS = [
    (3, 5, "box"),       # 箱子障碍
    (5, 3, "trap"),      # 陷阱
    (7, 4, "heal"),      # 治疗装置
    (4, 7, "damage"),    # 伤害装置
    (2, 6, "portal"),    # 传送门
    (6, 2, "support"),   # 支援装置
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


# ════════════════════════════════════════════
# FLAT tile drawing (no 3D)
# ════════════════════════════════════════════
def draw_tile_flat(d, rect, base_color, edge_light=8, edge_dark=12):
    """Flat tile with subtle 1px edge - PRTS style"""
    d.rectangle(rect, fill=base_color)
    x0,y0,x1,y1 = rect
    # Top/left 1px light edge
    light = tuple(min(255, v+edge_light) for v in base_color)
    d.line([(x0,y0),(x1-1,y0)], fill=light, width=1)
    d.line([(x0,y0),(x0,y1-1)], fill=light, width=1)
    # Bottom/right 1px dark edge
    dark = tuple(max(0, v-edge_dark) for v in base_color)
    d.line([(x0,y1-1),(x1-1,y1-1)], fill=dark, width=1)
    d.line([(x1-1,y0),(x1-1,y1-1)], fill=dark, width=1)


# ════════════════════════════════════════════
# 3D DOOR (spawn / goal) - the main 3D element
# ════════════════════════════════════════════
def draw_3d_door(d, x, y, size, is_red=True, count=None):
    """
    Draw a 3D beveled door/marker.
    is_red=True -> spawn door (red)
    is_red=False -> goal door (blue)
    """
    margin = 6
    bevel = 5
    door_x = x + margin
    door_y = y + margin
    door_sz = size - margin*2
    
    if is_red:
        base = (180, 50, 40)
        highlight = (240, 100, 85)
        shadow = (120, 28, 22)
        glow_base = (120, 20, 14)
        text_color = (255, 255, 255)
    else:
        base = (45, 95, 185)
        highlight = (90, 155, 245)
        shadow = (26, 58, 120)
        glow_base = (18, 42, 90)
        text_color = (255, 255, 255)
    
    # Outer glow
    glow_rect = [door_x-3, door_y-3, door_x+door_sz+3, door_y+door_sz+3]
    d.rounded_rectangle(glow_rect, radius=bevel+3, fill=glow_base)
    
    # Main face
    main_rect = [door_x, door_y, door_x+door_sz, door_y+door_sz]
    d.rounded_rectangle(main_rect, radius=bevel, fill=base)
    
    # Top bevel (gradient highlight)
    for i in range(bevel):
        alpha = (bevel-i)/bevel
        c = tuple(int(highlight[j]*alpha + base[j]*(1-alpha)) for j in range(3))
        yi = door_y + i
        # Rounded top corners: only draw within rounded area
        d.line([(door_x+bevel, yi), (door_x+door_sz-bevel, yi)], fill=c, width=1)
    
    # Left bevel
    for i in range(bevel):
        alpha = (bevel-i)/bevel
        c = tuple(int(highlight[j]*alpha + base[j]*(1-alpha)) for j in range(3))
        xi = door_x + i
        d.line([(xi, door_y+bevel), (xi, door_y+door_sz-bevel)], fill=c, width=1)
    
    # Bottom bevel (shadow)
    for i in range(bevel):
        alpha = i/bevel
        c = tuple(int(base[j]*alpha + shadow[j]*(1-alpha)) for j in range(3))
        yi = door_y + door_sz - 1 - i
        d.line([(door_x+bevel, yi), (door_x+door_sz-bevel, yi)], fill=c, width=1)
    
    # Right bevel (shadow)
    for i in range(bevel):
        alpha = i/bevel
        c = tuple(int(base[j]*alpha + shadow[j]*(1-alpha)) for j in range(3))
        xi = door_x + door_sz - 1 - i
        d.line([(xi, door_y+bevel), (xi, door_y+door_sz-bevel)], fill=c, width=1)
    
    # Inner highlight line (top-left inner edge)
    inner_light = tuple(min(255, v+30) for v in base)
    d.line([(door_x+bevel+1, door_y+bevel+1), (door_x+door_sz-bevel-2, door_y+bevel+1)], 
           fill=inner_light, width=1)
    d.line([(door_x+bevel+1, door_y+bevel+1), (door_x+bevel+1, door_y+door_sz-bevel-2)], 
           fill=inner_light, width=1)
    
    # Count number
    if count is not None:
        txt = str(count)
        bf = font(18, bold=True)
        # Text shadow
        d.text((door_x+door_sz//2-5+1, door_y+door_sz//2-9+1), txt, fill=(0,0,0), font=bf)
        d.text((door_x+door_sz//2-5, door_y+door_sz//2-9), txt, fill=text_color, font=bf)


# ════════════════════════════════════════════
# 3D MECHANISM / DEVICE icons
# ════════════════════════════════════════════
def draw_3d_box(d, cx, cy, sz):
    """Box/obstacle - brown 3D crate"""
    b = 6; box_sz = sz - b*2; x=cx+b; y=cy+b
    base=(160,120,80); hi=(210,170,120); sh=(110,75,48)
    # Shadow under box
    d.rounded_rectangle([x+3,y+3,x+box_sz+3,y+box_sz+3],radius=4,fill=(30,24,18))
    # Face
    d.rounded_rectangle([x,y,x+box_sz,y+box_sz],radius=4,fill=base)
    # Bevel top
    for i in range(4):
        a=(4-i)/4; c=tuple(int(hi[j]*a+base[j]*(1-a)) for j in range(3))
        d.line([(x+4,y+i),(x+box_sz-4,y+i)],fill=c,width=1)
    # Bevel left
    for i in range(4):
        a=(4-i)/4; c=tuple(int(hi[j]*a+base[j]*(1-a)) for j in range(3))
        d.line([(x+i,y+4),(x+i,y+box_sz-4)],fill=c,width=1)
    # Bevel bottom
    for i in range(4):
        a=i/4; c=tuple(int(base[j]*a+sh[j]*(1-a)) for j in range(3))
        d.line([(x+4,y+box_sz-1-i),(x+box_sz-4,y+box_sz-1-i)],fill=c,width=1)
    # Cross tape lines on box
    tc=tuple(max(0,v-20) for v in base)
    d.line([(x+box_sz//3,y+4),(x+box_sz//3,y+box_sz-4)],fill=tc,width=1)
    d.line([(x+2*box_sz//3,y+4),(x+2*box_sz//3,y+box_sz-4)],fill=tc,width=1)
    d.line([(x+4,y+box_sz//3),(x+box_sz-4,y+box_sz//3)],fill=tc,width=1)

def draw_3d_trap(d, cx, cy, sz):
    """Trap - spiked plate"""
    b=8; ts=sz-b*2; x=cx+b; y=cy+b
    base=(140,140,140); hi=(190,190,190); sh=(90,90,90)
    d.ellipse([x+2,y+2,x+ts+2,y+ts+2],fill=(30,28,26))
    d.ellipse([x,y,x+ts,y+ts],fill=base)
    # Ring highlight
    d.ellipse([x+3,y+3,x+ts-3,y+ts-3],outline=hi,width=2)
    # Spikes (triangle points inward)
    mid_x=x+ts//2; mid_y=y+ts//2; r=ts//2-5
    import math
    for angle in range(0,360,45):
        rad=math.radians(angle-90)  # -90 so first spike points up
        px1=mid_x+int(r*math.cos(rad))
        py1=mid_y+int(r*math.sin(rad))
        px2=mid_x+int((r-8)*math.cos(rad))
        py2=mid_y+int((r-8)*math.sin(rad))
        d.line([(px1,py1),(px2,py2)],fill=hi,width=2)
    # Center warning dot
    d.ellipse([mid_x-4,mid_y-4,mid_x+4,mid_y+4],fill=(220,60,50))

def draw_3d_heal(d, cx, cy, sz):
    """Healing device - green cross 3D"""
    b=6; hs=sz-b*2; x=cx+b; y=cy+b
    base=(50,150,80); hi=(90,200,120); sh=(30,100,52)
    d.rounded_rectangle([x+2,y+2,x+hs+2,y+hs+2],radius=hs//3,fill=(20,50,28))
    d.rounded_rectangle([x,y,x+hs,y+hs],radius=hs//3,fill=base)
    # Bevel
    for i in range(3):
        a=(3-i)/3; c=tuple(int(hi[j]*a+base[j]*(1-a)) for j in range(3))
        d.line([(x+hs//3,y+i),(x+hs-hs//3,y+i)],fill=c,width=1)
    # White cross
    cw=hs//4; ch=hs//2; mx=x+hs//2; my=y+hs//2
    d.rectangle([mx-cw//2,my-ch//2,mx+cw//2,my+ch//2],fill=(255,255,255))
    d.rectangle([mx-ch//2,my-cw//2,mx+ch//2,my+cw//2],fill=(255,255,255))

def draw_3d_damage(d, cx, cy, sz):
    """Damage zone - red/orange hazard"""
    b=6; ds=sz-b*2; x=cx+b; y=cy+b
    base=(170,50,40); hi=(230,90,70); sh=(110,28,22)
    d.rounded_rectangle([x+2,y+2,x+ds+2,y+ds+2],radius=ds//3,fill=(60,15,10))
    d.rounded_rectangle([x,y,x+ds,y+ds],radius=ds//3,fill=base)
    # Bevel
    for i in range(3):
        a=(3-i)/3; c=tuple(int(hi[j]*a+base[j]*(1-a)) for j in range(3))
        d.line([(x+ds//3,y+i),(x+ds-ds//3,y+i)],fill=c,width=1)
    # Warning triangle / lightning icon
    mx=x+ds//2; my=y+ds//2; tr=ds//3
    # Triangle
    d.polygon([(mx,my-tr),(mx-tr,my+tr//1.5),(mx+tr,my+tr//1.5)],fill=(255,220,100))
    d.polygon([(mx,my-tr+4),(mx-tr+4,my+tr//1.5-2),(mx+tr-4,my+tr//1.5-2)],fill=(180,50,35))

def draw_3d_portal(d, cx, cy, sz):
    """Portal - purple swirling gate"""
    b=5; ps=sz-b*2; x=cx+b; y=cy+b
    outer=(60,30,110); inner=(130,80,200); glow=(90,50,160)
    # Outer ring shadow
    d.ellipse([x+2,y+2,x+ps+2,y+ps+2],fill=(20,12,32))
    # Glow
    d.ellipse([x-3,y-3,x+ps+3,y+ps+3],fill=(40,18,70))
    # Outer ring
    d.ellipse([x,y,x+ps,y+ps],fill=outer)
    # Inner gradient rings
    for i in range(3,0,-1):
        r=i*3
        a=i/4
        c=tuple(int(inner[j]*a+outer[j]*(1-a)) for j in range(3))
        d.ellipse([x+r,y+r,x+ps-r,y+ps-r],outline=c,width=2)
    # Core bright center
    cr=ps//3
    d.ellipse([x+ps//2-cr,y+ps//2-cr,x+ps//2+cr,y+ps//2+cr],fill=(180,140,255))
    # Swirl hints
    d.arc([x+4,y+4,x+ps-4,y+ps-4],start=30,end=150,fill=(170,120,240),width=2)
    d.arc([x+6,y+6,x+ps-6,y+ps-6],start=210,end=330,fill=(170,120,240),width=2)

def draw_3d_support(d, cx, cy, sz):
    """Support device - blue flag/flagpole"""
    b=6; ss=sz-b*2; x=cx+b; y=cy+b
    # Pole shadow
    d.rectangle([x+ss//2+1,y+4,x+ss//2+3,y+ss-4],fill=(20,30,45))
    # Pole
    pole_c=(180,190,200); pole_hi=(220,228,235); pole_sh=(120,130,145)
    d.rectangle([x+ss//2-1,y+4,x+ss//2+2,y+ss-2],fill=pole_c)
    d.line([(x+ss//2-1,y+4),(x+ss//2+2,y+4)],fill=pole_hi,width=1)
    # Flag (triangle)
    flag_pts=[(x+ss//2+2,y+6),(x+ss-3,y+ss//3),(x+ss//2+2,y+ss//3+4)]
    d.polygon(flag_pts,fill=(60,130,220))
    # Flag highlight
    fhi_pts=[(x+ss//2+2,y+7),(x+ss-5,y+ss//3-2),(x+ss//2+2,y+ss//3+2)]
    d.polygon(fhi_pts,fill=(100,170,245))
    # Base
    d.rectangle([x+ss//4,y+ss-5,x+3*ss//4,y+ss-2],fill=(100,105,115))
    d.line([(x+ss//4,y+ss-5),(x+3*ss//4,y+ss-5)],fill=(150,155,165),width=1)


def draw_mechanism(d, col, row, mech_type):
    """Dispatch to correct 3D mechanism drawer"""
    x, y = px(col, row)
    dispatch = {
        "box": draw_3d_box,
        "trap": draw_3d_trap,
        "heal": draw_3d_heal,
        "damage": draw_3d_damage,
        "portal": draw_3d_portal,
        "support": draw_3d_support,
    }
    fn = dispatch.get(mech_type)
    if fn:
        fn(d, x, y, CELL)


def draw_routes(d, routes):
    for ri, rt in enumerate(routes):
        co=(80,160,255) if ri==0 else (255,100,90)
        gl=tuple(v//3 for v in co)
        pts=[px(a,b) for a,b in rt]
        for i in range(len(pts)-1): 
            d.line([pts[i],pts[i+1]],fill=gl,width=7)
            d.line([pts[i],pts[i+1]],fill=co,width=3)
        for c,r in rt:
            xx,yy=px(c,r)
            d.ellipse([xx+24-7,yy+24-7,xx+24+7,yy+24+7],fill=gl)
            d.ellipse([xx+24-4,yy+24-4,xx+24+4,yy+24+4],fill=co)


# ════════════════════════════════════════════
# STYLE D: Flat Tiles + 3D Doors + 3D Mechanisms (Dark)
# ════════════════════════════════════════════
def draw_style_d():
    im=Image.new("RGB",(W,H),(20,22,26)); d=ImageDraw.Draw(im)
    # Warm dark flat palette
    P={
        "lowland": (48,44,40),
        "highland":(64,60,54),
        "wall":   (36,34,32),
        "deepwater":(28,52,68),
        "hole":   (14,12,10),
        "road":   (56,54,48),
    }
    for r,c,t in MAP_DATA:
        base=P.get(t,P["lowland"])
        cr=crect(c,r)
        draw_tile_flat(d,cr,base)
        x,y=px(c,r)
        d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(100,96,88))
    
    # Routes
    draw_routes(d,ROUTES)
    
    # 3D Doors
    for c,r,n in SPAWNS:
        x,y=px(c,r)
        draw_3d_door(d,x,y,CELL,is_red=True,count=n)
    for c,r,_ in GOALS:
        x,y=px(c,r)
        draw_3d_door(d,x,y,CELL,is_red=False,count=None)
    
    # 3D Mechanisms
    for c,r,m in MECHANISMS:
        draw_mechanism(d,c,r,m)
    
    # Title
    d.rectangle([0,0,W,36],fill=(26,28,32))
    d.text((12,8),"Style D: Flat Tiles + 3D Doors + 3D Devices (Dark)",fill=(210,205,198),font=font(16))
    d.text((W-250,12),"Flat warm tiles / 3D beveled doors & mechanisms",fill=(110,105,98),font=font(11))
    im.save(os.path.join(OUT,"sample_style_d.png"),quality=95); print("[OK] style_d")


# ════════════════════════════════════════════
# STYLE E: Same but In-Game Warm tone
# ════════════════════════════════════════════
def draw_style_e():
    im=Image.new("RGB",(W,H),(40,36,32)); d=ImageDraw.Draw(im)
    P={
        "lowland": (152,144,136),
        "highland":(132,124,116),
        "wall":   (96,88,80),
        "deepwater":(76,116,144),
        "hole":   (36,32,28),
        "road":   (140,132,124),
    }
    for r,c,t in MAP_DATA:
        base=P.get(t,P["lowland"])
        cr=crect(c,r)
        draw_tile_flat(d,cr,base,edge_light=12,edge_dark=16)
        x,y=px(c,r)
        d.text((x+3,y+2),f"{chr(64+c)},{r}",fill=(80,74,68))
    
    # Routes - stroked style for lighter bg
    for ri,rt in enumerate(ROUTES):
        co=(220,70,60) if ri==0 else (70,140,220)
        dk=(40,32,28)
        pts=[px(a,b) for a,b in rt]
        for i in range(len(pts)-1): d.line([pts[i],pts[i+1]],fill=dk,width=6); d.line([pts[i],pts[i+1]],fill=co,width=3)
        for c,r in rt:
            xx,yy=px(c,r); d.ellipse([xx+24-6,yy+24-6,xx+24+6,yy+24+6],fill=dk); d.ellipse([xx+24-4,yy+24-4,xx+24+4,yy+24+4],fill=co)
    
    for c,r,n in SPAWNS:
        x,y=px(c,r); draw_3d_door(d,x,y,CELL,is_red=True,count=n)
    for c,r,_ in GOALS:
        x,y=px(c,r); draw_3d_door(d,x,y,CELL,is_red=False,count=None)
    for c,r,m in MECHANISMS:
        draw_mechanism(d,c,r,m)
    
    d.rectangle([0,0,W,36],fill=(52,46,40))
    d.text((12,8),"Style E: Flat Tiles + 3D Doors + 3D Devices (Warm)",fill=(212,206,198),font=font(16))
    d.text((W-250,12),"Game-warm flat tiles / 3D beveled doors & mechanisms",fill=(130,122,114),font=font(11))
    im.save(os.path.join(OUT,"sample_style_e.png"),quality=95); print("[OK] style_e")


if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    draw_style_d(); draw_style_e()
    print("Done!")

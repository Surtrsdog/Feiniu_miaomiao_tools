# -*- coding: utf-8 -*-
"""High-quality map renderer v4: textured flat tiles + real 3D devices with blur glow"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os, math, random

OUT = r"F:\mini api\shots"
CELL, PAD = 56, 24
GRID_W, GRID_H = 10, 8
W = CELL * GRID_W + PAD * 2
H = CELL * GRID_H + PAD * 2
SS = 2  # supersample 2x for anti-aliasing

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
MECHANISMS=[
    (3,5,"box"),(5,3,"trap"),(7,4,"heal"),
    (4,7,"damage"),(2,6,"portal"),(6,2,"support"),
]

def px(c,r): return PAD+(c-1)*CELL, PAD+(GRID_H-r)*CELL
def crect(c,r):
    x,y=px(c,r); return [x,y,x+CELL,y+CELL]
def ppx(c,r): return px(c,r)[0]*SS, px(c,r)[1]*SS
def pcrect(c,r):
    x,y=ppx(c,r); return [x,y,x+CELL*SS,y+CELL*SS]

def font(sz,bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc",sz) if bold else ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",sz)
    except:
        try: return ImageFont.truetype("C:/Windows/Fonts/simhei.ttf",sz)
        except: return ImageFont.load_default()


# ════════════════════════════════════════════
# TEXTURE & NOISE HELPERS  
# ════════════════════════════════════════════
def make_noise_tile(base_color, size, noise_strength=12, seed=None):
    """Generate a tile with subtle noise texture"""
    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), base_color)
    pixels = img.load()
    for py in range(size):
        for px in range(size):
            n = rng.randint(-noise_strength, noise_strength)
            c = pixels[px,py]
            pixels[px,py] = tuple(max(0,min(255,v+n)) for v in c)
    return img

def make_gradient_rect(w, h, color_tl, color_br):
    """Create a rectangle with smooth diagonal gradient"""
    img = Image.new("RGB", (w, h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            fx = x/(w-1) if w>1 else 0
            fy = y/(h-1) if h>1 else 0
            r = int(color_tl[0]*(1-fy)+color_br[0]*fy)
            g = int(color_tl[1]*(1-fy)+color_br[1]*fy)
            b = int(color_tl[2]*(1-fy)+color_br[2]*fy)
            # blend x too
            r2 = int(r*(1-fx) + int(color_br[0]*0.3+color_tl[0]*0.7)*fx)
            g2 = int(g*(1-fx) + int(color_br[1]*0.3+color_tl[1]*0.7)*fx)
            b2 = int(b*(1-fx) + int(color_br[2]*0.3+color_tl[2]*0.7)*fx)
            pixels[x,y] = (r2,g2,b2)
    return img

def make_radial_glow(size, center_color, edge_color, radius_factor=1.0):
    """Create a radial gradient circle for glow effects"""
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    pixels = img.load()
    cx, cy = size//2, size//2
    max_r = (size//2) * radius_factor
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x-cx)**2 + (y-cy)**2)
            if dist < max_r:
                t = dist / max_r
                t = t * t  # ease-out for softer edge
                r = int(center_color[0]*(1-t) + edge_color[0]*t)
                g = int(center_color[1]*(1-t) + edge_color[1]*t)
                b = int(center_color[2]*(1-t) + edge_color[2]*t)
                a = int(255*(1-t*t))
                pixels[x,y] = (r,g,b,a)
    return img


# ════════════════════════════════════════════
# FLAT TEXTURED TILE
# ════════════════════════════════════════════
PALETTE_FLAT = {
    "lowland":   ((52,48,44), (62,58,52), (42,38,34)),   # base, light_var, dark_var
    "highland":  ((68,64,56), (80,76,68), (56,52,46)),
    "wall":      ((40,38,34), (50,48,42), (32,30,26)),
    "deepwater":((28,54,72), (40,70,92), (20,40,54)),
    "hole":      ((16,14,12), (24,22,18), (10,8,6)),
    "road":      ((60,56,50), (72,68,60), (48,44,40)),
}

def draw_textured_tile(target, rect, tile_type, seed_base=0):
    """Draw a flat tile with noise texture and subtle gradient"""
    x0,y0,x1,y1 = rect
    tw,th = x1-x0, y1-y0
    base,light,dark = PALETTE_FLAT.get(tile_type, PALETTE_FLAT["lowland"])
    
    # Gradient base (subtle top-left to bottom-right)
    grad = make_gradient_rect(tw, th, light, dark)
    
    # Add noise
    rng = random.Random(seed_base)
    pixels = grad.load()
    for py in range(th):
        for px in range(tw):
            n = rng.randint(-8, 8)
            c = pixels[px,py]
            pixels[px,py] = tuple(max(0,min(255,v+n)) for v in c)
    
    target.paste(grad, (x0,y0,x1,y1))
    
    # Crisp 1px border (inset)
    d = ImageDraw.Draw(target)
    border_light = tuple(min(255,v+10) for v in base)
    border_dark = tuple(max(0,v-14) for v in base)
    d.line([(x0,y0),(x1-1,y0)], fill=border_light, width=1)
    d.line([(x0,y0),(x0,y1-1)], fill=border_light, width=1)
    d.line([(x0,y1-1),(x1-1,y1-1)], fill=border_dark, width=1)
    d.line([(x1-1,y0),(x1-1,y1-1)], fill=border_dark, width=1)


# ════════════════════════════════════════════
# REAL 3D DOOR with gradient + blur glow
# ════════════════════════════════════════════
def draw_real_3d_door(target, sx, sy, sz, is_red=True, count=None):
    """Render a proper 3D door with gradient faces and blurred glow"""
    m = 6  # margin
    bevel = min(8, (sz-m*2)//4)
    dsz = sz - m*2  # door size
    dx, dy = sx+m, sy+m
    
    if is_red:
        base=(200,55,45); hi_t=(255,140,120); hi_l=(255,160,140)
        sh_b=(140,32,24); sh_r=(130,28,22)
        glow_c=(220,80,60); glow_dark=(140,30,18)
    else:
        base=(50,110,210); hi_t=(130,180,255); hi_l=(150,200,255)
        sh_b=(28,68,140); sh_r=(24,58,120)
        glow_c=(80,150,255); glow_dark=(30,65,140)
    
    # === 1. Outer glow (render larger, then gaussian blur) ===
    glow_sz = dsz + 16
    glow_img = Image.new("RGBA", (glow_sz, glow_sz), (0,0,0,0))
    gd = ImageDraw.Draw(glow_img)
    gc = glow_sz // 2
    gd.ellipse([4,4,glow_sz-4,glow_sz-4],fill=(*glow_dark,200))
    gd.ellipse([10,10,glow_sz-10,glow_sz-10],fill=(*glow_c,180))
    # Blur it!
    glow_blurred = glow_img.filter(ImageFilter.GaussianBlur(radius=6))
    target.paste(glow_blurred, (dx-8, dy-8), glow_blurred)
    
    # === 2. Door face with real gradient (pixel-level) ===
    face = Image.new("RGB", (dsz, dsz), base)
    fp = face.load()
    
    # Top bevel zone: gradient from hi_t -> base
    for by in range(bevel):
        fy = by/bevel
        c_top = tuple(int(hi_t[i]*fy + base[i]*(1-fy)) for i in range(3))
        for bx in range(dsz):
            # Round corners: fade out alpha near corners
            corner_fade = 1.0
            if bx < bevel:
                dist = math.sqrt((bx-bevel)**2 + (by-bevel)**2)
                if dist > bevel: corner_fade = max(0, 1-(dist-bevel)/bevel)
            elif bx >= dsz-bevel:
                dist = math.sqrt((bx-(dsz-bevel-1))**2 + (by-bevel)**2)
                if dist > bevel: corner_fade = max(0, 1-(dist-bevel)/bevel)
            if corner_fade > 0:
                blended = tuple(int(c_top[i]*corner_fade + (fp[bx,by][i] if isinstance(fp[bx,by],tuple) else base[i])*(1-corner_fade)) for i in range(3))
                fp[bx,by] = blended
    
    # Left bevel zone
    for bx in range(bevel):
        fx = bx/bevel
        c_left = tuple(int(hi_l[i]*fx + base[i]*(1-fx)) for i in range(3))
        for by in range(bevel, dsz-bevel):
            fp[bx,by] = c_left
    
    # Bottom bevel zone
    for by in range(dsz-bevel, dsz):
        fy = (by-(dsz-bevel))/bevel
        c_bot = tuple(int(base[i]*fy + sh_b[i]*(1-fy)) for i in range(3))
        for bx in range(dsz):
            fp[bx,by] = c_bot
    
    # Right bevel zone
    for bx in range(dsz-bevel, dsz):
        fx = (bx-(dsz-bevel))/bevel
        c_right = tuple(int(base[i]*fx + sh_r[i]*(1-fx)) for i in range(3))
        for by in range(bevel, dsz-bevel):
            fp[bx,by] = c_right
    
    # Inner highlight (thin bright line at top-left inner edge)
    inner_hi = tuple(min(255,v+40) for v in base)
    for i in range(bevel+1, bevel+3):
        if i < dsz-1:
            for bx in range(bevel+1, dsz-bevel-1):
                fp[bx,i] = inner_hi
            for bi in range(bevel+1, dsz-bevel-1):
                fp[i,bi] = inner_hi
    
    # Paste face (with rounded corners via mask)
    mask = Image.new("L", (dsz, dsz), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0,0,dsz-1,dsz-1],radius=bevel,fill=255)
    target.paste(face, (dx,dy), mask)
    
    # === 3. Count text with text shadow ===
    if count is not None:
        txt=str(count)
        bf=font(20,True)
        txt_img = Image.new("RGBA",(dsz,dsz),(0,0,0,0))
        td = ImageDraw.Draw(txt_img)
        cx = dsz//2 - 8
        cy = dsz//2 - 14
        td.text((cx+2,cy+2),txt,fill=(0,0,0,180),font=bf)
        td.text((cx,cy),txt,fill=(255,255,255,255),font=bf)
        target.paste(txt_img,(dx,dy),txt_img)


# ════════════════════════════════════════════
# 3D DEVICES with real gradients + shadows + blur
# ════════════════════════════════════════════
def draw_device_box(target, sx, sy, sz):
    """Wooden box crate with texture, bevel, cross tape, drop shadow"""
    m=7; bsz=sz-m*2; x=sx+m; y=sy+m
    # Drop shadow
    sh = Image.new("RGBA",(bsz,bsz),(0,0,0,0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([3,3,bsz+2,bsz+2],radius=5,fill=(0,0,0,100))
    shb = sh.filter(ImageFilter.GaussianBlur(radius=3))
    target.paste(shb,(x,y),shb)
    
    # Face gradient
    face = Image.new("RGB",(bsz,bsz),(160,120,75))
    fp=face.load()
    base=(165,125,78); hi=(215,172,120); sh=(115,80,48)
    bv=5
    for by in range(bv):
        f=by/bv; c=tuple(int(hi[i]*f+base[i]*(1-f))for i in range(3))
        for bx in range(bsz): fp[bx,by]=c
    for bx in range(bv):
        f=bx/bv; c=tuple(int(hi[i]*f+base[i]*(1-f))for i in range(3))
        for by in range(bv,bsz-bv): fp[bx,by]=c
    for by in range(bsz-bv,bsz):
        f=(by-bsz+bv)/bv; c=tuple(int(base[i]*f+sh[i]*(1-f))for i in range(3))
        for bx in range(bsz): fp[bx,by]=c
    for bx in range(bsz-bv,bsz):
        f=(bx-bsz+bv)/bv; c=tuple(int(base[i]*f+sh[i]*(1-f))for i in range(3))
        for by in range(bv,bsz-bv): fp[bx,by]=c
    # Noise texture
    rng=random.Random(42)
    for py in range(bsz):
        for px in range(bsz):
            n=rng.randint(-12,12)
            c=fp[px,py]; fp[px,py]=tuple(max(0,min(255,v+n))for v in c)
    # Tape cross (darker)
    tc=tuple(max(0,v-25)for v in base)
    for i in range(bsz):
        if bsz//3<i<2*bsz//3:
            fp[bsz//3,i]=tc; fp[2*bsz//3,i]=tc
        if bsz//3<i<2*bsz//3:
            fp[i,bsz//3]=tc; fp[i,2*bsz//3]=tc
    # Mask rounded
    mk=Image.new("L",(bsz,bsz),0); md=ImageDraw.Draw(mk)
    md.rounded_rectangle([0,0,bsz-1,bsz-1],radius=5,fill=255)
    target.paste(face,(x,y),mk)

def draw_device_trap(target,sx,sy,sz):
    """Spiked trap plate - metallic with radial gradient + spikes"""
    m=8; ts=sz-m*2; x=sx+m; y=sy+m
    # Shadow
    sh=Image.new("RGBA",(ts,ts),(0,0,0,0))
    sd=ImageDraw.Draw(sh)
    sd.ellipse([2,2,ts+3,ts+3],fill=(0,0,0,90))
    target.paste(sh.filter(ImageFilter.GaussianBlur(radius=3)),(x,y),sh)
    # Face - radial metallic gradient
    face=Image.new("RGB",(ts,ts),(140,140,145))
    fp=face.load(); cx,cy=ts//2,ts//2
    for py in range(ts):
        for pwx in range(ts):
            dist=math.sqrt((pwx-cx)**2+(py-cy)**2)/(ts*0.5)
            dist=min(1,dist)
            # Metallic: brighter ring, darker center
            ring=1-abs(dist-0.5)*2
            val=int(155*ring+100*(1-ring))
            fp[pwx,py]=(val,val,val+2)
    # Ring grooves
    d=ImageDraw.Draw(face)
    d.ellipse([4,4,ts-5,ts-5],outline=(100,100,105),width=2)
    d.ellipse([8,8,ts-9,ts-9],outline=(170,170,175),width=1)
    # Spikes
    spike_c=(200,200,205)
    for angle in range(0,360,45):
        rad=math.radians(angle-90)
        for r in range(ts//2-8,ts//3,-1):
            spx=cx+int(r*math.cos(rad)); spy=cy+int(r*math.sin(rad))
            if 0<=spx<ts and 0<spy<ts:
                fp[spx,spy]=spike_c
    # Red warning center
    d.ellipse([cx-5,cy-5,cx+5,cy+5],fill=(230,55,45))
    d.ellipse([cx-2,cy-2,cx+2,cy+2],fill=(255,180,170))
    target.paste(Image.new("L",(ts,ts),0).convert("RGBA"),(x,y))  # clear
    # Make circular mask
    mk=Image.new("L",(ts,ts),0); md=ImageDraw.Draw(mk)
    md.ellipse([0,0,ts-1,ts-1],fill=255)
    target.paste(face,(x,y),mk)

def draw_device_heal(target,sx,sy,sz):
    """Green medical device with soft glow"""
    m=6; hs=sz-m*2; x=sx+m; y=sy+m
    # Glow underneath
    glow=Image.new("RGBA",(hs,hs),(0,0,0,0))
    gd=ImageDraw.Draw(glow)
    gd.rounded_rectangle([-4,-4,hs+4,hs+4],radius=hs//3+4,fill=(40,180,90,60))
    target.paste(glow.filter(ImageFilter.GaussianBlur(radius=5)),(x,y),glow)
    # Face
    face=Image.new("RGB",(hs,hs),(45,150,80))
    fp=face.load(); base=(48,155,85); hi=(90,210,130); sh=(30,100,52)
    bv=4
    for by in range(bv):
        f=by/bv; c=tuple(int(hi[i]*f+base[i]*(1-f))for i in range(3))
        for bx in range(hs): fp[bx,by]=c
    for bx in range(bv):
        f=bx/bv; c=tuple(int(hi[i]*f+base[i]*(1-f))for i in range(3))
        for by in range(bv,hs-bv): fp[bx,by]=c
    for by in range(hs-bv,hs):
        f=(by-hs+bv)/bv; c=tuple(int(base[i]*f+sh[i]*(1-f))for i in range(3))
        for bx in range(hs): fp[bx,by]=c
    for bx in range(hs-bv,hs):
        f=(bx-hs+bv)/bv; c=tuple(int(base[i]*f+sh[i]*(1-f))for i in range(3))
        for by in range(bv,hs-bv): fp[bx,by]=c
    # White cross
    cw,ch=hs//4,hs//2; mx,mx2=hs//4,3*hs//4; my,my2=hs//4,3*hs//4
    d=ImageDraw.Draw(face)
    d.rectangle([mx,my2-ch//2,mx+cw,my2+ch//2],fill=(255,255,255))
    d.rectangle([mx2-ch//2,my,mx2+ch//2,my+ch],fill=(255,255,255))
    mk=Image.new("L",(hs,hs),0); md=ImageDraw.Draw(mk)
    md.rounded_rectangle([0,0,hs-1,hs-1],radius=hs//3,fill=255)
    target.paste(face,(x,y),mk)

def draw_device_damage(target,sx,sy,sz):
    """Red hazard / damage zone"""
    m=6; ds=sz-m*2; x=sx+m; y=sy+m
    # Danger glow
    glow=Image.new("RGBA",(ds,ds),(0,0,0,0))
    gd=ImageDraw.Draw(glow)
    gd.rounded_rectangle([-4,-4,ds+4,ds+4],radius=ds//3+4,fill=(200,50,30,50))
    target.paste(glow.filter(ImageFilter.GaussianBlur(radius=5)),(x,y),glow)
    # Face
    face=Image.new("RGB",(ds,ds),(180,50,40))
    fp=face.load(); base=(185,55,45); hi=(240,100,80); sh=(120,30,22)
    bv=4
    for by in range(bv):
        f=by/bv; c=tuple(int(hi[i]*f+base[i]*(1-f))for i in range(3))
        for bx in range(ds): fp[bx,by]=c
    for bx in range(bv):
        f=bx/bv; c=tuple(int(hi[i]*f+base[i]*(1-f))for i in range(3))
        for by in range(bv,ds-bv): fp[bx,by]=c
    for by in range(ds-bv,ds):
        f=(by-ds+bv)/bv; c=tuple(int(base[i]*f+sh[i]*(1-f))for i in range(3))
        for bx in range(ds): fp[bx,by]=c
    for bx in range(ds-bv,ds):
        f=(bx-ds+bv)/bv; c=tuple(int(base[i]*f+sh[i]*(1-f))for i in range(3))
        for by in range(bv,ds-bv): fp[bx,by]=c
    # Warning triangle
    d=ImageDraw.Draw(face)
    mx,my=ds//2,ds//2; tr=ds//3
    d.polygon([(mx,my-tr),(mx-tr,my+tr//1.5),(mx+tr,my+tr//1.5)],fill=(255,225,100))
    d.polygon([(mx,my-tr+4),(mx-tr+4,my+tr//1.5-2),(mx+tr-4,my+tr//1.5-2)],fill=(180,50,35))
    mk=Image.new("L",(ds,ds),0); md=ImageDraw.Draw(mk)
    md.rounded_rectangle([0,0,ds-1,ds-1],radius=ds//3,fill=255)
    target.paste(face,(x,y),mk)

def draw_device_portal(target,sx,sy,sz):
    """Purple swirling portal with real blur glow"""
    m=5; ps=sz-m*2; x=sx+m; y=sy+m
    # Multi-layer glow (blurred)
    for gr,ga in [(14,40),(10,70),(6,120)]:
        g=Image.new("RGBA",(ps,ps),(0,0,0,0))
        gdraw=ImageDraw.Draw(g)
        gdraw.ellipse([gr,gr,ps-gr,ps-gr],fill=(100+gr*5,50,180,ga))
        target.paste(g.filter(ImageFilter.GaussianBlur(radius=gr//2+2)),(x,y),g)
    # Core rings
    face=Image.new("RGBA",(ps,ps),(0,0,0,0))
    d=ImageDraw.Draw(face)
    d.ellipse([2,2,ps-2,ps-2],fill=(55,25,100,230))
    d.ellipse([6,6,ps-6,ps-6],outline=(100,55,180),width=2)
    d.ellipse([10,10,ps-10,ps-10],outline=(140,90,210),width=2)
    # Bright core
    cr=ps//3
    d.ellipse([ps//2-cr,ps//2-cr,ps//2+cr,ps//2+cr],fill=(190,150,255,255))
    d.ellipse([ps//2-cr//2,ps//2-cr//2,ps//2+cr//2,ps//2+cr//2],fill=(230,210,255,255))
    # Swirl arcs
    d.arc([4,4,ps-4,ps-4],start=30,end=150,fill=(170,120,240,200),width=2)
    d.arc([8,8,ps-8,ps-8],start=210,end=330,fill=(170,120,240,200),width=2)
    target.paste(face,(x,y),face)

def draw_device_support(target,sx,sy,sz):
    """Flag/support point with pole and flag"""
    m=6; ss=sz-m*2; x=sx+m; y=sy+m
    # Pole shadow
    d=ImageDraw.Draw(target)
    d.rectangle([x+ss//2+2,y+6,x+ss//2+5,y+ss-3],fill=(15,22,32,180))
    # Pole (gradient metal)
    pole=Image.new("RGB",(4,ss-10),(180,188,195))
    pp=pole.load()
    for row in range(ss-10):
        f=row/(ss-10)
        c=(int(180+f*40),int(188+f*40),int(195+f*35))
        for col in range(4): pp[col,row]=c
    target.pole=pole; target.paste(pole,(x+ss//2-2,y+5))
    # Flag (triangle with gradient)
    fh=ss//3
    flag=Image.new("RGBA",(ss//2,fh+4),(0,0,0,0))
    fd=ImageDraw.Draw(flag)
    fd.polygon([(2,0),(ss//2-2,fh//2),(2,fh)],fill=(50,130,230,255))
    fd.polygon([(2,1),(ss//2-4,fh//2-1),(2,fh-1)],fill=(100,175,255,200))
    target.paste(flag,(x+ss//2,y+3),flag)
    # Base
    d.rectangle([x+ss//5,y+ss-6,x+4*ss//5,y+ss-2],fill=(95,100,112))
    d.line([(x+ss//5,y+ss-6),(x+4*ss//5,y+ss-6)],fill=(140,148,160),width=1)


DEVICE_FNS={
    "box":draw_device_box,"trap":draw_device_trap,"heal":draw_device_heal,
    "damage":draw_device_damage,"portal":draw_device_portal,"support":draw_device_support,
}

def draw_mechanism(target,col,row,mtype):
    x,y=px(col,row)
    fn=DEVICE_FNS.get(mtype)
    if fn: fn(target,x,y,CELL)


def draw_routes(target, routes):
    d=ImageDraw.Draw(target)
    for ri,rt in enumerate(routes):
        co=(70,155,255) if ri==0 else (255,90,80)
        gl=tuple(v//3 for v in co)
        pts=[px(a,b) for a,b in rt]
        # Glow layer (thick, semi-transparent)
        for i in range(len(pts)-1):
            d.line([pts[i],pts[i+1]],fill=(*gl,100) if len(gl)==3 else gl,width=7)
        # Core layer
        for i in range(len(pts)-1):
            d.line([pts[i],pts[i+1]],fill=co,width=3)
        # Nodes with glow
        for c,r in rt:
            xx,yy=px(c,r)
            d.ellipse([xx+20,yy+20,xx+28,yy+28],fill=(*gl,120) if len(gl)==3 else gl)
            d.ellipse([xx+22,yy+22,xx+26,yy+26],fill=co)


# ════════════════════════════════════════════
# FINAL COMPOSITION
# ════════════════════════════════════════════
def render_final(style_name, bg_color, title_text, subtitle_text, title_fg, subtitle_fg, title_bar_bg):
    # Render at 2x then downsample
    WW,HH=W*SS,H*SS
    img=Image.new("RGB",(WW,HH),bg_color)
    
    # Tiles
    for r,c,t in MAP_DATA:
        cr=pcrect(c,r)
        draw_textured_tile(img,cr,t,seed_base=r*100+c)
        # Coord label
        x,y=ppx(c,r)
        d=ImageDraw.Draw(img)
        label_color=(110,105,98) if style_name=="F" else (80,74,68)
        d.text((x+6,y+4),f"{chr(64+c)},{r}",fill=label_color,font=font(11*SS))
    
    # Routes
    draw_routes(img, ROUTES)
    
    # 3D Doors
    for c,r,n in SPAWNS:
        xx,yy=ppx(c,r)
        draw_real_3d_door(img,xx,yy,CELL*SS,is_red=True,count=n)
    for c,r,_ in GOALS:
        xx,yy=ppx(c,r)
        draw_real_3d_door(img,xx,yy,CELL*SS,is_red=False,count=None)
    
    # Devices
    for c,r,m in MECHANISMS:
        draw_mechanism(img,c,r,m)
    
    # Title bar
    d=ImageDraw.Draw(img)
    d.rectangle([0,0,WW,36*SS],fill=title_bar_bg)
    d.text((12*SS,8*SS),title_text,fill=title_fg,font=font(16*SS))
    d.text((W*SS-250*SS,12*SS),subtitle_text,fill=subtitle_fg,font=font(11*SS))
    
    # Downsample
    out=img.resize((W,H),Image.LANCZOS)
    fname=os.path.join(OUT,f"sample_{style_name.lower()}.png")
    out.save(fname,quality=95)
    print(f"[OK] {style_name}")

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    render_final(
        "F",(20,22,26),
        "Style F: Textured Flat + Real 3D Doors + Devices (Dark)",
        "Noise-textured tiles / gradient 3D / blur glow / shadows",
        (210,205,198),(110,105,98),(26,28,32)
    )
    print("Done!")
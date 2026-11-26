"""Run from this folder: python gen.py. Needs Pillow and ffmpeg. Generates animated icons (GIF), a cover video (MP4) and PH gallery PNGs for cheap-inference 2.0.0."""
import math, random, subprocess, pathlib
from PIL import Image, ImageDraw, ImageFont

OR, DK, CR = (218,85,47), (29,24,20), (244,237,228)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FS = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
def f(p, s): return ImageFont.truetype(p, s)
def ease(t): return t*t*(3-2*t)
def clamp(x): return max(0, min(1, x))
def mix(a, b, t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def center(d, xy, text, font, fill):
    w = d.textlength(text, font=font); d.text((xy[0]-w/2, xy[1]), text, font=font, fill=fill)

# ---------------------------------------------------------------- icons (square, looping)
def icon_funnel(t, S=512):
    im = Image.new("RGB", (S,S), DK); d = ImageDraw.Draw(im)
    d.polygon([(70,150),(442,150),(290,330),(222,330)], fill=CR)
    d.rectangle([222,330,290,400], fill=CR)
    random.seed(3)
    for i in range(9):
        ph = (t + i/9) % 1
        x = 90 + i*42
        y = 40 + ph*140
        a = clamp(1-abs(ph-.4)*2.2)
        # tokens converge toward the neck as they fall
        xx = x + (256-x)*clamp((ph-.2)*1.4)
        d.ellipse([xx-11,y-11,xx+11,y+11], fill=OR if i%2 else CR)
    # the cheap prompt drops out
    p = (t*2) % 1
    d.ellipse([256-12,410+p*60-12,256+12,410+p*60+12], fill=OR)
    return im

def icon_lint(t, S=512):
    im = Image.new("RGB", (S,S), DK); d = ImageDraw.Draw(im)
    for i, ok in enumerate([True, True, False]):
        y = 110 + i*100
        d.rounded_rectangle([60,y,452,y+60], 14, fill=(50,40,34))
        d.rectangle([80,y+22,80+[260,200,300][i],y+38], fill=(120,105,95))
    y = 110 + ease(clamp(t*1.4))*200
    d.rectangle([40,y,472,y+6], fill=OR)
    if t > .55:
        d.rounded_rectangle([60,310,452,370], 14, outline=OR, width=5)
        cx, cy = 410, 340
        d.line([cx-14,cy-14,cx+14,cy+14], fill=OR, width=7); d.line([cx-14,cy+14,cx+14,cy-14], fill=OR, width=7)
    if t < .55:
        for i in range(2):
            if t > .12*(i+1)+.1:
                cy = 140 + i*100; d.line([400,cy,412,cy+12,436,cy-14], fill=(123,216,143), width=7)
    center(d, (256,430), "0 tokens", f(FB,40), CR)
    return im

def icon_ladder(t, S=512):
    im = Image.new("RGB", (S,S), DK); d = ImageDraw.Draw(im)
    for i in range(6):
        h = 50 + i*45
        d.rounded_rectangle([40+i*72, 440-h, 40+i*72+62, 440], 8, fill=mix((90,45,30), OR, i/5))
    step = min(5, int(t*7))
    frac = ease(clamp(t*7 - step))
    pos = lambda k: (40+k*72+31, 440-(50+k*45)-22)
    a, b = pos(step), pos(min(5, step+1))
    x, y = a[0]+(b[0]-a[0])*frac, a[1]+(b[1]-a[1])*frac - math.sin(frac*math.pi)*30
    d.ellipse([x-16,y-16,x+16,y+16], fill=CR); d.ellipse([x-6,y-6,x+6,y+6], fill=DK)
    center(d, (256,36), "one rung at a time", f(FB,30), CR)
    return im

def icon_cache(t, S=512):
    im = Image.new("RGB", (S,S), DK); d = ImageDraw.Draw(im)
    labels = ["rules","tools","docs"]
    for i, l in enumerate(labels):
        d.rounded_rectangle([60,100+i*80,452,160+i*80], 12, fill=OR if (t*3 > i+.2) else (60,48,40))
        center(d, (256,114+i*80), l, f(FB,28), CR if t*3 > i+.2 else (150,135,120))
    d.rounded_rectangle([60,350,452,410], 12, fill=CR); center(d, (256,364), "question", f(FB,28), DK)
    pct = int(97*clamp(t*1.3))
    center(d, (256,430), f"{pct}% cacheable", f(FB,34), OR)
    d.text((60,36), "order = discount", font=f(FB,28), fill=CR)
    return im

def icon_budget(t, S=512):
    im = Image.new("RGB", (S,S), DK); d = ImageDraw.Draw(im)
    k = ease(clamp((t-.15)/.5)) if t < .75 else 1-ease(clamp((t-.75)/.25))
    for i, c in enumerate([OR, CR, OR]):
        y = 130 + i*90
        d.rounded_rectangle([60,y,452,y+50], 12, fill=(50,40,34))
        w = int(392*(1-.82*k))
        d.rounded_rectangle([60,y,60+max(w,24),y+50], 12, fill=c)
    center(d, (256,40), "context diet", f(FB,36), CR)
    center(d, (256,420), "loaded every session", f(FR,26), (170,155,140))
    return im

ICONS = {"funnel": icon_funnel, "linter": icon_lint, "ladder": icon_ladder, "cache": icon_cache, "budget": icon_budget}
def gif(name, fn, frames=36, size=512):
    ims = [fn(i/frames).resize((size,size)) for i in range(frames)]
    out = pathlib.Path("icons")/f"{name}-{size}.gif"
    ims[0].save(out, save_all=True, append_images=ims[1:], duration=60, loop=0, optimize=True)
for n, fn in ICONS.items():
    gif(n, fn); gif(n, fn, size=240)

# ---------------------------------------------------------------- cover video 1280x720, 14 s @ 24 fps
W, H, FPS, DUR = 1280, 720, 24, 14
def bg(): return Image.new("RGB", (W,H), DK)
def fade(t, a, b): return clamp((t-a)/(b-a))

def scene(t):
    im = bg(); d = ImageDraw.Draw(im)
    if t < 3.5:   # hook
        k = ease(fade(t,0,.8))
        for i in range(26):
            ph = ((t*.6)+i/26) % 1
            x = 80 + (i*47) % 1120; y = ph*740-20
            d.ellipse([x-8,y-8,x+8,y+8], fill=mix(DK, OR if i%2 else CR, .5))
        center(d,(W/2,190-20*(1-k)),"Your AI bill",f(FS,92),mix(DK,CR,k))
        center(d,(W/2,300-20*(1-k)),"is not your question.",f(FS,92),mix(DK,OR,k))
        center(d,(W/2,470),"It is everything that rides along with it.",f(FR,34),mix(DK,CR,fade(t,1.4,2.2)))
    elif t < 7:   # zero tokens
        u = t-3.5
        center(d,(W/2,70),"13 tools. 0 tokens.",f(FS,84),CR)
        rows = ['> "The essential feature of the memex ..."','> "build trails of linked documents"','> "The memex was first built in 1975"']
        for i, r in enumerate(rows):
            y = 220+i*95
            d.rounded_rectangle([140,y,1140,y+68],16,fill=(50,40,34))
            d.text((170,y+20),r,font=f(FM,26),fill=CR)
        sy = 205+ease(clamp(u/2.2))*270
        d.rectangle([110,sy,1170,sy+6],fill=OR)
        if u > 1.8:
            d.rounded_rectangle([140,410,1140,478],16,outline=OR,width=5); d.text((800,430),"QUOTE NOT IN SOURCE",font=f(FB,22),fill=OR)
        if u > .5: d.text((1040,238),"OK",font=f(FB,28),fill=(123,216,143))
        if u > 1.2: d.text((1040,333),"OK",font=f(FB,28),fill=(123,216,143))
        center(d,(W/2,560),"A script caught the lie. No model was called.",f(FR,34),mix(DK,CR,fade(u,2.2,2.9)))
    elif t < 10.5:  # ladder
        u = t-7
        center(d,(W/2,60),"Climb one rung. Only with a reason.",f(FS,50),CR)
        for i in range(6):
            h = 70+i*62; x = 130+i*168
            d.rounded_rectangle([x,640-h,x+150,640],14,fill=mix((90,45,30),OR,i/5))
            center(d,(x+75,640-h+18),["inline","one call","few calls","one agent","fan-out","premium"][i],f(FB,22),CR)
        step = min(5,int(u*1.6)); fr = ease(clamp(u*1.6-step))
        P = lambda k:(130+k*168+75, 640-(70+k*62)-30)
        a,b = P(step),P(min(5,step+1))
        x = a[0]+(b[0]-a[0])*fr; y = a[1]+(b[1]-a[1])*fr - math.sin(fr*math.pi)*50
        d.ellipse([x-22,y-22,x+22,y+22],fill=CR); d.ellipse([x-9,y-9,x+9,y+9],fill=DK)
    else:          # CTA
        u = t-10.5; k = ease(fade(u,0,.7))
        center(d,(W/2,150),"cheap-inference",f(FS,104),mix(DK,CR,k))
        center(d,(W/2,290),"2.0.0",f(FB,64),mix(DK,OR,k))
        center(d,(W/2,400),"42 prompts · 100 tips · 14 chapters · MIT",f(FR,34),mix(DK,CR,fade(u,.4,1.1)))
        d.rounded_rectangle([230,480,1050,560],40,fill=mix(DK,OR,fade(u,.8,1.4)))
        center(d,(W/2,506),"github.com/paulfxyz/cheap-inference",f(FB,30),mix(DK,DK,1) if u>1.4 else DK)
    return im

import tempfile, shutil
tmp = pathlib.Path(tempfile.mkdtemp())
for i in range(FPS*DUR):
    scene(i/FPS).save(tmp/f"f{i:04d}.png")
Image.open(tmp/f"f{int(11.5*FPS):04d}.png").save("video/cover-1280x720.png")
subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(tmp/"f%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","22","video/cheap-inference-cover.mp4"],check=True)
# square 1080 crop for LinkedIn feed variants
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","video/cheap-inference-cover.mp4","-vf","scale=1280:720","-an","-t","14","-c:v","libx264","-pix_fmt","yuv420p","video/cheap-inference-cover-silent.mp4"],check=True)
# PH gallery: stills from the video at 1270x760
for name, sec in [("1-hook",1.8),("2-zero-tokens",6.2),("3-ladder",9.6),("4-cta",12.8)]:
    Image.open(tmp/f"f{int(sec*FPS):04d}.png").resize((1270,760)).save(f"producthunt/gallery-{name}.png")
# PH thumbnail: 240x240 animated GIF
gif_path = pathlib.Path("producthunt/thumbnail-240.gif"); shutil.copy("icons/funnel-240.gif", gif_path)
shutil.rmtree(tmp)
print("done")

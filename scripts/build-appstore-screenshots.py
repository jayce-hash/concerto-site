from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json, sys
from pathlib import Path
SITE=Path('/home/claude/work/site/concerto-site-2-8'); SCR=SITE/'img/product/screens'; man=json.loads((SCR/'manifest.json').read_text())
NAVY=(18,30,54); GOLD=(201,168,76); GOLD2=(230,201,109); CREAM=(248,249,249); PAPER=(252,252,250); MUTED=(95,106,126); SAND=(243,238,227)
PF='/tmp/fonts/PlayfairDisplay.ttf'; DM='/tmp/fonts/dm-fonts-main/Sans/fonts/ttf/DMSans-Medium.ttf'; DMB='/tmp/fonts/dm-fonts-main/Sans/fonts/ttf/DMSans-Bold.ttf'
def pf(size):
    f=ImageFont.truetype(PF,size); f.set_variation_by_name('Medium'); return f
SS=2
FRAMES=[
 dict(shot='home', eyebrow='YOUR NEXT SHOW', title='One tap from\neverything.', sub='Home tells you where you are going next. Your Night tells you everything about that night.', bg='cream'),
 dict(shot='your-night', eyebrow='YOUR NIGHT', title='The whole night,\nin one place.', sub='Venue rules, weather, setlist, nearby places, getting there, and getting home for the show you saved.', bg='navy'),
 dict(shot='venue', eyebrow='VERIFIED VENUE GUIDES', title='Know before\nyou go.', sub='Bag policy, parking, rideshare, entrances, and concessions for 300+ venues. Researched from official sources and dated.', bg='cream'),
 dict(shot='near-me', eyebrow='NEAR ME', title='Every show\naround you.', sub='Live music by location and date, night by night. Save one and the countdown starts.', bg='navy'),
 dict(shot='premium', eyebrow='CONCERTO+', title='Your whole night,\nplanned around you.', sub='Plan My Night builds dinner, arrival, parking, and the ride home around your exact show.', bg='sand', offset=0.185),
]
def wrap(draw,text,font,maxw):
    words=text.split(); lines=[]; cur=''
    for w in words:
        t=(cur+' '+w).strip()
        if draw.textlength(t,font=font)<=maxw: cur=t
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines
def device(shot_path, width, offset=0.0):
    im=Image.open(shot_path).convert('RGB')
    if offset:
        bar=round(im.height*0.049); y0=int(im.height*offset); tab_top=int(im.height*0.905)
        body=im.crop((0,y0,im.width,tab_top)); tab=im.crop((0,tab_top,im.width,im.height))
        out=Image.new('RGB',im.size,(248,249,249))
        out.paste(im.crop((0,0,im.width,bar)),(0,0)); out.paste(body,(0,bar)); out.paste(tab,(0,tab_top)); im=out
    ar=im.height/im.width; bezel=int(width*0.028); radius_out=int(width*0.17); radius_in=radius_out-bezel
    W=width; H=int(W*ar)+2*bezel
    canvas=Image.new('RGBA',(W*SS,H*SS),(0,0,0,0)); d=ImageDraw.Draw(canvas)
    # body gradient-ish: dark with lighter edge
    d.rounded_rectangle((0,0,W*SS-1,H*SS-1),radius=radius_out*SS,fill=(12,13,16))
    d.rounded_rectangle((2*SS,2*SS,W*SS-3*SS,H*SS-3*SS),radius=(radius_out-2)*SS,outline=(70,74,82),width=2*SS)
    screen=im.resize(((W-2*bezel)*SS,(H-2*bezel)*SS),Image.LANCZOS)
    mask=Image.new('L',screen.size,0); ImageDraw.Draw(mask).rounded_rectangle((0,0,screen.width-1,screen.height-1),radius=radius_in*SS,fill=255)
    canvas.paste(screen,(bezel*SS,bezel*SS),mask)
    # dynamic island
    iw=int(W*0.26); ih=int(W*0.075); ix=(W-iw)//2; iy=bezel+int(W*0.055)
    d.rounded_rectangle((ix*SS,iy*SS,(ix+iw)*SS,(iy+ih)*SS),radius=ih*SS//2,fill=(5,5,5))
    return canvas.resize((W,H),Image.LANCZOS)
def frame(spec, size, out):
    W,H=size; s=W/1320
    bgc={'cream':PAPER,'navy':NAVY,'sand':SAND}[spec['bg']]; dark=spec['bg']=='navy'
    img=Image.new('RGB',(W,H),bgc); d=ImageDraw.Draw(img)
    # soft gold glow behind phone
    glow=Image.new('RGBA',(W,H),(0,0,0,0)); g=ImageDraw.Draw(glow)
    g.ellipse((W*0.15,H*0.42,W*0.85,H*1.02),fill=(201,168,76,70 if not dark else 55)); glow=glow.filter(ImageFilter.GaussianBlur(int(120*s)))
    img.paste(glow,(0,0),glow)
    d=ImageDraw.Draw(img)
    ink=(255,255,255) if dark else NAVY; sub=(255,255,255,170) if dark else MUTED
    eyebrow_font=ImageFont.truetype(DMB,int(34*s)); title_font=pf(int(118*s)); sub_font=ImageFont.truetype(DM,int(44*s))
    x=int(96*s); y=int(190*s)
    bf=ImageFont.truetype(DMB,int(26*s)); tag='CONCERTO  ·  FROM THE CONCERT TO THE CITY®'
    d.text((x,int(96*s)),tag,font=bf,fill=(GOLD2 if dark else GOLD))
    y=int(226*s)
    # eyebrow with gold rule
    d.text((x,y),spec['eyebrow'],font=eyebrow_font,fill=GOLD if not dark else GOLD2); 
    # letter-spaced eyebrow: draw char by char
    d.rectangle((x,y-int(2*s),x,y),fill=bgc)
    ew=0
    for ch in spec['eyebrow']:
        pass
    y+=int(80*s)
    for line in spec['title'].split('\n'):
        d.text((x,y),line,font=title_font,fill=ink); y+=int(122*s)
    y+=int(22*s)
    for line in wrap(d,spec['sub'],sub_font,W-2*x):
        d.text((x,y),line,font=sub_font,fill=(255,255,255) if dark else MUTED); y+=int(60*s)
    if dark:  # soften sub on navy
        pass
    # phone
    pw=int(W*0.70); dev=device(SCR/man[spec['shot']],pw,spec.get('offset',0))
    py=max(y+int(70*s), int(H*0.36))
    shadow=Image.new('RGBA',(W,H),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
    sd.rounded_rectangle(((W-pw)//2+int(10*s),py+int(60*s),(W+pw)//2-int(10*s),py+dev.height),radius=int(pw*0.17),fill=(18,30,54,110)); shadow=shadow.filter(ImageFilter.GaussianBlur(int(70*s)))
    img.paste(shadow,(0,0),shadow)
    img.paste(dev,((W-pw)//2,py),dev)
    img.save(out,quality=95)
    return out
if __name__=='__main__':
    sizes={'6.9':(1320,2868),'6.5':(1284,2778)}
    for label,size in sizes.items():
        outdir=Path(f'/home/claude/work/appstore/{label}-inch'); outdir.mkdir(parents=True,exist_ok=True)
        for i,spec in enumerate(FRAMES,1):
            frame(spec,size,outdir/f'{i:02d}-{spec["shot"]}.png')
    print('done')

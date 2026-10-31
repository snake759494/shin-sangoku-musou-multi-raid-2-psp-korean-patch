from PIL import Image,ImageDraw,ImageFont
import numpy as np
def glyph(ch,font,cs,size,thr=110,dy=0,dx=0):
    im=Image.new('L',(cs*4,cs*4),0); dr=ImageDraw.Draw(im)
    f=ImageFont.truetype(font,size)
    bb=dr.textbbox((0,0),ch,font=f)
    w=bb[2]-bb[0]
    x=(cs-w)//2-bb[0]+cs+dx
    asc,desc=f.getmetrics()
    y=cs+(cs-(asc+desc))//2+dy
    dr.text((x,y),ch,font=f,fill=255)
    a=np.array(im)[cs:2*cs,cs:2*cs]
    return [[1 if v>=thr else 0 for v in row] for row in a]

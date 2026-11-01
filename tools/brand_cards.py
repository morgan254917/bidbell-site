"""Render BidBell's code-authored social cards using its shared logo and font."""
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[1]
f=TTFont(ROOT/'fonts/public-sans.woff2');f.flavor=None;buf=BytesIO();f.save(buf);FONT=buf.getvalue()
INK='#191b30';CREAM='#faf8f3';MUTED='#60616d';LAVENDER='#e5dff7';CORAL='#d8664e';LINE='#deddd7'
def font(size,bold=False):
 f=ImageFont.truetype(BytesIO(FONT),size)
 try:f.set_variation_by_axes([750 if bold else 400])
 except (ValueError,OSError):pass
 return f
def label(d,xy,text,size=28,bold=False,fill=INK):d.text(xy,text,font=font(size,bold),fill=fill)
def bell(im,xy,size):im.paste(Image.open(ROOT/'brand-icon.png').convert('RGB').resize((size,size),Image.Resampling.LANCZOS),xy)
def square(tag='ONE BIDBELL PLAN',headline=('Find the bid.','Build the response.')):
 im=Image.new('RGB',(1080,1080),CREAM);d=ImageDraw.Draw(im)
 bell(im,(52,48),88);label(d,(146,64),'BidBell',46,True);label(d,(320,64),'.',46,True,CORAL)
 label(d,(70,190),tag,22,True,MUTED)
 for i,line in enumerate(headline):label(d,(65,250+i*105),line,86,True)
 label(d,(70,495),'Daily alerts + AI-assisted bid preparation.',30)
 label(d,(70,546),'Your company facts. Your sources. Your final review.',26,False,MUTED)
 for i,t in enumerate(['Open the bid','Reuse details','Draft with AI','Review + export']):
  x=70+i*238;d.rounded_rectangle((x,660,x+220,780),radius=18,fill=LAVENDER if i%2==0 else '#f2e3db')
  label(d,(x+17,677),'0'+str(i+1),19,True,MUTED);label(d,(x+17,720),t,22,True)
  if i<3:label(d,(x+223,701),'>',18,False,MUTED)
 d.line((70,850,1010,850),fill=LINE,width=2)
 label(d,(70,883),'14 days free. No card.',34,True)
 label(d,(70,935),'Then US$39/month if you continue. Usage limits apply.',23,False,MUTED)
 label(d,(70,1000),'getbidbell.com',27,True)
 return im
def cover(width=1640,height=624):
 im=Image.new('RGB',(width,height),CREAM);d=ImageDraw.Draw(im)
 # The centered content remains clear when Facebook crops the sides on phones.
 scale=width/1640
 def txt(y,t,sz,bold=False,color=INK):
  ft=font(round(sz*scale),bold);box=d.textbbox((0,0),t,font=ft);d.text(((width-(box[2]-box[0]))/2,y*height/624),t,font=ft,fill=color)
 bell(im,(round(width*.405),round(height*.085)),round(width*.04))
 txt(65,'BidBell',42,True)
 txt(145,'Find the bid.',62,True)
 txt(220,'Build the response.',62,True)
 txt(325,'Daily alerts + AI-assisted bid preparation.',30)
 txt(380,'Open a bid. Reuse your details. Draft. Review. Export.',24,False,MUTED)
 txt(455,'14 days free, no card. Then US$39/month if you continue.',24,True)
 txt(510,'getbidbell.com',26,True,CORAL)
 return im
if __name__=='__main__':
 tags={'bid-janitorial':'JANITORIAL OPPORTUNITIES','bid-carpet':'CARPET CLEANING OPPORTUNITIES','bid-window':'WINDOW + EXTERIOR OPPORTUNITIES','bid-small':'SMALL BUSINESS OPPORTUNITIES','bid-hubzone':'HUBZONE OPPORTUNITIES','bid-sdvosb':'SDVOSB OPPORTUNITIES','bid-wosb':'WOSB OPPORTUNITIES','brand':'ONE BIDBELL PLAN','bb-calendar':'YOUR OPPORTUNITY CALENDAR','bb-friday':'YOUR WEEK. YOUR NEXT RESPONSE.','bb-texas':'TEXAS CLEANING OPPORTUNITIES','bb-veterans-day':'YOUR COMPANY. YOUR NEXT OPPORTUNITY.'}
 for name,tag in tags.items():square(tag).save(ROOT/'social'/f'{name}.jpg',quality=94)
 cover().save(ROOT/'social/facebook-cover.jpg',quality=95)
 cover(1200,630).save(ROOT/'og.png')
 print('Rendered 12 shared-brand cards, Facebook cover and social preview.')

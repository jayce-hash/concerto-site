"""Original web-native illustrations. No app captures or third-party artwork."""
def stage():
    seats = ''.join(f'<path d="M{80+i*20} {350+i*22} Q600 {650+i*10} {1120-i*20} {350+i*22}"/>' for i in range(7))
    return f'''<div class="night-art" aria-hidden="true"><svg viewBox="0 0 1200 620" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="stage-beam" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#C9A84C" stop-opacity=".22"/><stop offset="1" stop-color="#C9A84C" stop-opacity="0"/></linearGradient></defs><ellipse cx="600" cy="352" rx="220" ry="78" stroke="#C9A84C" stroke-width="1.5"/><ellipse cx="600" cy="352" rx="202" ry="63" stroke="#C9A84C" stroke-opacity=".45"/><path d="M430 327L230 0H430L470 327M770 327L970 0H770L730 327" fill="url(#stage-beam)"/><path d="M510 324L480 30H530L550 324M690 324L720 30H670L650 324" fill="url(#stage-beam)"/><g stroke="#F8F9F9" stroke-opacity=".17">{seats}</g><path d="M430 320H770V360H430z" fill="#1C2B4A" stroke="#C9A84C"/><path d="M600 282v38m-7-39a7 7 0 1 0 14 0a7 7 0 1 0-14 0" stroke="#F8F9F9" stroke-width="2"/><g fill="#C9A84C"><circle cx="192" cy="309" r="3"/><circle cx="997" cy="389" r="3"/><circle cx="325" cy="464" r="3"/><circle cx="870" cy="489" r="3"/><circle cx="586" cy="518" r="3"/></g></svg><div class="art-caption"><span>THE TICKET IS JUST THE BEGINNING</span><span>THE REST IS YOUR NIGHT</span></div></div>'''

def route(kind='before'):
    data = {
      'before': ('Make it your night.', [('Find your show','A date worth saving'),('Know the venue','The details before you go'),('Explore the city','Somewhere good nearby')]),
      'there': ('Walk in ready.', [('Bag policy','Check the published rules'),('Getting there','Parking and arrival guidance'),('The music','Available setlists and playlists')]),
      'after': ('One last thing.', [('The encore','Stay for your favorite part'),('Your pickup','Check the venue’s guidance'),('The way home','Keep ride links close')]),
      'plan': ('An evening, connected.', [('Before','Find dinner nearby'),('The show','Build around your concert'),('After','Plan the way home')]),
    }
    title, steps = data.get(kind, data['plan'])
    items=''.join(f'<li><span class="route-dot">0{i+1}</span><div><strong>{name}</strong><span>{detail}</span></div></li>' for i,(name,detail) in enumerate(steps))
    return f'<div class="night-route"><p class="eyebrow">The Concerto approach</p><h3>{title}</h3><ol>{items}</ol><p class="route-note">One concert. Everything around it.</p></div>'

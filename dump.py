

%matplotlib inline
import pyautogui
import numpy as np
from IPython.display import clear_output
from pytesseract import image_to_string
from PIL import Image
import time

import creds #make this yourself

#Color/bitmap finding routines

def rgb2hsl(x):
    '''converts an [...,3] RGB image to an [...,3] HSL image'''
    hsl = np.empty_like(x,dtype='float32')
    x = np.asarray(x,dtype='float32')/255.0
    m = np.min(x,axis=-1)
    M = np.max(x,axis=-1)
    c = M-m
    dg = c==0
    ndg = ~dg
    r = x[...,0]
    g = x[...,1]
    b = x[...,2]
    hsl[...,2]=(M+m)/2
    hsl[ndg,1]=c[ndg]/(1.0-np.abs(2.0*hsl[ndg,2]-1.0))
    maskr = np.logical_and(np.equal(r,M),ndg)
    hsl[maskr,0] = (g[maskr] - b[maskr]) / c[maskr] / 6.0 + np.where(g[maskr] < b[maskr],1.0,0.0)
    maskg = np.logical_and(np.equal(g,M),ndg)
    hsl[maskg,0] = (b[maskg] - r[maskg]) / c[maskg] / 6.0 + 1.0/3.0
    maskb = np.logical_and(np.equal(b,M),ndg)
    hsl[maskb,0] = (r[maskb] - g[maskb]) / c[maskb] / 6.0 + 2.0/3.0
    hsl[dg,0] = 0.0
    hsl[dg,1] = 0.0
    return hsl

def hsl_val(a,b,a_rgb=True,b_rgb=True):
    '''returns the change in hue,sat,lum for each coordinate in a,b
       a,b can be preconverted to hsl and the *_rgb kwarg set to save time'''
    a = rgb2hsl(a) if a_rgb else a
    b = rgb2hsl(b) if b_rgb else b
    dh = np.abs(a[...,0]-b[...,0])
    dh[dh>0.5] = 1.0 - dh[dh>0.5]
    ds = np.abs(a[...,1]-b[...,1])
    dl = np.abs(a[...,2]-b[...,2])
    return dh,ds,dl
def hsl_cmp(a,b,tol,a_rgb=True,b_rgb=True):
    '''returns a boolean mask for values that satisfy tolerange requirements between a,b
       tolerance requires difference between hue,sat,lum to be separately less than tol
       a,b can be preconverted to hsl and the *_rgb kwarg set to save time'''
    dh,ds,dl = hsl_val(a,b,a_rgb,b_rgb)
    try:
        return np.logical_and(dh < tol[0],np.logical_and(ds < tol[1],dl < tol[2]))
    except TypeError:
        return np.logical_and(dh < tol,np.logical_and(ds < tol,dl < tol))

def dist_val(a,b):
    '''returns the sum of squared RGB color distance for each coordinate of a,b normalized such that dist(black,white)=1.0'''
    return np.sum(np.square(a-b),axis=-1) / (3*255**2.0)
def dist_cmp(a,b,tol):
    '''returns a boolean mask for values that satisfy tolerange requirements between a,b
       tolerance requires the quadrature sum of channel distances to be less than tol'''
    return dist_val(a,b) < tol*tol

def diff_val(a,b):
    '''returns the sum of absolute RGB distance for each coordinate of a,b normalized such that dist(black,white)=1.0'''
    return np.sum(np.abs(a-b),axis=-1) / (3*255)
def diff_cmp(a,b,tol):
    '''returns a boolean mask for values that satisfy tolerange requirements between a,b
       tolerance requires the sum of channel distances to be less than tol'''
    return diff_val(a,b) < tol

def get_val(mode):
    '''return the distance function for the given color mode'''
    if mode == 'diff':
        val = diff_val
    elif mode == 'dist':
        val = dist_val
    elif mode == 'hsl':
        val = hsl_val
    else:
        raise RuntimeError('Unknown tolerance mode: %s'%mode)
    return val
def get_cmp(mode):
    '''return the comparator function for the given color mode'''
    if mode == 'diff':
        cmp = diff_cmp
    elif mode == 'dist':
        cmp = dist_cmp
    elif mode == 'hsl':
        cmp = hsl_cmp
    else:
        raise RuntimeError('Unknown tolerance mode: %s'%mode)
    return cmp

def find_bitmap_prob(bmp,region,mask=None,mode='dist'):
    '''compare to matchTemplate in opencv - returns the distance between bmp and every possible location in region'''
    hr,wr=region.shape[:2]
    hs,ws=bmp.shape[:2]
    val = get_val(mode)
    if mode == 'hsl':
        bmp = rgb2hsl(bmp)
        region = rgb2hsl(region)
        if mask is not None:
            return np.asarray([[np.sum(val(bmp[mask],region[i:i+hs,j:j+ws][mask],a_rgb=False,b_rgb=False)[0]) for j in range(wr-ws)] for i in range(hr-hs)])
        else:
            return np.asarray([[np.sum(val(bmp,region[i:i+hs,j:j+ws],a_rgb=False,b_rgb=False)[0]) for j in range(wr-ws)] for i in range(hr-hs)])
    else:
        if mask is not None:
            return np.asarray([[np.sum(val(bmp[mask],region[i:i+hs,j:j+ws][mask])) for j in range(wr-ws)] for i in range(hr-hs)])
        else:
            return np.asarray([[np.sum(val(bmp,region[i:i+hs,j:j+ws])) for j in range(wr-ws)] for i in range(hr-hs)])

def find_best_bitmap(bmp,region,tol=0.4):
    probs = find_bitmap_prob(bmp,region)
    found = np.asarray(np.nonzero(probs < tol))
    return found[[1,0]].T
        
def find_bitmap(bmp,region,tol=0.01,mask=None,mode='dist'):
    '''similar to find_bitmap_prob but uses the heuristic that each pixel must match better than some tolerance.
       Only returns the coordinates of potential matches.'''
    xs,ys=0,0
    hr,wr=region.shape[:2]
    hs,ws=bmp.shape[:2]
    cmp = get_cmp(mode)
    if mask is None:
        candidates = np.asarray(np.nonzero(cmp(bmp[0,0],region[:-hs,:-ws],tol)))
    else:
        candidates = np.asarray(np.nonzero(np.ones((hr-hs+1,wr-ws+1))))
    for i in np.arange(0,hs):
        for j in np.arange(0,ws):
            if (mask is None and i==0 and j==0) or (mask is not None and not mask[i,j]):
                continue
            view = region[candidates[0]+i,candidates[1]+j,:]
            passed = cmp(bmp[i,j],view,tol)
            candidates = candidates.T[passed].T
        
    return candidates[[1,0],:].T

def find_colors(color,region,tol=0.1,mode='dist'):
    '''finds all instance of color in region'''
    cmp = get_cmp(mode)
    mask = cmp(region,color,tol)
    found = np.argwhere(mask)[:,[1,0]]
    return found

def filter_near(a,b,dist):    
    '''returns all points in a within some distance to a point in b'''
    if len(a) == 0 or len(b) == 0:
        return np.asarray([])
    diffs = np.asarray([(i,np.min(np.sum(np.square(p-b),axis=-1))) for i,p in enumerate(a)])
    return a[diffs[:,1]<dist*dist]

def filter_far(a,b,dist):    
    '''returns all points in a within some distance to a point in b'''
    if len(a) == 0:
        return np.asarray([])
    if len(b) == 0:
        return a
    diffs = np.asarray([(i,np.min(np.sum(np.square(p-b),axis=-1))) for i,p in enumerate(a)])
    return a[diffs[:,1]>dist*dist]

def filter_radius(pts,center,radius):
    '''returns all points in pts within radius of the center point'''
    return pts[np.sum(np.square(pts-center),axis=-1)<radius*radius]

def closest(point,points):
    '''returns the closest value in points to the given point'''
    sorter = np.argsort(np.sum(np.square(points-point),axis=-1))
    return points[np.argmin(sorter)]

def cluster(points,radius=5):
    clusters = np.zeros(len(points),dtype='uint32')
    while True: #loop until all points are clustered
        unclustered = clusters==0
        remaining = np.count_nonzero(unclustered)
        if remaining == 0:
            break 
        # any points near this group (and their points) become a new group
        candidate = points[unclustered][np.random.randint(remaining)] #do this randomly to save time
        dist = np.sum(np.square(points-candidate),axis=1)
        nearby_mask = dist<=radius*radius #importantly includes candidate point
        overlaps = set(list(clusters[nearby_mask])) #groups that were close
        overlaps.remove(0)
        if len(overlaps) == 0:
            G = np.max(clusters)+1 #new cluster
        else:
            G = np.min(list(overlaps)) #prefer smaller numbers
        #set all nearby clusters to index G
        clusters[nearby_mask] = G
        for g in overlaps:
            if g == G or g == 0:
                continue
            clusters[clusters==g] = G
    unique, counts = np.unique(clusters, return_counts=True)
    cluster_points = np.asarray([points[clusters==c] for c in unique],dtype='object')
    return cluster_points,counts

#bitmap and convenience functions
minimap_mask = np.asarray(Image.open('minimap_mask.png'))[:,:,0] == 255
anchor = np.asarray(Image.open('anchor.png')) #image (always) on the client's banner

# misc useful coordinates
x0,y0 = 0,0 #set by target() used throughout
w,h = 765,503
msxs,msxe,msys,msye = 5,519,5,337
msw,msh = (msxe-msxs+1),(msye-msys+1)
msxc,msyc = msxs+msw/2,msys+msh/2
ivxs,ivxe,ivys,ivye = 560,737,207,460
ivw,ivh = (ivxe-ivxs+1),(ivye-ivys+1)
mmxs,mmxe,mmys,mmye = 548,726,3,165
mmxc,mmyc=647,85

def target():
    '''looks for the client and caches its location'''
    global x0,y0
    desktop = np.asarray(pyautogui.screenshot())
    pts = find_bitmap(anchor,desktop)
    assert len(pts)==1,'window ambiguious or not found'
    x0,y0 = pts[0]+[0,anchor.shape[1]]

#functions to grab images of client - smaller region is faster maybe?
def get_client():
    return np.asarray(pyautogui.screenshot(region=(x0,y0,w,h)))
def get_mainscreen():
    return np.asarray(pyautogui.screenshot(region=(x0+msxs,y0+msys,msxe-msxs+1,msye-msys+1)))
def get_uptext(width=400):
    return np.asarray(pyautogui.screenshot(region=(x0+7,y0+7,width-7+1,23-7+1)))
def get_minimap():
    return np.asarray(pyautogui.screenshot(region=(x0+mmxs,y0+mmys,mmxe-mmxs+1,mmye-mmys+1)))
def get_compass():
    return np.asarray(pyautogui.screenshot(region=(x0+mmxs,y0+mmys,37,35)))
def get_inventory():
    return np.asarray(pyautogui.screenshot(region=(x0+ivxs,y0+ivys,ivxe-ivxs+1,ivye-ivys+1)))

def get_compass_angle():
    compass = get_compass()
    red = find_colors([238,0,0],compass,0.2)-np.asarray(compass.shape)[[1,0]]/2
    clusters,counts = cluster(red,radius=5)
    tips = clusters[counts<5]
    meanxy = np.asarray([np.mean(tip.T,axis=1) for tip in clusters[counts<5]])
    meanxy = np.mean(meanxy.T,axis=1)
    direction = [-1,1]*meanxy/np.sqrt(np.sum(np.square(meanxy)))
    return np.mod(-np.arctan2(direction[1],direction[0])/np.pi*180+90,360)

def polish_minimap(min_same=28,horizontal=True,bounds=30,click=True):
    if click:
        click_mouse(mmxc,mmyc)
    bestn = 0
    left = True
    pyautogui.PAUSE = 0.001
    while True:
        deg = get_compass_angle()
        left = np.random.random() < 0.5
        if deg < 360-bounds and deg > 180:
            left = False
        if deg < 180 and deg > bounds:
            left = True
        if left:
            pyautogui.keyDown('left')
            time.sleep(0.1*np.random.random())
            pyautogui.keyUp('left')
        else:
            pyautogui.keyDown('right')
            time.sleep(0.1*np.random.random())
            pyautogui.keyUp('right')
            
        minimap = get_minimap()
        walls = find_colors([238,238,238],minimap,tol=0.05)
        vals,counts = np.unique(walls[:,1 if horizontal else 0],return_counts=True)
        maxn = np.max(counts)
        print(maxn)
        if maxn >= min_same and (deg > 360-bounds or deg < bounds):
            break
    pyautogui.PAUSE = 0.1

def flag_wait(init=2.0,step=0.2,post=1.5,imax=50):
    '''sleeps the init time, then each step while the flag stem is visible up to imax times, finally sleeping post'''
    time.sleep(init)
    i = 0
    while True:
        minimap = get_minimap()
        i = i+1
        if i > imax:
            break
        if len(find_bitmap(flag,minimap)) == 0:
            time.sleep(post)
            break
        time.sleep(step)

def uptext_mask(uptext,width=None):
    '''provides a black-on-white mask of an uptext image for OCR'''
    uptext = uptext[:,:width] if width is not None else uptext
    white = find_colors([225,225,225],uptext,tol=0.1)
    cyan = find_colors([0,225,225],uptext,tol=0.1)
    yel = find_colors([225,225,0],uptext,tol=0.1)
    thresh = np.full_like(uptext,255)
    
    for c in [white,cyan,yel]:
        thresh[c[:,1],c[:,0]] = [0,0,0]

    return uptext,thresh

def move_mouse(x,y,speed=1.0):
    '''moves the mouse to a point'''
    cx,cy = pyautogui.position()
    ex,ey = x+x0,y+y0
    dt = np.sqrt((cx-x)**2.0+(cy-y)**2.0)/(speed*1000)
    pyautogui.moveTo(ex,ey,dt,pyautogui.easeOutQuad)

def click_mouse(x,y,left=True,speed=1.0):
    '''moves to and clicks a point'''
    move_mouse(x,y,speed=speed)
    pyautogui.click(button='left' if left else 'right')
    
def send_keys(text,speed=1.0):
    '''sends text to the client (\n for enter)'''
    pyautogui.typewrite(text,interval=0.05*speed)

flag = np.asarray(Image.open('flag.png'))
loginscreen = np.asarray(Image.open('loginscreen.png'))
existinguser = np.asarray(Image.open('existinguser.png'))
use_booth = np.asarray(Image.open('use_booth.png'))
bank_window = np.asarray(Image.open('bank_window.png'))
store_all = np.asarray(Image.open('store_all.png'))
crumbling = np.asarray(Image.open('crumbling.png'))
minerocks,minerocks_mask = uptext_mask(np.asarray(Image.open('minerocks.png')))

west_road = [122,117,70]
east_road = [121,119,97]
wall_color = [190,184,155]
inner_wall_color = [60,60,50]
outer_wall_color = [73,64,41]

copper_color = [174,126,81]
tin_color = [149,138,138]
iron_color = [60,35,28]
gold_color = [251,204,31]
silver_color = []

#higher level routines

def login():    
    '''basic login routine - assumes current state is login window'''
    print('logging in')
    if len(find_bitmap(existinguser,client)) > 0:
        click_mouse(463,291)
        time.sleep(2.0)
    click_mouse(355,240)
    time.sleep(2.0)
    send_keys('%s\n%s'%(creds.username,creds.password))
    time.sleep(1.0)
    click_mouse(305,326)
    time.sleep(5.0)
    click_mouse(401,335)
    time.sleep(5.0)

def count_inv(mask=False,color=[1,0,0],tol=0.02):
    '''counts the number of items with the given color (default is shadow, so all) in the inventory'''
    inventory = get_inventory()
    w,h = 42,36
    grid = [[len(find_colors(color,inventory[h*i:h*i+h,w*j:w*j+w],tol=tol))>0 for i in range(7)] for j in range(4)]
    return grid if mask else np.count_nonzero(grid)

def count_rocks(weighted=True,rocks=None):
    '''finds the weighted count of each rock in the inventory for each rock the rocks list'''
    count_inv
    raw_counts = np.asarray([(count_inv(color=invc,tol=tol),weight) for weight,color,tol,invc in rocks])
    return raw_counts[:,0]/raw_counts[:,1] if weighted else raw_counts[:,0]


bank_floor_colors = [[130,60,47],[170,104,80]]
def open_bank():
    '''opens bank window if not already open - FALADOR WEST ONLY
       bank is found by proximity of npc points to a unique bank floor color
       booth is found by proximity of two colors on the booth (dark top and light mid area)
       right clicks booth and checks for Use Quickly, tries next option if not found'''
    mainscreen = get_mainscreen()
    if len(find_bitmap(bank_window,mainscreen)) > 0:
        return True
    minimap = get_minimap()
    npc_points = find_colors([255,255,0],minimap,tol=0.05,mode='hsl')
    bank_points = np.concatenate([find_colors(bank_floor,minimap,tol=0.085,mode='hsl') for bank_floor in bank_floor_colors])
    print('Bank points:',len(bank_points))
    clusters,counts = cluster(bank_points)
    if len(counts) < 1 or np.count_nonzero(counts>20) < 1:
        bank_points = np.asarray([])
    else:
        bank_points = clusters[np.random.choice(np.nonzero(counts>20)[0])]
    print('Clustered bank points:',len(bank_points))
    bank_points = filter_near(npc_points,bank_points,6)
    print('Points near NPCs:',len(bank_points))
    np.random.shuffle(bank_points)
    if len(bank_points) < 15:
        return False
    click_mouse(*(bank_points[0]+[mmxs,mmys-8]))
    flag_wait()
    flag_wait()
    mainscreen = get_mainscreen()
    pa = find_colors([74,70,70],mainscreen,tol=0.02,mode='hsl')
    pb = find_colors([118,96,68],mainscreen,tol=0.02,mode='hsl')
    points = filter_near(pa,pb,20)
    np.random.shuffle(points)
    if len(points) > 1:
        minidx = np.argmin(np.sum(np.square(points-[msxc-msxs,msyc-msys]),axis=1))
        points[-1],points[minidx] = points[minidx],points[-1]
    for point in points[-5:]:
        click_mouse(*point,left=False)
        time.sleep(0.05)
        use = find_bitmap(use_booth,get_mainscreen())
        if len(use) > 0:
            click_mouse(*(use[0]+[10,10]))
            flag_wait()
            return True
        move_mouse(*(point+[0,-25]))
    return False
            
def deposit_all():
    '''searches for border colors in inventory and deposits them all to bank
       assumes bank window already open'''
    mainscreen = get_mainscreen()
    while len(find_bitmap(bank_window,mainscreen)) > 0:
        inventory = get_inventory()
        found = find_colors([1,0,0],inventory)
        if len(found):
            np.random.shuffle(found)
            click_mouse(*found[0]+[ivxs,ivys],left=False)
            time.sleep(0.5)
            client = get_client()
            found = find_bitmap(store_all,client)
            if len(found):
                click_mouse(*found[0]+[10,10])
                time.sleep(1.0)
        else:
            break
        mainscreen = get_mainscreen()
    
tabs = {'settings':[681,484],'inventory':[645,187],'stats':[584,190]}
def open_tab(tab):
    if tab not in tabs:
        raise RuntimeException('Unknown tab %s'%tab)
    click_mouse(*tabs[tab])
    time.sleep(0.5)

run_already_on = np.asarray(Image.open('run_on.png'))[...,:3]
def run_on(restore_tab='inventory'):
    open_tab('settings')
    inventory = get_inventory()
    if len(find_bitmap(run_already_on,inventory,tol=0.02)) == 0:
        click_mouse(646,435)
        time.sleep(0.5)
    open_tab(restore_tab)
    

#Seer's Flax picker and spinner - UNFINISHED

bank_floor = [141,134,131]
party_room_gray = [165,156,152]
party_room_blue = [99,115,147]
mm_flax = [93,93,163]
mm_ladder = [82,33,0]


inv_flax = np.asarray(Image.open('flax.png'))
inv_bowstring = np.asarray(Image.open('bowstring.png'))


def pick_flax():
    print('trying to pick')
    return False

inventory = get_inventory()
nf = len(find_best_bitmap(inv_flax,inventory,tol=0.2))
nbs = len(find_best_bitmap(inv_bowstring,inventory,tol=0.2))
nrem = 28 - count_inv()

if nrem > 0:
    if nf > 0:
        state = 'picking'
    else:
        state = 'to_flax'
else:
    if nf > 0:
        if nbs > 0:
            state = 'spinning'
        else:
            state = 'to_spin'
    else:
        minimap = get_minimap()
        bank = find_best_bitmap(bank_icon,minimap,tol=0.05)
        spin = find_best_bitmap(spin_icon,minimap,tol=0.05)
        if len(spin) > 0:
            state = 'exit_house'
        else:
            state = 'to_bank'


a = find_colors(bank_floor,minimap,tol=(0.5,0.03,0.03),mode='hsl')
b = find_colors(party_room_gray,minimap,tol=(0.5,0.03,0.03),mode='hsl')
c = find_colors(party_room_blue,minimap,tol=(0.05,0.03,0.03),mode='hsl')
d = find_colors([238,0,0],minimap,tol=(0.05,0.03,0.03),mode='hsl')
e = find_colors(mm_ladder,minimap,tol=(0.05,0.03,0.03),mode='hsl')
spindoor = filter_near(d,e,10)
party = filter_near(b,c,5)
npc = find_colors([238,238,0],minimap,tol=(0.05,0.2,0.2),mode='hsl')
flax = find_colors(mm_flax,minimap,tol=(0.05,0.2,0.2),mode='hsl')
bank = a

if state == 'picking':
    pick_flax()
elif state == 'spinning':
    time.sleep(1.0)
elif state == 'to_flax':
    if len(flax) > 0:
        np.random.shuffle(flax)
        click_mouse(*(flax[0]+[mmxs,mmys]))
        flag_wait()
        pick_flax()
        continue
    if len(party) > 0:
        minx = np.min(party[:,0])
        click_mouse(*([minx-10,mmcy+40]))
        flag_wait()
elif state == 'to_bank':
    if len(bank) > 0:
        click_mouse(*(bank+[mmxs,mmys]))
        flag_wait()
        #open bank
        deposit_all()
    else:
        print('no bank!')
elif state == 'to_spin':
    if len(party) > 0:
        minx = np.min(party[:,0])
        click_mouse(*([minx-10,mmcy-40]))
        flag_wait()
    else:
        print('no party room!')

#Air rune crafter falador east

ess = np.asarray(Image.open('pure_essence.png'))[...,:3]
air_rune = np.asarray(Image.open('air_rune.png'))[...,:3]

mm_bank = [185,174,147]
mm_north_road = [132,125,105]
mm_south_road = [113,105,105]
mm_altar_dirt = [127,108,72]

use_tiara = True

target()
total_trips = 0
last_craft = time.monotonic()
logins = 0
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
    if time.monotonic()-last_craft > 10*60:
        raise RuntimeError('Took more than 10min to craft, something is wrong.')

    inv = count_inv()
    minimap = get_minimap()
    dirt = find_colors(mm_altar_dirt,minimap,mode='hsl',tol=(0.05,0.08,0.08))
    dirt = filter_radius(dirt,[mmxc-mmxs,mmyc-mmys],65)
    
    print('dirt',len(dirt))
    if len(dirt) > 2000: #at altar
        if inv == 28: #craft
            mainscreen = get_mainscreen()
            found = find_colors([64,64,64],mainscreen,tol=(0.5,0.1,0.1),mode='hsl')
            np.random.shuffle(found)
            for trial in range(15):
                move_mouse(*(found[-trial]+[msxs,msys]))
                uptext,mask = uptext_mask(get_uptext())
                txt = image_to_string(mask)
                print('tesseract say:',txt)
                if 'mu.' in txt or ' 1W' in txt or 'Curran' in txt or 'Cum.' in txt or 'Am.' in txt or 'am.' in txt or 'cmmuna' in txt:
                    click_mouse(*(found[-trial]+[msxs,msys]))
                    flag_wait()
                    last_craft = time.monotonic()
                    time.sleep(2.0)
                    break
        else: #return
            clusters,counts = cluster(dirt,radius=2)
            print('dirt clusters',counts)
            if np.count_nonzero(counts<1000):
                exit = np.concatenate(clusters[counts<1000])
                np.random.shuffle(exit)
                click_mouse(*(exit[0]+[mmxs,mmys]))
                flag_wait()                    
                mainscreen = get_mainscreen()
                portal = find_colors([215,212,174],mainscreen,tol=0.08,mode='hsl')
                if len(portal) > 0:
                    np.random.shuffle(portal)
                    click_mouse(*(portal[0]+[msxs,msys]))
                    flag_wait()
                    continue
                else:
                    print('no portal!')
    else: #banking or going to altar
        north = find_colors(mm_north_road,minimap,mode='hsl',tol=(0.05,0.08,0.08))
        north = filter_radius(north,[mmxc-mmxs,mmyc-mmys],65)
        south = find_colors(mm_south_road,minimap,mode='hsl',tol=(0.05,0.08,0.08))
        south = filter_radius(south,[mmxc-mmxs,mmyc-mmys],65)
        bank = find_colors(mm_bank,minimap,mode='hsl',tol=(0.05,0.2,0.08))
        bank = filter_radius(bank,[mmxc-mmxs,mmyc-mmys],65)
        print('north',len(north),'south',len(south),'bank',len(bank))
        npc = find_colors([238,238,0],minimap,mode='hsl',tol=0.15)
        clusters,counts = cluster(npc,radius=5)
        if len(bank) and len(counts) and np.max(counts) > 50:
            npc = clusters[np.argmax(counts)]
            bank = filter_near(npc,bank,5)
        else:
            bank = []

        if inv == 28: #go craft
            if len(south) > 0:
                walls = find_colors([238,238,238],minimap,tol=0.15)
                border = filter_near(south,walls,5)
                border = filter_far(border,[[mmxc-mmxs,mmyc-mmys]],10)
                print('border',len(border))
                if len(border) > 100:
                    mainscreen = get_mainscreen()
                    a = find_colors([74,72,70],mainscreen,tol=(0.07,0.1,0.1),mode='hsl')
                    b = find_colors([64,64,64],mainscreen,tol=(0.07,0.1,0.1),mode='hsl')
                    altar = filter_near(a,b,10)
                    clusters,counts = cluster(altar)
                    if len(counts) > 5 and np.max(counts) > 1000:
                        print('altar located')
                        click_mouse(mmxc,mmyc)
                        flag_wait()
                        mainscreen = get_mainscreen()
                        a = find_colors([74,72,70],mainscreen,tol=(0.07,0.1,0.1),mode='hsl')
                        b = find_colors([64,64,64],mainscreen,tol=(0.07,0.1,0.1),mode='hsl')
                        altar = filter_near(a,b,10)
                        clusters,counts = cluster(altar)
                        if use_tiara is False:
                            click_mouse(586,226)
                            time.sleep(0.05)
                        found = clusters[np.argmax(counts)]
                        np.random.shuffle(found)
                        click_mouse(*(found[0]+[msxs,msys]))
                        flag_wait()
                        time.sleep(1.0)
                        continue
                    walkto = border[np.argmin(border[:,0])]-[15,55]
                    vec = walkto-[mmxc-mmxs,mmyc-mmys]
                    veclen = np.sqrt(np.sum(np.square(vec)))
                    if veclen > 65:
                        walkto = [mmxc-mmxs,mmyc-mmys] + vec/veclen*65

                else:
                    walkto = south[np.argmax(south[:,1])]
            elif len(north) > 0:
                walkto = north[np.argmax(north[:,1]-north[:,0])]
            else:
                print('really lost...')
                continue
            print('heading south')
            click_mouse(*(walkto+[mmxs,mmys]))
            time.sleep(1.5)
        else: #go bank
            if len(bank) > 0:
                np.random.shuffle(bank)
                click_mouse(*(bank[0]+[mmxs,mmys-10]))
                flag_wait()
                time.sleep(2.0)
                mainscreen = get_mainscreen()
                a = find_colors([125,101,71],mainscreen,tol=0.02,mode='hsl')
                b = find_colors([143,116,82],mainscreen,tol=0.02,mode='hsl')
                points = filter_near(a,b,40)
                np.random.shuffle(points)
                if len(points) > 1:
                    minidx = np.argmin(np.sum(np.square(points-[msxc-msxs,msyc-msys]),axis=1))
                    points[-1],points[minidx] = points[minidx],points[-1]
                for point in points[-5:]:
                    click_mouse(*point,left=False)
                    time.sleep(0.05)
                    use = find_bitmap(use_booth,get_client())
                    if len(use) > 0:
                        click_mouse(*(use[0]+[10,10]))
                        flag_wait()
                        time.sleep(2.0)
                        while True:
                            inv = get_inventory()
                            found = find_best_bitmap(air_rune,inv,tol=0.05)
                            if len(found) > 0:
                                np.random.shuffle(found)
                                click_mouse(*(found[0]+[ivxs,ivys]),left=False)
                                time.sleep(0.5)
                                client = get_client()
                                found = find_bitmap(store_all,client)
                                if len(found):
                                    click_mouse(*found[0]+[10,10])
                                    time.sleep(1.0)
                            else:
                                break
                        mainscreen = get_mainscreen()
                        found = find_best_bitmap(ess,mainscreen,tol=0.05)
                        if len(found) > 0:
                            np.random.shuffle(found)
                            click_mouse(*(found[0]+[msxs,msys]),left=False)
                            time.sleep(1.0)
                            click_mouse(*(found[0]+[msxs,msys+87]))
                            time.sleep(1.0)
                            send_keys('28')
                            time.sleep(0.5)
                            send_keys('\n')
                            time.sleep(0.5)
                        else:
                            raise RuntimeError('out of materials!')
                        click_mouse(488,43)
                        if np.random.random() < 0.2:
                            polish_minimap()
                        clear_output()
                        total_trips += 1
                        print('completed %i inventories'%total_trips)
                        time.sleep(1.0)
                        run_on()
                        break
                    move_mouse(*(point+[0,-25]))
                continue
            if len(north) > 100:
                walkto = north[np.argmin(north[:,1]+0.5*north[:,0])]
            else:
                walkto = np.asarray([mmxc-mmxs+20,mmyc-mmys-40])#south[np.argmin(south[:,1]-south[:,0])]
            print('heading north')
            click_mouse(*(walkto+[mmxs,mmys]))
            time.sleep(1.5)
            
            

#Aubury essence miner varrock

mm_dirt_road = [140,132,95]
mm_bank_floor = [136,134,126]

travel_icon = np.asarray(Image.open('travel_icon.png'))[...,:3]
magic_icon = np.asarray(Image.open('magic_shop.png'))[...,:3]
teleport = np.asarray(Image.open('teleport.png'))[...,:3]

target()
total_trips = 0
last_mine = time.monotonic()
logins = 0
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
    if time.monotonic()-last_mine > 10*60:
        raise RuntimeError('Bailing out, wandered around for 10 minutes, definitely lost.')
        
    minimap = get_minimap()
    black = find_colors([0,0,0],minimap,tol=0.05)
    inv = count_inv()
    
    if len(black) > 1000: #in mine
        border = filter_far(black,[[mmxc-mmxs,mmyc-mmys]],40)
        if len(border) > 9000: #we're in a wing
            if inv == 28: #full, leave
                mainscreen = get_mainscreen()
                portal = find_colors([215,212,174],mainscreen,tol=0.08,mode='hsl')
                if len(portal) > 0:
                    np.random.shuffle(portal)
                    click_mouse(*(portal[0]+[msxs,msys]))
                    flag_wait()
                    continue
                else:
                    print('no portal!')
                    travel = find_best_bitmap(travel_icon,minimap,tol=0.05)
                    if len(travel) > 0:
                        np.random.shuffle(travel)
                        click_mouse(*(travel[0]+[mmxs,mmys]))
                        flag_wait()
            else: #mine
                flag_wait(init=0,post=0)
                did_something = False
                for trial in range(15):
                    x,y = np.random.randint(msxs,msxs+msw),np.random.randint(msys,msys+msh)
                    move_mouse(x,y)
                    uptext,mask = uptext_mask(get_uptext())
                    txt = image_to_string(mask)
                    print('tesseract say:',txt)
                    if 'Runa' in txt or '1.“' in txt:
                        did_something = True
                        click_mouse(x,y)
                        flag_wait()
                        i = 0
                        while True:
                            new_inv = count_inv()
                            if new_inv != inv:
                                i = 0
                                inv = new_inv
                            if inv == 28:
                                break
                            if i > 10:
                                break
                            i += 1
                            time.sleep(0.5)
                        break
                if did_something:
                    last_mine = time.monotonic()
                    continue
            
            print('trying new area...')
            area = find_colors([200,200,200],minimap,mode='hsl',tol=0.3)
            area = filter_radius(area,[mmxc-mmxs,mmyc-mmys],70)
            area = filter_far(area,black,20)
            if len(area) > 0:
                np.random.shuffle(area)
                click_mouse(*(area[0]+[mmxs,mmys]))
                flag_wait()
            else:
                print('hopelessly lost')
        else:
            print('moving to essence')
            area = find_colors([200,200,200],minimap,mode='hsl',tol=0.3)
            area = filter_radius(area,[mmxc-mmxs,mmyc-mmys],65)
            if len(area) > 0:
                point = area[np.argmin(-area[:,0]-area[:,1])]
                click_mouse(*(point+[mmxs,mmys]))
                time.sleep(3.0)
            else:
                print('hopelessly lost')
                    
    else: # in varrock
        road = find_colors(mm_dirt_road,minimap,tol=(0.05,0.07,0.05),mode='hsl')
        road = filter_radius(road,[mmxc-mmxs,mmyc-mmys],65)
        print('road',len(road))
        if inv == 28: #go bank
            bank_floor = find_colors(mm_bank_floor,minimap,mode='hsl',tol=(0.06,0.08,0.09))
            npcs = find_colors([238,238,0],minimap,mode='hsl',tol=0.1)
            clusters,counts = cluster(npcs,radius=4)
            print('bank_clusters',counts)
            if len(counts) > 0 and np.max(counts) > 59:
                bank_points = clusters[np.argmax(counts)]
                bank_points = filter_near(npcs,bank_points,4)
                print('bank',len(bank_points))
                if len(bank_points) > 5:
                    np.random.shuffle(bank_points)
                    click_mouse(*(bank_points[0]+[mmxs,mmys]))
                    flag_wait(imax=200)
                    mainscreen = get_mainscreen()
                    a = find_colors([96,83,45],mainscreen,mode='hsl',tol=0.1)
                    b = find_colors([52,43,65],mainscreen,mode='hsl',tol=0.1)
                    points = filter_near(a,b,40)
                    np.random.shuffle(points)
                    if len(points) > 1:
                        minidx = np.argmin(np.sum(np.square(points-[msxc-msxs,msyc-msys]),axis=1))
                        points[-1],points[minidx] = points[minidx],points[-1]
                    for point in points[-5:]:
                        click_mouse(*point,left=False)
                        time.sleep(0.05)
                        use = find_bitmap(use_booth,get_mainscreen())
                        if len(use) > 0:
                            click_mouse(*(use[0]+[10,10]))
                            flag_wait()
                            time.sleep(2.0)
                            deposit_all()
                            click_mouse(488,43)
                            time.sleep(1.0)
                            run_on()
                            if np.random.random() < 0.2:
                                polish_minimap()
                            break
                        move_mouse(*(point+[0,-25]))
                    continue
            print('heading north')
            walkto = road[np.argmin(road[:,1]-road[:,0])]
        else: #go aubury
            magic = find_best_bitmap(magic_icon,minimap,tol=0.11)
            if len(magic) > 0:
                np.random.shuffle(magic)
                click_mouse(*(magic[0]+[mmxs+5,mmys+5]))
                flag_wait()
                print('search for aubury')
                for i in range(20):
                    mainscreen = get_mainscreen()
                    a = find_colors([251,220,32],mainscreen,tol=0.18)
                    b = find_colors([240,240,240],mainscreen,tol=0.18)
                    aubury = filter_near(a,b,30)
                    if len(aubury) > 0:
                        np.random.shuffle(aubury)
                        move_mouse(*(aubury[0]+[msxs,msys]))
                        uptext = get_uptext()
                        yellow = find_colors([238,238,0],uptext,mode='hsl',tol=0.18)
                        if len(yellow) > 100:
                            click_mouse(*(aubury[0]+[msxs,msys]),left=False)
                            mainscreen = get_mainscreen()
                            clickme = find_bitmap(teleport,mainscreen)
                            if len(clickme) == 1:
                                click_mouse(*(clickme[0]+[msxs+15,msys+3]))
                                time.sleep(5.0)
                                break
                continue
            print('heading south')
            walkto = road[np.argmax(road[:,1]+0.35*road[:,0])]
        click_mouse(*(walkto+[mmxs,mmys]))
        time.sleep(1.0)

#Tree copper and shaft fletcher

logs = np.asarray(Image.open('oak_logs.png'))[:,:,:3]
knife = np.asarray(Image.open('knife.png'))[:,:,:3]

target()
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
            
    mainscreen = get_mainscreen()
    
    if count_inv() > 26: #fletch (or fire)
        print('time to fletch')
        inventory = get_inventory()
        k = find_best_bitmap(knife, inventory, tol=0.2)
        l = find_best_bitmap(logs, inventory, tol=0.2)
        print(len(l))
        if len(k) > 0 and len(l) > 0:
            np.random.shuffle(k)
            np.random.shuffle(l)
            click_mouse(*(k[0]+[ivxs,ivys]))
            time.sleep(1.0)
            click_mouse(*(l[0]+[ivxs,ivys]))
            time.sleep(1.0)
            click_mouse(76,405,left=False)
            time.sleep(1.0)
            click_mouse(55,477)
            time.sleep(1.0)
            send_keys('9999')
            time.sleep(1.0)
            send_keys('\n')
            i = 0
            last_len = len(l)
            while True:
                inventory = get_inventory()
                new_len = len(find_best_bitmap(logs, inventory, tol=0.2))
                if new_len == 0:
                    break
                if last_len != new_len:
                    last_len = new_len
                    i = 0
                i=i+1
                if i > 4:
                    print('timed out')
                    break
                time.sleep(0.5)
        else:
            print('missing knife or logs')

    a = find_colors([0,10,0],mainscreen,tol=0.05,mode='hsl')
    c = find_colors([150,170,100],mainscreen,tol=0.05,mode='hsl')
    trees = filter_near(a,c,20)
    found = False
    if len(trees) > 0:
        np.random.shuffle(trees)
        print('trying trees')
        for tree in trees[-10:]:
            move_mouse(*(tree+[msxs,msys]))
            time.sleep(0.1)
            uptext,mask = uptext_mask(get_uptext())
            txt = image_to_string(mask)
            print('tesseract say:',txt)
            if 'unTan' in txt or 'm. 1.' in txt or '1.22' in txt or 'm. I.' in txt or 'm 1.' in txt or 'dnunTma' in txt or 'dnunTva' in txt:
                print('chop it down!')
                click_mouse(*(tree+[msxs,msys]))
                found = True
                inv = count_inv()
                flag_wait()
                i = 0
                while inv == count_inv():
                    i += 1
                    if i > 10:
                        print('timed out')
                        break
                    time.sleep(0.5)
                else: #didn't timeout
                    break
    if found:        
        continue
    t = find_colors([55,79,25],minimap,mode='hsl',tol=0.05)
    if np.random.random() > 0.1:
        t = t[t[...,1]>mmyc-mmys]
    if len(t) > 0:
        np.random.shuffle(t)
        click_mouse(*(t[0]+[mmxs,mmys]))
        flag_wait()

#Chicken killer + bone burrier + feather grabber

bones_inv = np.asarray(Image.open('bones_inv.png'))
raw_chicken = np.asarray(Image.open('raw_chicken.png'))[...,:3]
drop_txt = np.asarray(Image.open('drop.png'))[...,:3]

target()
total_chickens = 0
logins = 0
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
            
    mainscreen = get_mainscreen()
    hp_r = find_colors([255,0,0],mainscreen,tol=0.01,mode='hsl') - [msxc-msxs,msyc-msys]
    hp_g = find_colors([0,255,0],mainscreen,tol=0.01,mode='hsl') - [msxc-msxs,msyc-msys]
    
    if len(filter_radius(np.concatenate([hp_r]),[0,0],100)) > 10: #in combat
        time.sleep(1.0)
        continue
        
    mainscreen = get_mainscreen()
    a = find_colors([185,149,147],mainscreen,tol=0.05,mode='hsl')
    c = find_colors([225,225,225],mainscreen,tol=0.1,mode='hsl')
    bones = filter_near(a,c,10)
    if len(bones) > 0:
        print('collecting white stuff...')
        for i in range(4):
            if i > 0:
                mainscreen = get_mainscreen()
                a = find_colors([185,149,147],mainscreen,tol=0.05,mode='hsl')
                c = find_colors([225,225,225],mainscreen,tol=0.1,mode='hsl')
                bones = filter_near(a,c,10)
            np.random.shuffle(bones)
            if len(bones) == 0:
                continue
            move_mouse(*(bones[0]+[msxs,msys]))
            time.sleep(0.2)
            uptext = get_uptext()
            orange = find_colors([230,140,60],uptext,mode='hsl',tol=0.2)
            print('bones:',len(orange))
            if len(orange) > 50:
                click_mouse(*(bones[0]+[msxs,msys]))
                flag_wait(init=1.0,post=0.5)
            
    if count_inv() > 25: #time to bury
        print('dropping chicken...')
        while True:
            inventory = get_inventory()
            drop = find_best_bitmap(raw_chicken,inventory,tol=0.2)
            if len(drop) > 0:
                np.random.shuffle(drop)
                click_mouse(*(drop[0]+[ivxs,ivys]),left=False)
                time.sleep(0.2)
                client = get_client()
                found = find_bitmap(drop_txt,client,tol=0.02)
                if len(found) > 0:
                    click_mouse(*(found[0]+[10,5]))
                else:
                    move_mouse(*(drop[0]+[ivxs,ivys-10]))
                time.sleep(0.5)
            else:
                break
        print('burying bones...')
        while True:
            inventory = get_inventory()
            bury = find_best_bitmap(bones_inv,inventory,tol=0.2)
            if len(bury) > 0:
                np.random.shuffle(bury)
                click_mouse(*(bury[0]+[ivxs,ivys]))
                time.sleep(0.1)
            else:
                break
                
    mainscreen = get_mainscreen()
    a = find_colors([135,27,14],mainscreen,tol=0.1,mode='hsl') #beak
    a,counts = cluster(a)
    valid = counts<20
    if np.count_nonzero(valid) == 0:
        print('no chickens!')
        time.sleep(0.5)
        continue
    a = np.concatenate(a[valid])
    b = np.concatenate([find_colors(c,mainscreen,tol=(0.05,0.05,0.05),mode='hsl') for c in [[118,91,55],[183,167,124]]])
    veto = find_colors([88,104,133],mainscreen,tol=0.1,mode='hsl') #water
    if len(a) == 0 or len(b) == 0:
        continue
    chickens = filter_near(b,a,20)
    if len(veto) > 0:
        chickens = filter_far(chickens,veto,10)
        
    if len(chickens) > 0:
        np.random.shuffle(chickens)
        #dist = np.sqrt(np.sum(np.square(cows-[msw/2,msh/2]),axis=1))
        #dist += 50*(2.0*np.random.random(dist.shape)-1.0)
        #sorter = np.argsort(dist)
        
        move_mouse(*(chickens[0]+[msxs,msys]))
        time.sleep(0.1)
        uptext = get_uptext()
        greentxt = find_colors([0,225,0],uptext,tol=0.05,mode='hsl')
        if len(greentxt) > 10:
            total_chickens += 1
            print('Attacking chicken %i'%total_chickens)
            click_mouse(*(chickens[0]+[msxs,msys]))
            flag_wait(init=1.0,post=1.0)
            continue

#Cow killer + bone burrier

bones_inv = np.asarray(Image.open('bones_inv.png'))

target()
total_cows = 0
logins = 0
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
            
    mainscreen = get_mainscreen()
    hp_r = find_colors([255,0,0],mainscreen,tol=0.01,mode='hsl') - [msxc-msxs,msyc-msys]
    hp_g = find_colors([0,255,0],mainscreen,tol=0.01,mode='hsl') - [msxc-msxs,msyc-msys]
    
    if len(filter_radius(np.concatenate([hp_r]),[0,0],100)) > 10: #in combat
        time.sleep(1.0)
        continue
        
    mainscreen = get_mainscreen()
    a = find_colors([158,33,17],mainscreen,tol=0.05,mode='hsl')
    c = find_colors([225,225,225],mainscreen,tol=0.1,mode='hsl')
    bones = filter_near(a,c,10)
    if len(bones) > 0:
        print('collecting bones...')
        np.random.shuffle(bones)
        move_mouse(*(bones[0]+[msxs,msys]))
        time.sleep(0.5)
        uptext = get_uptext()
        orange = find_colors([225,128,50],uptext,mode='hsl',tol=(0.03,0.2,0.1))
        print('bones:',len(orange))
        if len(orange) > 50:
            click_mouse(*(bones[0]+[msxs,msys]))
            flag_wait()
            
    if count_inv() > 25: #time to bury
        print('burying bones...')
        while True:
            inventory = get_inventory()
            bury = find_best_bitmap(bones_inv,inventory,tol=0.2)
            if len(bury) > 0:
                np.random.shuffle(bury)
                click_mouse(*(bury[0]+[ivxs,ivys]))
                time.sleep(1.0)
            else:
                break
    
    mainscreen = get_mainscreen()
    a = find_colors([88,70,59],mainscreen,tol=0.08,mode='hsl')
    b = find_colors([33,29,13],mainscreen,tol=0.08,mode='hsl')
    c = find_colors([200,200,200],mainscreen,tol=0.2,mode='hsl')
    a = filter_near(a,c,50)
    b = filter_near(b,c,50)
    if len(a) == 0 and len(b) == 0:
        continue
    elif len(a) == 0:
        cows = b
    elif len(b) == 0:
        cows = a
    else:
        cows = np.concatenate([a,b])
        
    if len(cows) > 0:
        cows = cows[cows[:,0]<msw-1]#filter off edge...
        np.random.shuffle(cows)
        #dist = np.sqrt(np.sum(np.square(cows-[msw/2,msh/2]),axis=1))
        #dist += 50*(2.0*np.random.random(dist.shape)-1.0)
        #sorter = np.argsort(dist)
        
        move_mouse(*(cows[0]+[msxs,msys]))
        time.sleep(0.1)
        uptext = get_uptext()
        greentxt = find_colors([0,225,0],uptext,tol=0.05,mode='hsl')
        if len(greentxt) > 10:
            total_cows += 1
            print('Attacking cow %i'%total_cows)
            click_mouse(*(cows[0]+[msxs,msys]))
            time.sleep(5.0)
            continue

#Smither for varock west anvils

mm_floor = [94,87,54]
mm_ew_road = [124,122,115]
mm_s_road = [131,123,89]

final = np.asarray(Image.open('iron_plate.png'))
raw_req = 5

#final = np.asarray(Image.open('iron_arrowheads.png'))[...,:3]
#raw_req = 1

#final = np.asarray(Image.open('iron_bolts.png'))[...,:3]
#raw_req = 1

raw = np.asarray(Image.open('iron_bar.png'))
bmp_tol = 0.3

target()
total_trips = 0
logins = 0
last_smith = time.monotonic()
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
    if time.monotonic() - last_smith > 10*60:
        raise RuntimeError('Sorry folks, got lost somehow and now we\'re done.')
    minimap = get_minimap()
    masked = np.full_like(minimap,0)
    masked[minimap_mask] = minimap[minimap_mask]
    minimap = masked
    inv_full = count_inv() == 28
    a = find_colors(mm_ew_road,minimap,tol=(0.02,0.03,0.03),mode='hsl') #mm_ew_road
    b = find_colors(mm_s_road,minimap,tol=(0.02,0.03,0.03),mode='hsl') #mm_s_road
    c = find_colors(mm_floor,minimap,tol=(0.02,0.03,0.03),mode='hsl') #mm_floor

    anvil_bldg = filter_near(filter_near(c,a,10),b,10)
    bankers = filter_far(filter_near(find_colors([255,255,0],minimap,tol=0.05,mode='hsl'),c,2),b,30)
    
    inventory = get_inventory()
    raw_points = find_best_bitmap(raw,inventory,tol=bmp_tol)
    
    if inv_full or len(raw_points) > 1.5*raw_req: #go smith
        if len(anvil_bldg) == 0:
            print('can\'t find anvil building!')
            continue
        np.random.shuffle(anvil_bldg)
        click_mouse(*(anvil_bldg[0]+[mmxs+5,mmys+5]))
        flag_wait()
        if len(raw_points):
            np.random.shuffle(raw_points)
            click_mouse(*(raw_points[0]+[ivxs,ivys]))
            mainscreen = get_mainscreen()
            a = find_colors([50,50,50],mainscreen,tol=0.05,mode='hsl')
            b = find_colors([100,100,100],mainscreen,tol=0.05,mode='hsl')
            points = filter_near(b,a,10)
            np.random.shuffle(points)
            for point in points[-5:]:
                move_mouse(*(point+[msxs,msys]))
                time.sleep(0.5)
                uptext,mask = uptext_mask(get_uptext())
                txt = image_to_string(mask)
                print(txt)
                if 'ﬂmnl' in txt or 'nml' in txt or 'nwl' in txt or 'nyml' in txt:
                    click_mouse(*(point+[msxs,msys]))
                    flag_wait()
                    mainscreen = get_mainscreen()
                    smith_pos = find_best_bitmap(final,mainscreen,tol=0.27)
                    if len(smith_pos) ==0:
                        break
                    np.random.shuffle(smith_pos)
                    click_mouse(*(smith_pos[0]+[msxs,msys]),left=False)
                    time.sleep(2.0)
                    print('make 10')
                    click_mouse(*(smith_pos[0]+[msxs,msys+58]))
                    last_smith = time.monotonic()
                    polish_minimap(click=False)
                    raw_num = len(raw_points)
                    i = 0
                    while True:
                        i = i+1
                        inventory = get_inventory()
                        new_raw_num = len(find_best_bitmap(raw,inventory,tol=bmp_tol))
                        print('remaining:',new_raw_num)
                        if new_raw_num != raw_num:
                            raw_num = new_raw_num
                            i = 0
                        if i > 5:
                            break
                        if new_raw_num < raw_req:
                            break
                        time.sleep(0.5)
                    break
        else:
            print('no raw material found!')
    else: #go bank
        #open bank    
        mainscreen = get_mainscreen()
        if len(find_bitmap(bank_window,mainscreen,tol=0.02)) == 0:
            print('going to bank')
            if len(bankers) == 0:
                continue
            np.random.shuffle(bankers)
            click_mouse(*(bankers[0]+[mmxs,mmys]))
            flag_wait()
            
            mainscreen = get_mainscreen()
            a = find_colors([60,60,60],mainscreen,tol=0.05,mode='hsl')
            b = find_colors([55,45,87],mainscreen,tol=0.05,mode='hsl')
            points = filter_near(a,b,50) 
            print(len(a),len(b),len(points))
            np.random.shuffle(points)
            for point in points[-5:]:
                click_mouse(*point,left=False)
                time.sleep(0.5)
                use = find_bitmap(use_booth,get_mainscreen())
                if len(use) > 0:
                    click_mouse(*(use[0]+[10,10]))
                    time.sleep(1.0)
                    flag_wait()
                    print('bank opened')
                    time.sleep(1.0)
                    break
                move_mouse(*(point+[0,-25]))
            continue
        else:
            inventory = get_inventory()
            final_points = find_best_bitmap(final,inventory,tol=bmp_tol)
            if len(final_points):
                print('depositing product')
                np.random.shuffle(final_points)
                click_mouse(*final_points[0]+[ivxs,ivys],left=False)
                time.sleep(0.5)
                client = get_client()
                found = find_bitmap(store_all,client)
                if len(found):
                    click_mouse(*found[0]+[10,10])
                    time.sleep(1.0)
                    continue
            mainscreen = get_mainscreen()        
            raw_points = find_best_bitmap(raw,mainscreen,tol=bmp_tol)
            if len(raw_points):
                print('withdrawing raw')
                np.random.shuffle(raw_points)
                click_mouse(*(raw_points[0]+[msxs,msys]),left=False)
                time.sleep(1.0)
                click_mouse(*(raw_points[0]+[msxs,msys]+[0,87]))
                time.sleep(1.0)
                send_keys('28\n')
                time.sleep(1.0)

west_of_wall()

#Mining script requires agility shortcut Falador west

#rocks = [(1,copper_color,0.025,[223,129,59]),(1,tin_color,0.025,[139,130,129])] #copper&tin
rocks = [(1,iron_color,0.015,[78,48,36])] #iron
mm_rocks = [159,103,59]#[127,77,42]

mm_rock_tol = (0.07,0.08,0.06)
mm_east_tol = (0.07,0.08,0.08)
mm_west_tol = (0.07,0.1,0.08)

mine_icon = np.asarray(Image.open('mine_icon.png'))[...,:3]
agility_icon = np.asarray(Image.open('agility_icon.png'))[...,:3]

def mine(rocks=rocks):
    '''mines the next rock based on weights in rocks structure
       finds rock based on color of ore plus proximity to generic rock color
       confirms uptext hovering over rock before mining
       waits for rock to appear in inventory before proceeding'''
    counts = count_rocks(rocks=rocks)
    print('Weighted totals:',counts)
    minidx = np.argmin(counts)
    weight,color,tol,bmp = rocks[minidx]
    mainscreen = get_mainscreen()
    found = find_colors(color,mainscreen,tol=tol,mode='hsl')
    b = find_colors(np.asarray([107,88,28]),mainscreen,tol=0.02)
    found = filter_near(found,b,10)
    if len(found) == 0:
        return False
    point = closest([msw/2,msh/2-20],found)
    move_mouse(*(point+[msxs,msys]))
    time.sleep(0.2)
    uptext,mask = uptext_mask(get_uptext(width=80))
    txt = image_to_string(mask)
    if 'Ru(k' in txt:
        click_mouse(*(point+[msxs,msys]))
    else:
        return False
    for i in range(100):
        time.sleep(0.05)
        if np.any(count_rocks(rocks=rocks) != counts):
            time.sleep(0.2)
            return True
    return False

def west_of_wall():
    '''returns true if character is closer to west road or mine colors than east road or mine colors'''
    minimap = get_minimap()
    if len(find_best_bitmap(mine_icon,minimap,0.05)) > 0:
        print('at mine')
        return True
    west = find_colors(west_road,minimap,tol=mm_west_tol,mode='hsl')
    clusters,counts = cluster(west,radius=2)
    if len(counts) > 0 and np.max(counts) > 100:
        west = np.concatenate(clusters[counts > 25])
    else:
        west = []
    npc_points = find_colors([255,255,0],minimap,tol=0.05,mode='hsl')
    bank_points = np.concatenate([find_colors(bank_floor,minimap,tol=0.085,mode='hsl') for bank_floor in bank_floor_colors])
    clusters,counts = cluster(bank_points)
    if len(counts) < 1 or np.count_nonzero(counts>20) < 1:
        bank_points = np.asarray([])
    else:
        bank_points = clusters[np.random.choice(np.nonzero(counts>20)[0])]
    bank_points = filter_near(bank_points,npc_points,6)
    if len(bank_points) < 10:
        rocks = find_colors(mm_rocks,minimap,tol=mm_rock_tol,mode='hsl')
        if len(west) > 0:
            west = np.concatenate([rocks,west])
        else:
            west = rocks
    east = find_colors(east_road,minimap,tol=mm_east_tol,mode='hsl')
    clusters,counts = cluster(east,radius=2)
    if len(counts) > 0 and np.max(counts) > 100:
        east = np.concatenate(clusters[counts > 10])
    else:
        east = []
    print('Locating... E:',len(east),'W:',len(west),'B',len(bank_points))
    west_best = 9001 if len(west) == 0 else np.min(np.sum(np.square(west-[mmxc-mmxs,mmyc-mmys]),axis=-1))
    east_best = 9001 if len(east) == 0 else np.min(np.sum(np.square(east-[mmxc-mmxs,mmyc-mmys]),axis=-1))
    if west_best <= east_best:
        print('west of wall')
        return True
    else:
        print('east of wall')
        return False
            
            
def jump_wall():
    '''The Donald can't stop us!
       tries to get as close as possible to boundary between east and west road colors on minimap
       looks for proximity of wall color, east, and west road colors on mainscreen
       attempts to confirm uptext hovering over possible wall locations
       returns true if successfully jumped'''
    minimap = get_minimap()
    east = find_colors(east_road,minimap,tol=mm_east_tol,mode='hsl')
    west = find_colors(west_road,minimap,tol=mm_west_tol,mode='hsl')
    print('Road points... E:',len(east),'W:',len(west))
    if len(west) == 0 or len(east) == 0:
        return False
    border = filter_near(east,west,3)
    print('Boundary:',len(border))
    if len(border) <= 3: #try the agility icon
        agility = find_best_bitmap(agility_icon,minimap,tol=0.05)
    else:
        agility = None
    np.random.shuffle(border)
    if len(border) > 3 or len(agility) > 0:
        border = border[0] if len(border) > 3 else (agility[np.random.randint(len(agility))]+[5,5])
        click_mouse(*(border+[mmxs,mmys]))
        flag_wait()
        mainscreen = get_mainscreen()
        wall_points = find_colors(wall_color,mainscreen,tol=0.07,mode='hsl')
        inner_wall_points = find_colors(inner_wall_color,mainscreen,tol=0.07,mode='hsl')
        outer_wall_points = find_colors([73,64,41],mainscreen,tol=0.07,mode='hsl')
        wall_points = filter_near(filter_near(wall_points,inner_wall_points,10),outer_wall_points,10)
        np.random.shuffle(wall_points)
        for point in wall_points[-5:]:
            move_mouse(*(point+[msxs,msys]))
            time.sleep(0.2)
            uptext,mask = uptext_mask(get_uptext(width=80))
            txt = image_to_string(mask)
            print(txt)
            if 'Clumb' in txt or 'timb' in txt:
                click_mouse(*(point+[msxs,msys]))
                time.sleep(5.0)
                return True
    return False

target()
miss = 0
total_trips = 0
last_mine = time.monotonic()
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        login()
        continue
    if time.monotonic()-last_mine > 10*60:
        raise RuntimeError('Haven\'t mined in 10 minutes, giving up because something ain\'t right.')
    inv_full = count_inv() == 28
    print('Total items:',count_inv())
    if inv_full:
        if west_of_wall():
            if not jump_wall():
                minimap = get_minimap()
                west = filter_radius(find_colors(west_road,minimap,tol=mm_west_tol,mode='hsl'),[mmxc-mmxs,mmyc-mmys],70)
                print('Moving east:',len(west))
                if len(west):
                    click_mouse(*(west[np.argsort(west[:,0])[-1]]+(mmxs,mmys)))
                    time.sleep(2.0)
            else:
                print('Crossed wall west->east')
        else: 
            if open_bank():
                deposit_all()
                total_trips = total_trips + 1
                clear_output()
                if np.random.random() < 0.5:
                    polish_minimap(min_same=35,horizontal=False)
                print('Completed %i inventories'%total_trips)
                continue
    else:
        if west_of_wall():
            if not mine(rocks):
                print('No rock found!')
                miss = miss + 1
                if miss < 5:
                    time.sleep(0.5)
                    continue
                print('Trying new position...')
                minimap = get_minimap()
                mine_loc = find_colors(mm_rocks,minimap,tol=mm_rock_tol,mode='hsl')
                mine_loc = filter_radius(mine_loc,[mmxc-mmxs,mmyc-mmys],50)
                if len(mine_loc):
                    np.random.shuffle(mine_loc)
                    click_mouse(*(mine_loc[-1]+(mmxs,mmys)))
                    flag_wait()
                    continue
                west = find_colors(west_road,minimap,tol=mm_west_tol,mode='hsl')
                west = filter_radius(west,[mmxc-mmxs,mmyc-mmys],70)
                print('Moving west:',len(west))
                if len(west):
                    click_mouse(*(west[np.argsort(west[:,0])[0]]+(mmxs,mmys)))
                    time.sleep(2.0)
                else:
                    print('Got lost going to mine!')
            else:
                last_mine = time.monotonic()
                miss = 0
        else: 
            if not jump_wall():
                minimap = get_minimap()
                east = filter_radius(find_colors(east_road,minimap,tol=mm_east_tol,mode='hsl'),[mmxc-mmxs,mmyc-mmys],70)
                print('Moving west:',len(east))
                if len(east):
                    click_mouse(*(east[np.argsort(east[:,0]-east[:,1])[0]]+(mmxs,mmys)))
                    time.sleep(2.0)
                else:
                    print('Got lost going to wall!')
            else:
                miss = 9999 #to move west immediately
                run_on()
                print('Crossed wall east->west')

#Gold miner for Rimmington (falador shortcut south)

rimm_rock_color = [141,96,17]

mm_rock = [105,90,98]
mm_mine_colors = [[135,109,13]]

falador_wall = [189,175,152]
agility_color = [18,155,62]
tunnel_color = [60,9,0]
rimm_road = [117,109,108]

road_tol = 0.10


def to_mine(rr,minmap):
    mainscreen = get_mainscreen()
    i = find_colors(iron_color,mainscreen,mode='hsl',tol=0.05)
    g = find_colors(gold_color,mainscreen,mode='hsl',tol=0.07)
    r = find_colors(rimm_rock_color,mainscreen,mode='hsl',tol=0.05)
    i = filter_near(i,r,5)
    g = filter_near(g,r,5)
    found = g if len(g) else i
    if len(found) and (len(g) > 0 or np.random.random() < 0.75): #occasionally move to find gold
        point = closest([msw/2,msh/2-20],found)
        move_mouse(*(point+[msxs,msys]))
        time.sleep(0.2)
        uptext,mask = uptext_mask(get_uptext(width=80))
        txt = image_to_string(mask)
        if 'Ru(k' in txt:
            inv = count_inv()
            click_mouse(*(point+[msxs,msys]))
            for i in range(100 if len(g) == 0 else 1000):
                time.sleep(0.05)
                if np.any(count_inv() != inv):
                    time.sleep(1.0)
                    return True
    minimap = get_minimap()
    a = find_colors(mm_rock,minimap,tol=0.04,mode='hsl')
    c = np.concatenate([find_colors(mm_mine,minimap,tol=0.1,mode='hsl') for mm_mine in mm_mine_colors])
    locations = filter_near(a,c,10)
    print('rocks:',len(a),'mine:',len(c),'loc:',len(locations))
    locations = filter_far(locations,[mmxc-mmxs,mmyc-mmys],15)
    if len(locations) > 2:
        np.random.shuffle(locations)
        click_mouse(*(locations[0]+[mmxs,mmys]))
        flag_wait()
    else:
        order = np.argsort(-2*rr[:,1]-rr[:,0]) #sort by -2*y-x (sse-most)
        walkto = rr[order[0]]
        click_mouse(*(walkto+[mmxc,mmyc]))
        flag_wait()

target()
total_trips = 0
logins = 0
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        logins = logins + 1
        if logins > 10:
            raise RuntimeError('Too many logins! Bailing out before we get fishy!')
        login()
        continue
    minimap = get_minimap()
    masked = np.full_like(minimap,0)
    masked[minimap_mask] = minimap[minimap_mask]
    minimap = masked
    inv_full = count_inv() == 28
    rr = find_colors(rimm_road,minimap,tol=road_tol,mode='hsl') - [mmxc-mmxs,mmyc-mmys]
    fw = find_colors(falador_wall,minimap,tol=0.15,mode='hsl') - [mmxc-mmxs,mmyc-mmys]
    bank = np.concatenate([ind_colors(bank_floor,minimap,tol=0.08,mode='hsl') for bank_floor in bank_floor_colors])
    if len(bank) < 20:
        agility = find_colors(agility_color,minimap,tol=0.1,mode='hsl') - [mmxc-mmxs,mmyc-mmys]
    else:
        agility = []
    print('Locating...','R:',len(rr),'F:',len(fw),'B:',len(bank),'A:',len(agility))
    if len(fw) > 250: # inside falador either traveling or banking
        north_of_wall = None
        if len(agility) > 5 and len(filter_radius(agility,[0,0],30)) > 5: #close to hole
            near_wall = filter_radius(fw,[0,0],15)
            print('near wall',len(near_wall))
            if len(near_wall) > 5:
                north_of_wall = np.mean(near_wall[:,1]) > 0 #mean of y position of wall within 30 px of character
        if north_of_wall is None:
            sw_wall_count = np.count_nonzero(np.logical_and(fw[:,0] < 0,fw[:,1] > 0))
            print('sw wall',sw_wall_count)
            north_of_wall = sw_wall_count > 15 #more than 20 wall px in s or w 
        print('north' if north_of_wall else 'south','of wall')
        if len(agility) > 5 and (north_of_wall ^ inv_full): #if we haven't gone under wall yet
            order = np.argsort(-2*fw[:,1]+fw[:,0]) #sort by -2*y+x (ssw-most)
            walkto = fw[order[0]]+[20,0]
            click_mouse(*(walkto+[mmxc,mmyc]))
            flag_wait()
            mainscreen = get_mainscreen()
            tunnel = find_colors(tunnel_color,mainscreen,mode='hsl',tol=0.08)
            if len(tunnel)>20:
                np.random.shuffle(tunnel)
                click = tunnel[0]
                if north_of_wall:
                    click = tunnel[0]-[0,75]
                click_mouse(*(click+[msxs,msys]))
                time.sleep(10.0)
                if north_of_wall:
                    run_on()
                continue
        if inv_full: #definitely going north
            if open_bank(): #try to go to and open bank
                deposit_all()
                total_trips = total_trips + 1
                print('Completed %i inventories'%total_trips)
                continue    
            npc_points = find_colors([255,255,0],minimap,tol=0.05,mode='hsl')
            bank_points = filter_near(npc_points,bank,6)
            if len(bank_points) < 100:
                if north_of_wall: #otherwise if inside falador go north
                    order = np.argsort(2*fw[:,1]+fw[:,0]) #sort by -2*y+x (nnw-most)
                    walkto = fw[order[0]]+[20,0]
                    click_mouse(*(walkto+[mmxc,mmyc]))
                    flag_wait()
                else: #gotta get to hole
                    order = np.argsort(-2*fw[:,1]+fw[:,0]) #sort by -2*y+x (ssw-most)
                    walkto = fw[order[0]]+[20,0]
                    click_mouse(*(walkto+[mmxc,mmyc]))
                    flag_wait()
            else:
                print('must have missed bank...')
        elif north_of_wall: # inside falador, north of wall, and inv empty: go south
            order = np.argsort(-2*fw[:,1]+fw[:,0]) #sort by -2*y+x (ssw-most)
            walkto = fw[order[0]]+[20,0]
            click_mouse(*(walkto+[mmxc,mmyc]))
            flag_wait()
        else: #gotta get to mine
            to_mine(rr,minimap)
    elif inv_full: # full inventory travelin to bank
        if len(agility) > 5:
            np.random.shuffle(agility)
            walkto = agility[0]
        elif len(rr) > 0:
            order = np.argsort(4*rr[:,1]+rr[:,0]) #sort by 2*y+x (nnw-most)
            walkto = rr[order[0]]
        else:
            walkto = np.asarray([-20,-40])
        click_mouse(*(walkto+[mmxc,mmyc]))
        flag_wait()
    else: #mining or traveling to mine
        to_mine(rr,minimap)
    

#Smelting script banks Falador west and uses Falador furnace

#for gold
#bar = np.asarray(Image.open('gold_bar.png'))[:,:,:3]
#ore = np.asarray(Image.open('gold_ore.png'))[:,:,:3]
#inputs = [(1,ore)]
#bar_pos = np.asarray([310,405])

#for iron
bar = np.asarray(Image.open('iron_bar.png'))[:,:,:3]
ore = np.asarray(Image.open('iron_ore.png'))[:,:,:3]
inputs = [(1,ore)]
bar_pos = np.asarray([160,405])

#for bronze - update to bitmaps
#rocks = [(1,[94,80],0.025,[223,129,59]),(1,[143,80],0.025,[139,130,129])] #num_per_bar,bank_coords,tolerance,item_color
#bar_pos = np.asarray([50,405]) #position of bar on furnace menu 

def count_inputs():
    inventory = get_inventory()
    return np.asarray([len(find_best_bitmap(bmp,inventory,tol=0.02))//unit for unit,bmp in inputs])
        
furnace_icon = np.asarray(Image.open('furnace_icon.png'))[:,:,:3]
def go_smelt():
    '''finds furnace icon on minimap and walks to it, then locates furnace by proximity of metal and fire colors
       if found, starts smelting and waits until out of rocks or timed out'''
    minimap = get_minimap()
    icon = find_best_bitmap(furnace_icon,minimap,tol=0.04)#find_colors(np.asarray([255,115,41]),minimap,tol=0.05,mode='hsl')
    icon = filter_radius(icon,[mmxc-mmxs,mmyc-mmys],70) 
    np.random.shuffle(icon)
    print('Furnace icon points:',len(icon))
    if len(icon) == 1:
        click_mouse(*(icon[0]+(mmxs+4,mmys)))
        flag_wait()    
        mainscreen = get_mainscreen()
        fire = find_colors([192,79,48],mainscreen,mode='hsl',tol=0.04)
        furnace = find_colors([192,79,48],mainscreen,mode='hsl',tol=0.04)
        furnace = filter_near(furnace,fire,10)
        np.random.shuffle(furnace)
        if len(furnace) > 0:
            print('Found furnace, starting smelting...')
            click_mouse(*(furnace[-1]+[msxs+20,msys]))
            time.sleep(5.0)
            click_mouse(*bar_pos,left=False)
            time.sleep(1.0)
            click_mouse(*(bar_pos+[0,70]))
            time.sleep(1.0)
            send_keys('99\n')
            time.sleep(1.0)
            inv = count_inputs()
            polish_minimap(min_same=35,horizontal=False,click=False)
            i = 0
            while True:
                time.sleep(0.5)
                i = i+1
                cur_inv = count_inputs()
                if np.any(cur_inv != inv):
                    inv = cur_inv
                    i = 0
                if np.sum(cur_inv) == 0:
                    print('Success, getting more materials!')
                    run_on()
                    return True
                if i > 10:
                    print('Timed out, trying again')
                    return True
        return True # didn't smelt but don't run away...
    return False
    

target()
done = False
total_trips = 0
last_smelt = time.monotonic()
while True:
    client = get_client()
    if len(find_bitmap(loginscreen,client)) > 0:
        login()
        continue
    if time.monotonic() - last_smelt > 10*60:
        raise RuntimeError('Been a loooong time since a smelt. Probably horribly lost. Maybe.')
        
    inv = count_inputs()
    if np.all(inv != 0): #ready to smelt
        done = False
        if go_smelt():
            last_smelt = time.monotonic()
        else:
            minimap = get_minimap()
            east = filter_radius(find_colors(east_road,minimap,tol=0.08),[mmxc-mmxs,mmyc-mmys],70)
            print('Moving east:',len(east))
            if len(east):
                click_mouse(*(east[np.argsort(-east[:,0]+np.abs(east[:,1]-mmxc+mmxs)*0.1)[0]]+(mmxs,mmys)))
                time.sleep(1.5)
            else:
                print('Lost looking for furnace!')
    else: #go to bank
        if done:
            break
        if open_bank():
            deposit_all()
            clear_output()
            total_trips = total_trips + 1
            print('Completed %i invetories'%total_trips)
            done = True
            time.sleep(0.5)
            mainscreen = get_mainscreen()
            batch = np.sum([unit for unit,_ in inputs])
            for unit,bmp in inputs:
                coords = find_best_bitmap(bmp,mainscreen,tol=0.2)
                print('raw found:',len(coords))
                np.random.shuffle(coords)
                if len(coords) > 0:
                    click_mouse(*(coords[0]+[msxs,msys]),left=False)
                    time.sleep(1.0)
                    click_mouse(*(coords[0]+[msxs,msys]+[0,87]))
                    time.sleep(1.0)
                    send_keys('%i\n'%(unit*(28//batch)))
                    time.sleep(1.0)
                else:
                    print('Out of supplies!')
        else:                
            minimap = get_minimap()
            east = filter_radius(find_colors(east_road,minimap,tol=0.08,mode='hsl'),[mmxc-mmxs,mmyc-mmys],70)
            print('Moving west:',len(east))
            if len(east):
                click_mouse(*(east[np.argsort(east[:,0]+np.abs(east[:,1]-mmxc+mmxs)*0.1)[0]]+(mmxs,mmys)))
                time.sleep(1.5)
            else:
                print('Lost looking for bank!')

# Echos coords and colors under mouse
try:
    while True:
        time.sleep(1)
        target()
        x,y = pyautogui.position()
        print('%i,%i [%i,%i,%i]'%(x-x0,y-y0,*np.asarray(pyautogui.screenshot(region=[x,y,1,1]))[0,0]))
except KeyboardInterrupt:
    pass

while True: #buy feathers
    click_mouse(380,79,left=False)
    time.sleep(0.2)
    click_mouse(386,154)
    time.sleep(0.1)

while True: #make arrows
    click_mouse(580,228) #inv1
    time.sleep(0.5)
    click_mouse(625,236) #inv2
    time.sleep(0.5)
    click_mouse(250,420,left=False)
    time.sleep(0.5)
    click_mouse(237,480)
    time.sleep(10.0)

while True: #make bolts
    click_mouse(580,228) #inv1
    time.sleep(0.2)
    click_mouse(625,236) #inv2
    time.sleep(0.1)

target() #buy runes
topleft = np.asarray([95,85])
offset = np.asarray([144-95,0])
idx = np.asarray([0,0]) #rune to buy
for i in range(100):
    click_mouse(*(topleft+offset*idx),left=False)
    time.sleep(0.1)
    click_mouse(*((topleft+offset*idx)+[0,154-79]))
    time.sleep(0.05)



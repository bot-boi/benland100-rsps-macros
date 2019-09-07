

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












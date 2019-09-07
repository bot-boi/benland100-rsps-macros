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

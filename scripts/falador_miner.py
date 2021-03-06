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

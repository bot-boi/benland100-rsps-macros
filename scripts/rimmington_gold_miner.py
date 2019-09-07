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
    

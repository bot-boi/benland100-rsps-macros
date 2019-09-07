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

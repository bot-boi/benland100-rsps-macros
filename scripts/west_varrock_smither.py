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

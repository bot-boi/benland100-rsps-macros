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
 

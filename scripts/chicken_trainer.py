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

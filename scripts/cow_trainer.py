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

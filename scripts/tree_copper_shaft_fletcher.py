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

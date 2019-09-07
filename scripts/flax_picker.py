#Seer's Flax picker and spinner - UNFINISHED

bank_floor = [141,134,131]
party_room_gray = [165,156,152]
party_room_blue = [99,115,147]
mm_flax = [93,93,163]
mm_ladder = [82,33,0]


inv_flax = np.asarray(Image.open('flax.png'))
inv_bowstring = np.asarray(Image.open('bowstring.png'))


def pick_flax():
    print('trying to pick')
    return False

inventory = get_inventory()
nf = len(find_best_bitmap(inv_flax,inventory,tol=0.2))
nbs = len(find_best_bitmap(inv_bowstring,inventory,tol=0.2))
nrem = 28 - count_inv()

if nrem > 0:
    if nf > 0:
        state = 'picking'
    else:
        state = 'to_flax'
else:
    if nf > 0:
        if nbs > 0:
            state = 'spinning'
        else:
            state = 'to_spin'
    else:
        minimap = get_minimap()
        bank = find_best_bitmap(bank_icon,minimap,tol=0.05)
        spin = find_best_bitmap(spin_icon,minimap,tol=0.05)
        if len(spin) > 0:
            state = 'exit_house'
        else:
            state = 'to_bank'


a = find_colors(bank_floor,minimap,tol=(0.5,0.03,0.03),mode='hsl')
b = find_colors(party_room_gray,minimap,tol=(0.5,0.03,0.03),mode='hsl')
c = find_colors(party_room_blue,minimap,tol=(0.05,0.03,0.03),mode='hsl')
d = find_colors([238,0,0],minimap,tol=(0.05,0.03,0.03),mode='hsl')
e = find_colors(mm_ladder,minimap,tol=(0.05,0.03,0.03),mode='hsl')
spindoor = filter_near(d,e,10)
party = filter_near(b,c,5)
npc = find_colors([238,238,0],minimap,tol=(0.05,0.2,0.2),mode='hsl')
flax = find_colors(mm_flax,minimap,tol=(0.05,0.2,0.2),mode='hsl')
bank = a

if state == 'picking':
    pick_flax()
elif state == 'spinning':
    time.sleep(1.0)
elif state == 'to_flax':
    if len(flax) > 0:
        np.random.shuffle(flax)
        click_mouse(*(flax[0]+[mmxs,mmys]))
        flag_wait()
        pick_flax()
        continue
    if len(party) > 0:
        minx = np.min(party[:,0])
        click_mouse(*([minx-10,mmcy+40]))
        flag_wait()
elif state == 'to_bank':
    if len(bank) > 0:
        click_mouse(*(bank+[mmxs,mmys]))
        flag_wait()
        #open bank
        deposit_all()
    else:
        print('no bank!')
elif state == 'to_spin':
    if len(party) > 0:
        minx = np.min(party[:,0])
        click_mouse(*([minx-10,mmcy-40]))
        flag_wait()
    else:
        print('no party room!')

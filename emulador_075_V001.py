#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 18 14:56:11 2021
Ferranti Mercury Emulator (~1958)

@author: Julian Alejandro Lell
All Rights Reserved
"""
#%% Modules instance
import matplotlib.pyplot as plt
import numpy as np
import time
#from pynput.keyboard import Key, Listener

#%% Creation of virtual storage

#This is the virtual "magnetic core memory" a.k.a "computing store".
computing_store_pages = 32
computing_store_wpp = 64
computing_store_size = computing_store_pages*computing_store_wpp

computing_store = np.zeros(computing_store_size, dtype='i')
computing_store_paged = np.zeros((computing_store_pages,computing_store_wpp),dtype='i') #32 pages, 64 words each

#This is the virtual "magnetic drum memory" a.k.a. "backing store".
backing_store_sectors = 1024 # 4 drums in Clementina
backing_store_wps = 64
backing_store_size = backing_store_sectors*backing_store_wps

backing_store = np.zeros(backing_store_size, dtype='i')
backing_store_sectorized = np.zeros((backing_store_sectors,backing_store_wps),dtype='i') #512 sectors, 

#This is the "B-register"
B_register = np.zeros(8, dtype='i')

accumulator_LSB = np.int(0)
accumulator_MSB = np.int(0)

#accumulator_exponent = np.int(0)
#accumulator_mantissa = np.float64(0)
#accumulator_real = np.float(0)

verbose = False
sector_selected = 0

shutter = False #False = Closed

display = np.zeros(2, dtype='i')

TC = np.zeros(3, dtype='i') # TC[0] is not used

#Magnetic tape flags and registers
decks_available = 2
blocks_in_decks = 4860 # This number must was estimated from magnetic tape properties
magnetic_tape = np.zeros((decks_available, blocks_in_decks),dtype='i')
type_of_operation = 0
magnetic_tape_block_index = 0
magnetic_tape_block_preceding_index = 0
deck_number = 0

rounding = 1

shift = 0 # This is a real hidden register of the machine
          # If this is greater than 31, addition/sustraction is just one of the two original sumands
#%% Computing and Storage memory structure
# Page 0: Constants and indicators
# Pages 1-15: Programme
# Pages 16.0 - 24.42: Unfilled references
# Pages 24.44 - 27.52: Preset parameters (x0 to x100)
# Pages 27.54 - 30.62: Labels of the current routine (v0 to v100)
# Page 31: Working space

# Sectors 0-46: The Input Routine
# Sectors 47-63: The Quickies (can be fitted in range 47-61)
# Sectors 64-95: The label list
# Sectors 96-111: The routine list
# Sectors 112-113: The chapter list
# Sectors 114-126: Interlude Storage Space
# Sector 127: Working space 


#%% Instruction interpreter

# B = Bt = Cs
# This is NOT a B-modifiable instruction
def inst_00():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose    
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_register[fetched_B_register] = int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[fetched_B_register] = computing_store[int(pointer)]%1024        
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# Cs = B
# This is NOT a B-modifiable instruction
def inst_01():
    global B_register, fetched_B_register, computing_store, literal, verbose 
    pointer = literal/2
    if (pointer*10)%10 == 0:
        computing_store[int(pointer)] = computing_store[int(pointer)]%1024 + B_register[fetched_B_register]*8192
    else:
        computing_store[int(pointer)] = int(computing_store[int(pointer)]/1024)*1024 + B_register[fetched_B_register]        
    if verbose == True:
        print('computing_store_inst['+str(literal)+'] = '+str(int(computing_store[literal]/1024)))
        print('computing_store_add['+str(literal)+'] = '+str(computing_store[literal]%1024))

# B = Bt = B + Cs
# This is NOT a B-modifiable instruction
def inst_02():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_register[fetched_B_register] = (B_register[fetched_B_register] + int(computing_store[int(pointer)]/1024)*1024)%1024
    else:
        B_register[fetched_B_register] = (B_register[fetched_B_register] + computing_store[int(pointer)]%1024)%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B - Cs
# This is NOT a B-modifiable instruction
def inst_03():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_register[fetched_B_register] = B_register[fetched_B_register] - int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[fetched_B_register] = B_register[fetched_B_register] - computing_store[int(pointer)]%1024
    if B_register[fetched_B_register] < 0 and B_register[fetched_B_register] > -513:
        B_register[fetched_B_register] = np.abs(B_register[fetched_B_register]) + 511
    if B_register[fetched_B_register] <= -513:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B/2 - Cs
# This is NOT a B-modifiable instruction
def inst_04():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_register[fetched_B_register] = int(B_register[fetched_B_register]/2) - int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[fetched_B_register] = int(B_register[fetched_B_register]/2) - computing_store[int(pointer)]%1024
    if B_register[fetched_B_register] < 0 and B_register[fetched_B_register] > -513:
        B_register[fetched_B_register] = np.abs(B_register[fetched_B_register]) + 511
    if B_register[fetched_B_register] <= -513:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B & Cs
# This is NOT a B-modifiable instruction
def inst_05():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_register[fetched_B_register] = B_register[fetched_B_register] & (int(computing_store[int(pointer)]/1024)*1024)
    else:
        B_register[fetched_B_register] = B_register[fetched_B_register] & (computing_store[int(pointer)]%1024)
    if B_register[fetched_B_register] < 0:
       B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
       B_register[fetched_B_register] = B_register[fetched_B_register]%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B ^ Cs
# This is NOT a B-modifiable instruction
def inst_06():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_register[fetched_B_register] = B_register[fetched_B_register] ^ (int(computing_store[int(pointer)]/1024)*1024)
    else:
        B_register[fetched_B_register] = B_register[fetched_B_register] ^ (computing_store[int(pointer)]%1024)
    if B_register[fetched_B_register] < 0:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
        B_register[fetched_B_register] = B_register[fetched_B_register]%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# Bt = B - Cs
# This is NOT a B-modifiable instruction
def inst_07():
    global B_register, B_test, fetched_B_register, computing_store, literal, verbose
    pointer = literal/2
    if (pointer*10)%10 == 0:
        B_test = B_register[fetched_B_register] - int(computing_store[int(pointer)]/1024)*1024
    else:
        B_test = B_register[fetched_B_register] - computing_store[int(pointer)]%1024        
    if B_test < 0 and B_test > -513:
        B_test = np.abs(B_test) + 511
    if B_test <= -513:
        B_test = B_test + 1024
    if verbose == True:
        print('B_test = '+str(B_test))

# Bt != 0
# This is a B-modifiable instruction
def inst_08():
    global B_test, B_register, fetched_B_register, program_counter, literal, verbose
    if B_test != 0:
        program_counter = B_register[fetched_B_register] + literal-1
        if verbose == True:
            print('Jumping to: '+str(program_counter + 1))
    else:
        if verbose == True:
            print('No jumping made')            

# Bt >= 0
# This is a B-modifiable instruction
def inst_09():
    global B_test, B_register, fetched_B_register, program_counter, literal, verbose
    if B_test < 512:  #This means B_test is positive, since 9th bit is off            
                      #Remember, B_test register is signed, so 9th bit is sign.
        program_counter = B_register[fetched_B_register] + literal-1
        if verbose == True:
            print('Jumping to: '+str(program_counter + 1))
    else:
        if verbose == True:
            print('No jumping made')            

# B = Bt = n
# This is NOT a B-modifiable instruction
def inst_10():
    global B_register, B_test, fetched_B_register, literal, verbose
    B_register[fetched_B_register] = literal
    B_test = literal
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B + n
# This is NOT a B-modifiable instruction
def inst_12():
    global B_register, B_test, fetched_B_register, literal, verbose
    B_register[fetched_B_register] = (B_register[fetched_B_register] + literal)%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B - n
# This is NOT a B-modifiable instruction
def inst_13():
    global B_register, B_test, fetched_B_register, literal, verbose
    B_register[fetched_B_register] = B_register[fetched_B_register] - literal
    if B_register[fetched_B_register] < 0 and B_register[fetched_B_register] > -513:
        B_register[fetched_B_register] = np.abs(B_register[fetched_B_register]) + 511
    if B_register[fetched_B_register] <= -513:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B = Bt = B/2 - n
# This is NOT a B-modifiable instruction
def inst_14():
    global B_register, B_test, fetched_B_register, literal, verbose
    B_register[fetched_B_register] = B_register[fetched_B_register]/2 - literal
    if B_register[fetched_B_register] < 0 and B_register[fetched_B_register] > -513:
        B_register[fetched_B_register] = np.abs(B_register[fetched_B_register]) + 511
    if B_register[fetched_B_register] <= -513:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_15():
    global B_register, B_test, fetched_B_register, literal, verbose 
    B_register[fetched_B_register] = B_register[fetched_B_register] & literal
    if B_register[fetched_B_register] < 0:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
        B_register[fetched_B_register] = B_register[fetched_B_register]%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_16():
    global B_register, B_test, fetched_B_register, literal, verbose
    B_register[fetched_B_register] = B_register[fetched_B_register] ^ literal
    if B_register[fetched_B_register] < 0:
       B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
       B_register[fetched_B_register] = B_register[fetched_B_register]%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_17():
    global B_register, B_test, fetched_B_register, literal, verbose
    B_test = B_register[fetched_B_register]-literal
    if B_test < 0:
        B_test = B_test + 1024
    if verbose == True:
        print('B_test = '+str(B_test))
    
def inst_18():
    global B_register, B_test, fetched_B_register, literal, program_counter, verbose
    if B_test != 0:              
        program_counter = literal-1
        if verbose == True:
            print('Jumping to: '+str(literal))
    else:
        if verbose == True:
            print('No jumping made')            
    if B_register[fetched_B_register] >= 1023:
        B_register[fetched_B_register] = 0
    else:
        B_register[fetched_B_register] = B_register[fetched_B_register] + 1

    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_test = B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

# B7 = B7t = Cs
# This is a B-modifiable instruction
def inst_20():
    global B_register, fetched_B_register, computing_store, literal, sac_test, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        B_register[7] =  int(computing_store[int(pointer)]/1024)%1024
    else:
        B_register[7] =  computing_store[int(pointer)]%1024
    if verbose == True:                                             
        print('Computing store address '+str(pointer))
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

# Cs = B7
# This is a B-modifiable instruction
def inst_21():
    global B_register, fetched_B_register, computing_store, literal, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        computing_store[int(pointer)] = computing_store[int(pointer)]%1024 + B_register[7]*1024#8192
    else:
        computing_store[int(pointer)] = int(computing_store[int(pointer)]/1024)*1024 + B_register[7]
    if verbose == True:
        print('sac = '+str(B_register[7]))    
        print('computing_store_instruction['+str(int(pointer))+'] = '+str(int(computing_store[int(pointer)]/1024)))
        print('computing_store_address['+str(int(pointer))+'] = '+str(computing_store[int(pointer)]%1024))

# B7 = B7t = B7 + Cs
# This is a B-modifiable instruction
def inst_22():
    global B_register, fetched_B_register, computing_store, literal, sac_test, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        B_register[7] = (B_register[7] + int(computing_store[int(pointer)]/1024)%1024)%1024
    else:
        B_register[7] = (B_register[7] + computing_store[int(pointer)]%1024)%1024
    if verbose == True:
        print('este es el literal '+str(literal))
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

# B7 = B7t = B7 - Cs
# This is a B-modifiable instruction
def inst_23():
    global B_register, computing_store, literal, sac_test, fetched_B_register, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        B_register[7] = B_register[7]-int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[7] = B_register[7]-computing_store[int(pointer)]%1024
    if B_register[7] < 0 and B_register[7] > -513:
        B_register[7] = np.abs(B_register[7]) + 511
    if B_register[7] <= -513:
        B_register[7] = B_register[7] + 1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

# B7 = B7t = B7/2 - Cs
# This is a B-modifiable instruction
def inst_24():
    global B_register, computing_store, literal, sac_test, fetched_B_register, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        B_register[7] = int(B_register[7]/2) - int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[7] = int(B_register[7]/2) - computing_store[int(pointer)]%1024
    if B_register[7] < 0 and B_register[7] > -513:
        B_register[7] = np.abs(B_register[7]) + 511
    if B_register[7] <= -513:
        B_register[7] = B_register[7] + 1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

# B7 = B7t = B7 & Cs
# This is a B-modifiable instruction
def inst_25():
    global B_register, computing_store, literal, sac_test, fetched_B_register, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        B_register[7] = B_register[7] & int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[7] = B_register[7] & computing_store[int(pointer)]%1024
    if B_register[7] < 0:
        B_register[7] = B_register[7] + 1024
    if B_register[7] > 1023:
        B_register[7] = B_register[7]%1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

# B7 = B7t = B7 ^ Cs
# This is a B-modifiable instruction
def inst_26():
    global B_register, computing_store, literal, sac_test, fetched_B_register, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        B_register[7] = B_register[7] ^ int(computing_store[int(pointer)]/1024)*1024
    else:
        B_register[7] = B_register[7] ^ computing_store[int(pointer)]%1024
    if B_register[7] < 0:
        B_register[7] = B_register[7] + 1024
    if B_register[7] > 1023:
        B_register[7] = B_register[7]%1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

# B7t = B7 ^ Cs
# This is a B-modifiable instruction
def inst_27():
    global B_register, computing_store, literal, sac_test, fetched_B_register, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        sac_test = B_register[7]-int(computing_store[int(pointer)]/1024)*1024
    else:
        sac_test = B_register[7]-computing_store[int(pointer)]%1024        
    if sac_test < 0 and sac_test > -513:
        sac_test = np.abs(sac_test) + 511
    if B_register[7] <= -513:
        sac_test = sac_test + 1024
    if verbose == True:
        print('Sac_test = '+str(sac_test))

def inst_28():
    global sac_test, B_register, fetched_B_register, program_counter, literal, verbose
    if sac_test == 0:              
        program_counter = B_register[fetched_B_register] + literal-1
        if verbose == True:
            print('Jumping to: '+str(program_counter + 1))
    else:
        if verbose == True:
            print('No jumping made')            

def inst_29():
    global sac_test, B_register, fetched_B_register, program_counter, literal, verbose
    if sac_test >= 0:              
        program_counter = B_register[fetched_B_register] + literal-1
        if verbose == True:
            print('Jumping to: '+str(program_counter + 1))
    else:
        if verbose == True:
            print('No jumping made')            

def inst_30():
    global B_register, fetched_B_register, literal, sac_test, verbose
    B_register[7] = B_register[fetched_B_register] + literal
    if B_register[7] >= 1024:
        B_register[7] = B_register[7]%1024   
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

def inst_32():
    global B_register, fetched_B_register, literal, sac_test, verbose
    B_register[7] = (B_register[fetched_B_register] + B_register[7] + literal)%1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

def inst_33():
    global B_register, fetched_B_register, literal, sac_test, verbose
    B_register[7] = B_register[7] - literal - B_register[fetched_B_register]
    if B_register[7] < 0 and B_register[7] > -513:
        B_register[7] = np.abs(B_register[7]) + 511
    if B_register[7] <= -513:
        B_register[7] = B_register[7] + 1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

def inst_34():
    global B_register, fetched_B_register, literal, sac_test, verbose
    B_register[7] = int(B_register[7]/2) - literal - B_register[fetched_B_register]
    if B_register[7] < 0 and B_register[7] > -513:
        B_register[7] = np.abs(B_register[7]) + 511
    if B_register[7] <= -513:
        B_register[7] = B_register[7] + 1024
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

def inst_35():
    global B_register, fetched_B_register, literal, sac_test, verbose
    B_register[7] = B_register[7] & (literal + B_register[fetched_B_register]) #Not sure if B_register is added to literal
    if B_register[7] < 0:
        B_register[7] = B_register[7] + 1024
    if B_register[7] > 1023:
        B_register[7] = B_register[7]%1024        
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

def inst_36():
    global B_register, fetched_B_register, literal, sac_test, verbose
    B_register[7] = int(B_register[7]/2) ^ (literal + B_register[fetched_B_register]) #Not sure if B_register is added to literal
    if B_register[7] < 0:
        B_register[7] = B_register[7] + 1024
    if B_register[7] > 1023:
        B_register[7] = B_register[7]%1024        
    sac_test = B_register[7]
    if verbose == True:
        print('Sac(B7) = '+str(sac_test))

def inst_37():
    global B_register, fetched_B_register, literal, sac_test, verbose
    sac_test = B_register[7] - literal  - B_register[fetched_B_register]
    if sac_test < 0 and sac_test > -513:
        sac_test = np.abs(sac_test) + 511
    if B_register[7] <= -513:
        sac_test = sac_test + 1024
    if verbose == True:
        print('Sac_test = '+str(sac_test))
    
def inst_38():
    global sac_test, B_register, fetched_B_register, program_counter, literal, verbose
    if sac_test != 0:              
        program_counter = B_register[fetched_B_register] + literal-1
        if verbose == True:
            print('Jumping to: '+str(program_counter + 1))
    else:
        if verbose == True:
            print('No jumping made')
    B_register[7] = B_register[7] + 1
    if B_register[7] >= 1024:
        B_register[7] = 0
    sac_test = B_register[7]
    if verbose == True:
        print(str(sac_test))    


# The accumulator is x.2^y,  -256 <= y <= 255
#                              -1 <= x <= 1-2^-29
# A floating number is standarized is the two MSB are different
# -1 <= x < -1/2   or  1/2 <= x < 1
# The first 10 bit is exponent (2^a) (-256<= a <=255)
# The seccond 10 bit is LSB (b*2^-29) (0<= b <= 1023)
# The third 10 bit (c*2^-19) (0<= c <= 1023)
# The fourth 10 bit (d*2^-9) (-512<= d <=511)
# Accumulator = (d*2^-9 + c*2^-19 + b*2^-29).2^a

def inst_40():
    global accumulator_MSB, accumulator_LSB, computing_store, B_register, fetched_B_register, literal, verbose
    CS_add = literal + B_register[fetched_B_register]
    accumulator_LSB = computing_store[CS_add]%1048576
    accumulator_MSB = computing_store[CS_add + 1]%1048576
    if verbose == True:
        print('Accumulator_LSB = ' + str(accumulator_LSB))
        print('Accumulator_MSB = ' + str(accumulator_LSB))

def inst_41():
    global accumulator_MSB, accumulator_LSB, computing_store, B_register, fetched_B_register, literal, verbose
    CS_add = literal + B_register[fetched_B_register]
    computing_store[CS_add] = accumulator_LSB%1048576
    computing_store[CS_add + 1] = accumulator_MSB%1048576
    if verbose == True:
        print('Computing store['+str(CS_add) + '] = ' + str(accumulator_LSB%1048576))
        print('Computing store['+str(CS_add + 1) + '] = ' + str(accumulator_MSB%1048576))

def inst_42():
    global rounding, shift, accumulator_MSB, accumulator_LSB, computing_store, B_register, fetched_B_register, literal, verbose
    CS_add = literal + B_register[fetched_B_register]
    #-----------------------------------------------------------
    #Test if accumulator exponent is negative
    #That is, if the 10th bit is set
    if int(int(accumulator_LSB/1024)/512) == 1:
        #Then make the number negative in the allowed interval
        accumulator_exponent = -1-(int(accumulator_LSB/1024)%256)
    else:
        #Then make the number positive in the allowed interval
        accumulator_exponent = int(accumulator_LSB/1024)%256
    #-----------------------------------------------------------
    #Test if accumulator mantissa is negative
    #That is, if the 20th MSB is set
    if int(accumulator_MSB/1048576) == 1: #If it is negative
        accumulator_mantissa = -1 - (accumulator_MSB%524288)*1024 - accumulator_LSB%1024 
    else: #If it is positive
        accumulator_mantissa = (accumulator_MSB%524288)*1024 + accumulator_LSB%1024 
    #-----------------------------------------------------------
    #Test if Computing store exponent is negative
    #That is, if the 10th bit is set    
    if int(int(computing_store[CS_add]/1024)/512) == 1:
        #Then make the number negative in the allowed interval
        CS_exponent = -1-(int(computing_store[CS_add]/1024)%256)
    else:
        #Then make the number positive in the allowed interval
        CS_exponent = int(computing_store[CS_add]/1024)%256
    #-----------------------------------------------------------
    #Test if Computing store mantissa is negative
    #That is, if the 20th MSB is set
    if int(computing_store[CS_add + 1]/1048576) == 1: #If it is negative
        computing_store_mantissa = -1 - (computing_store[CS_add + 1]%524288)*1024 - computing_store[CS_add]%1024 
    else: #If it is positive
        computing_store_mantissa = (computing_store[CS_add + 1]%524288)*1024 + computing_store[CS_add]%1024 
    #-----------------------------------------------------------
    #Decide which number (absolute value) is bigger 
    exponents_difference = accumulator_exponent - CS_exponent
    shift = np.abs(exponents_difference)
    #-----------------------------------------------------------    
    # If accumulator is bigger or equal than CS
    if np.abs(exponents_difference) < 32:
        if exponents_difference > 0:
            #Do nothing (yet) to the accumulator exponent
            #Then adjust CS mantissa to perform adding
            CS_about_to_add = int(computing_store_mantissa/(2**exponents_difference)) | rounding               
            accumulator_mantissa = accumulator_mantissa + CS_about_to_add 
        if exponents_difference == 0:
            #Do nothing (yet) to the accumulator exponent
            #Then adjust CS mantissa to perform adding
            CS_about_to_add = computing_store_mantissa                   
            accumulator_mantissa = accumulator_mantissa + CS_about_to_add 
        if exponents_difference < 0:
            accumulator_exponent = CS_exponent
            #Then adjust CS mantissa to perform adding
            acc_about_to_add = int(accumulator_mantissa/(2**exponents_difference)) | rounding
            accumulator_mantissa = computing_store_mantissa + acc_about_to_add
        if accumulator_mantissa == 0:
            if rounding == 0:
                accumulator_exponent = -256
            else:
                accumulator_mantissa = 536870912
                accumulator_exponent = accumulator_exponent - 29
                if accumulator_exponent < -256:
                    accumulator_exponent = -256                
        else:
            #If the number can't be accomodated in the form x,xxxxxx
            if accumulator_mantissa >= 1073741824:
                accumulator_mantissa = int(accumulator_mantissa/2) | 1
                accumulator_exponent = accumulator_exponent + 1    
            while accumulator_mantissa < 536870912:
                accumulator_mantissa = accumulator_mantissa*2 
                accumulator_exponent = accumulator_exponent - 1    
        if accumulator_mantissa < 0:        
            accumulator_MSB = 1048576 + int(np.abs(accumulator_mantissa)/1024)%524288 - 1 
            accumulator_LSB = (np.abs(accumulator_mantissa)%1024)*1024
        else:
            accumulator_MSB = int(accumulator_mantissa/1024)%524288 
            accumulator_LSB = accumulator_mantissa%1024
        if accumulator_exponent < 0:
            accumulator_LSB = accumulator_LSB + 1048576 + (np.abs(accumulator_exponent) - 1)*1024
        else:
            accumulator_LSB = accumulator_LSB + accumulator_exponent*1024
    else:
        if exponents_difference < 0: #If Accumulator is 32 order of magnitud less 
            inst_40()                #than CS, just transfer CS into Accumulator.
        #If Accumulator is 32 or more orders of magnitud bigger than CS, do nothing.
        
def inst_43(): #Must verify if sustraction is the same as addition but changing sumand sign
    global rounding, accumulator_MSB, accumulator_LSB, computing_store, B_register, fetched_B_register, literal
    CS_add = literal + B_register[fetched_B_register]
    computing_store[CS_add + 1] = computing_store[CS_add + 1] ^ 1048576
    inst_42()
    computing_store[CS_add + 1] = computing_store[CS_add + 1] ^ 1048576

def inst_44():
    global rounding, accumulator_MSB, accumulator_LSB, computing_store, B_register, fetched_B_register, literal
    rounding = 0
    inst_42()
    rounding = 1

def inst_45(): #Must verify if sustraction is the same as addition but changing sumand sign
    global rounding, accumulator_MSB, accumulator_LSB, computing_store, B_register, fetched_B_register, literal
    CS_add = literal + B_register[fetched_B_register]
    rounding = 0
    computing_store[CS_add + 1] = computing_store[CS_add + 1] ^ 1048576
    inst_42()
    rounding = 1
    computing_store[CS_add + 1] = computing_store[CS_add + 1] ^ 1048576
    
def inst_46():
    global accumulator_MSB, accumulator_LSB, B_register, fetched_B_register, literal
    print('WORK TO DO')

def inst_48():
    global shift, program_counter, B_register, fetched_B_register, literal, verbose
    if shift <= 31:
        program_counter = B_register[fetched_B_register] + literal - 1
        if verbose == True:
            print('Jumping to: ' + str(program_counter + 1))

def inst_49():
    global accumulator_MSB, program_counter, B_register, fetched_B_register, literal, verbose
    if (accumulator_MSB & 524288) == 0:
        program_counter = B_register[fetched_B_register] + literal - 1
        if verbose == True:
            print('Jumping to: ' + str(program_counter + 1))

def inst_56():
    global computing_store, literal, CRT_x, CRT_y, verbose   #Must check if address needs to be halved
    CRT_y = (int(computing_store[literal+1]/1024))%256
    CRT_x = computing_store[literal+1]%256    
    if verbose == True:
        print('CRT Set coordinates')

def inst_57():
    global verbose
    if verbose == True:
        print('Dummy instruction')

def inst_58():
    global verbose
    if verbose == True:
        print('\a')
        print('Hoot')

def inst_59():
    global B_register, fetched_B_register, program_counter, literal, verbose
    program_counter = B_register[fetched_B_register] + literal-1
    if verbose == True:
        print('Jumping to: '+str(program_counter + 1))

def inst_60():
    global computing_store, literal, tape, tape_index, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        computing_store[int(pointer)] = computing_store[int(pointer)]%1024 + tape[tape_index]*1024 #*8192
    else:
        computing_store[int(pointer)] = int(computing_store[int(pointer)]/1024)*1024 + tape[tape_index]
    if verbose == True:
        print('Tape character '+str(tape_index)+' = '+str(tape[tape_index]))
        print('computing_store['+str(int(pointer))+']_Address = '+str(computing_store[int(pointer)]%1024))
    tape_index = tape_index + 1

def inst_61():
    global computing_store, switches, literal, verbose
    if verbose == True:
        print('Address of computing store: '+str(literal))
        print('Switches_number: '+str(int(switches,2)))
    pointer = (B_register[fetched_B_register] + literal)/2
    if (pointer*10)%10 == 0:
        computing_store[int(pointer)] = computing_store[int(pointer)]%1024 + int(switches,2)*8192
    else:
        computing_store[int(pointer)] = int(computing_store[int(pointer)]/1024)*1024 + int(switches,2)
    if verbose == True:
        print('computing_store['+str(int(pointer))+'] = '+str(computing_store[int(pointer)]))

def inst_62():
    global literal, B_register, fetched_B_register, tape_index, verbose
    tape[tape_index] = (B_register[fetched_B_register]+literal)%32
    tape_index = tape_index + 1
    if verbose == True:
        print('Tape character '+str(tape_index)+' = '+str(tape[tape_index-1]))

def inst_63():
    global literal, tape_index, computing_store, B_register, fetched_B_register, verbose
    pointer = (B_register[fetched_B_register] + literal)/2
    if fetched_B_register == 0:
        pointer = literal%1024
    else:
        B_sign = np.sign(B_register[fetched_B_register])
        if B_sign >= 0:
            B_reg = B_register[fetched_B_register]%512
        else:
            B_reg = -1*np.abs(B_register[fetched_B_register])%513            
        pointer = literal%1024 + B_reg   # Address in 0-1534
        if pointer < 0:
            pointer = pointer + 2048     # Address in 1536-2047-0-1022
            if verbose == True:
                print('B-modified address')  # Only address 1535 is impossible to reach.          
    tape[tape_index] = computing_store[pointer]%32
    if verbose == True:
        print('Tape character '+str(tape_index)+' = '+str(tape[tape_index]))
    tape_index = tape_index + 1

def inst_64(): #Display made with bulbs
    global literal, computing_store, display, verbose
    display[0] = computing_store[literal]
    display[1] = computing_store[literal+1]
    sleep(0.05)  #Actually, the signal was available for 120us
    display[0] = 0
    display[1] = 0
    if verbose == True:
        print('Show long register on display')

def inst_65(): #Shutter open
    global shutter, verbose
    shutter = True
    if verbose == True:
        print('Open Shutter')
    
def inst_66(): #Shutter close
    global shutter, verbose
    shutter = False
    if verbose == True:
        print('Close Shutter')
    
def inst_67():
    global B_register, fetched_B_register, sector_selected, literal, verbose
    sector_selected = int(literal) + B_register[fetched_B_register]
    if verbose == True:
        print('Selected_sector: '+str(sector_selected))

def inst_68():
    global B_register, fetched_B_register, sector_selected, computing_store, backing_store_sectorized, literal, verbose
    if fetched_B_register != 0:
        inicio = (B_register[fetched_B_register]+literal)*64
    else:
        inicio = literal*64
    fin = inicio+64
    computing_store[inicio:fin] = list(backing_store_sectorized[sector_selected])
    if verbose == True:
        print('Computer Store '+str(literal)+ ' now contains sector ' + str(sector_selected) + ' of Drum')

def inst_69():
    global B_register, fetched_B_register, sector_selected, computing_store, backing_store_sectorized, literal, verbose
    backing_store_sectorized[sector_selected] = list(computing_store[(B_register[fetched_B_register]+literal)*64:(B_register[fetched_B_register]+literal)*64+64])
    if verbose == True:
        print('Drum sector '+str(sector_selected)+ ' now contains page ' + str(literal) + ' of Computing Store')

def inst_70():
    global B_register, fetched_B_register, B_test, literal, accumulator_exponent, verbose
    B_register[fetched_B_register] = (accumulator_exponent + literal)%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_71():
    global B_register, fetched_B_register, B_test, literal, accumulator_exponent, verbose
    accumulator_exponent = B_register[fetched_B_register]
    if verbose == True:
        print('Accumulator exponent = ' + str(accumulator_exponent))

def inst_72():
    global B_register, fetched_B_register, B_test, accumulator_exponent, literal, verbose
    B_register[fetched_B_register] = (B_register[fetched_B_register] + accumulator_exponent + literal)%1024
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_test = B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_73():
    global B_register, fetched_B_register, B_test, accumulator_exponent, literal, verbose
    B_register[fetched_B_register] = B_register[fetched_B_register] - (accumulator_exponent + literal)%1024
    if B_register[fetched_B_register] < 0:
       B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
       B_register[fetched_B_register] = B_register[fetched_B_register]%1024     
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_test = B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_74():
    global B_register, fetched_B_register, B_test, accumulator_exponent, literal, verbose
    B_register[fetched_B_register] = int(B_register[fetched_B_register]/2) - (accumulator_exponent + literal)%1024
    if B_register[fetched_B_register] < 0:
       B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
       B_register[fetched_B_register] = B_register[fetched_B_register]%1024     
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_test = B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_75():
    global B_register, fetched_B_register, B_test, accumulator_exponent, literal, verbose
    B_register[fetched_B_register] = B_register[fetched_B_register] & (accumulator_exponent + literal)%1024
    if B_register[fetched_B_register] < 0:
       B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
       B_register[fetched_B_register] = B_register[fetched_B_register]%1024     
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_test = B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_76():
    global B_register, fetched_B_register, B_test, accumulator_exponent, literal, verbose
    B_register[fetched_B_register] = B_register[fetched_B_register] ^ (accumulator_exponent + literal)%1024
    if B_register[fetched_B_register] < 0:
       B_register[fetched_B_register] = B_register[fetched_B_register] + 1024
    if B_register[fetched_B_register] > 1023:
       B_register[fetched_B_register] = B_register[fetched_B_register]%1024     
    B_test = B_register[fetched_B_register]
    if verbose == True:
        print('B_test = B_register['+str(fetched_B_register)+'] = '+str(B_register[fetched_B_register]))

def inst_77():
    global B_register, fetched_B_register, B_test, accumulator_exponent, literal, verbose
    B_test = B_register[fetched_B_register] - (accumulator_exponent + literal)%1024
    if B_test < 0:
        B_test = B_test + 1024
    if verbose == True:
        print('B_test = '+str(B_test))

def inst_78():
    global accumulator_exponent, accumulator_mantissa, literal, verbose
    accumulator_exponent = 2**literal
    accumulator_mantissa = int(accumulator_mantissa/2)
    if verbose == True:
        print('Accumulator exponent = ' + str(accumulator_exponent))
        print('Accumulator mantissa = ' + str(accumulator_mantissa))

def inst_80():
    global verbose
    # This is related to IBM cards type read and punch, and related to the printer too.
    if verbose == True:
        print('Conditioning')

def inst_81():
    global verbose
    # This is related to IBM cards type read and punch, and related to the printer too.
    if verbose == True:
        print('Read card')

def inst_82():
    global verbose
    # This is related to IBM cards type read and punch, and related to the printer too.
    if verbose == True:
        print('Punch card/print line')

def inst_83():
    global verbose
    # This is related to IBM cards type read and punch, and related to the printer too.
    if verbose == True:
        print('Paper throw')


def inst_86():
    global type_of_operation, deck_number, magnetic_tape_block_index, magnetic_tape_block_preceding_index, literal, verbose
    if verbose == True:
        print('Initiates Operation on deck')
    if type_of_operation == 5:
        magnetic_tape_block_index = magnetic_tape_block_index - 1
        if magnetic_tape_block_index < 0:
           magnetic_tape_block_index = 0
        if verbose == True:
            print('Rewind performed')
    if type_of_operation == 1:
        magnetic_tape_block_index = literal #Must restringe literal!! 
        if verbose == True:
            print('Search performed')
    if type_of_operation == 0:
        if literal%64 == 0: #cheks if this is the beginning of a page           
            computing_store[literal:literal+256] = magnetic_tape[magnetic_tape_block_index]
            magnetic_tape_block_preceding_index = magnetic_tape_block_index
            magnetic_tape_block_index = magnetic_tape_block_index + 1
        else:
            if verbose == True:
                print('Emulator message: Invalid computing store address (must be the beginning of a page)')
        if verbose == True:
            print('Read from tape performed')
    if type_of_operation == 2:
        if literal%64 == 0: #cheks if this is the beginning of a page           
            magnetic_tape[magnetic_tape_block_index] = computing_store[literal:literal+256]
            magnetic_tape_block_preceding_index = magnetic_tape_block_index
            magnetic_tape_block_index = magnetic_tape_block_index + 1
        else:
            if verbose == True:
                print('Emulator message: Invalid computing store address (must be the beginning of a page)')
        if verbose == True:
            print('Write to tape performed')
    if type_of_operation == 2:
        if literal%64 == 0: #cheks if this is the beginning of a page           
            computing_store[literal:literal+256] = magnetic_tape[magnetic_tape_block_preceding_index]
            magnetic_tape_block_preceding_index = magnetic_tape_block_index            
        else:
            if verbose == True:
                print('Emulator message: Invalid computing store address (must be the beginning of a page)')
        if verbose == True:
            print('Read from tape performed')
    if type_of_operation == 6:
        if literal%64 == 0: #cheks if this is the beginning of a page           
            magnetic_tape[magnetic_tape_block_preceding_index] = computing_store[literal:literal+256]
            magnetic_tape_block_preceding_index = magnetic_tape_block_index
        else:
            if verbose == True:
                print('Emulator message: Invalid computing store address (must be the beginning of a page)')
        if verbose == True:
            print('Write to tape performed')


def inst_87():
    global type_of_operation, deck_number, literal, verbose
    if verbose == True:
        print('Operation on deck')
    type_of_operation = int((literal%512)/64)
    deck_number = literal%8
    if type_of_operation == 5:
        if verbose == True:
            print('Rewind selected')
    if type_of_operation == 1:
        if verbose == True:
            print('Search selected')
    if type_of_operation == 0:
        if verbose == True:
            print('Read from following block selected')
    if type_of_operation == 2:
        if verbose == True:
            print('Write to following block selected')
    if type_of_operation == 4:
        if verbose == True:
            print('Read from preceding block selected')
    if type_of_operation == 6:
        if verbose == True:
            print('Write to preceding block selected')        

def inst_88():
    global TC, program_counter, literal, verbose
    TC[1] = True #This is a flag for magnetic tape I/O
    program_counter = literal-1
    if verbose == True:
        print('Jumping to: '+str(literal))

def inst_89():
    global TC, program_counter, literal, verbose
    TC[2] = True #This is a flag for magnetic tape I/O
    program_counter = literal-1
    if verbose == True:
        print('Jumping to: '+str(literal))

def inst_90():
    global accumulator_mantissa, accumulator_exponent, B_register, fetched_B_register, literal, verbose
    if fetched_B_register == 0:
        B_register[7] = (accumulator_exponent + literal)%1024
        if verbose == True:
            print('Accumulator exponent to sac: '+str(B_register[7]))
    if (fetched_B_register >= 1) and (fetched_B_register <= 3):
        B_register[7] = (channel[fetched_B_register]+literal)%1024
        if verbose == True:
            print('Channel '+str(fetched_B_register)+' read plus '+str(literal)+' to sac: '+str(B_register[7]))
    if (fetched_B_register >= 4) and (fetched_B_register <= 7):
        B_register[7] = channel[fetched_B_register]
        if verbose == True:
            print('Channel '+str(fetched_B_register)+' read to sac: '+str(B_register[7]))
        

def inst_99():
    global run
    print('Halt')
    run = False


def inst_inexistent():
    global run
    print('Inexistent_instruction')
    run = False


#The instructions necessary to run Tele-input and Tele-output are 31/:
# 00, 01, 03, 08, 09,
# 10, 12, 14, 17, 18,
# 20, 21, 23, 27, 29,
# 30, 32, 33, 34, 37,
# 38, 40, 58, 59, 60,
# 61, 62, 67, 68, 90,
# 99

# It was possible to use up to eight magnetic tape units
# four in each of the two available control units
# Tape characteristics: 60 inches/sec.
# Up to 3000 ft. long
# 8 tracks (6 for data, 1 for address and 1 for clock).
# Information is stored in blocks, address sequentially.
# The principal method of storing is in blocks of 128 forty-bit words
#  -> so one block of information in magnetic tape occupies
#     4 pages of the computing store.
# A block occupies 6.4 inches on the tape (including address).
# There is a gap of 1 inch between blocks.
# At the end of each block is an automatically introduced 6 digit checksum
# A block is re-read if checksum fails
# If the reading procedure fails multiple times, computer
# indicates "tape failure" and stops.
# Times: Read/Write next block: 127ms
#        Read/Write preceding block: 234ms
# Search: 127ms for each 4 page block scanned



switcher = {    
    '00': inst_00,
    '01': inst_01,
    '02': inst_02,
    '03': inst_03,
    '04': inst_04,
    '05': inst_05,
    '06': inst_06,
    '07': inst_07,
    '08': inst_08,
    '09': inst_09,
    '10': inst_10,
    '11': inst_inexistent,
    '12': inst_12,
    '13': inst_13,
    '14': inst_14,
    '15': inst_15,
    '16': inst_16,
    '17': inst_17,
    '18': inst_18,
    '19': inst_inexistent,
    '20': inst_20,
    '21': inst_21,
    '22': inst_22,
    '23': inst_23,
    '24': inst_24,
    '25': inst_25,
    '26': inst_26,
    '27': inst_27,
    '28': inst_28,
    '29': inst_29, # Jump if sac_test >= 0
    '30': inst_30, # sac = n
    '31': inst_inexistent,
    '32': inst_32, # sac = sac + n
    '33': inst_33, # sac = sac - n
    '34': inst_34, # sac = sac/2 - n
    '35': inst_35, # sac = sac AND n
    '36': inst_36, # sac = sac/2 XOR n
    '37': inst_37, # sac_test = sac - n
    '38': inst_38, # Jump if sac_test != 0
    '39': inst_inexistent, # Inexistent
    '40': inst_40, # Acc = CS
    '41': inst_41, # CS = Acc
    '42': inst_42, # Acc = Acc + CS (with rounding)
    '43': inst_43, # Acc = Acc - CS (with rounding)
    '44': inst_44, # Acc = Acc + CS (without rounding)
    '45': inst_45, # Acc = Acc - CS (without rounding)
    '46': inst_46, # This is not easy....
    '47': inst_inexistent,
    '48': inst_48, # Jump if shift <= 31
    '49': inst_49, # Jump if Acc >= 0
    '50': inst_inexistent, # This is for multiplication
    '51': inst_inexistent, # This is for multiplication
    '52': inst_inexistent, # This is for multiplication
    '53': inst_inexistent, # This is for multiplication
    '54': inst_inexistent, # This is for multiplication
    '55': inst_inexistent, # This is for multiplication
    '56': inst_56, # Output to CRT
    '57': inst_57, # Dummy instruction (does nothing)
    '58': inst_58, # Hoot (square pulse to speaker)
    '59': inst_59, # Unconditional Jump
    '60': inst_60, # Read tape character into computing store
    '61': inst_61, # Transfer switches to computer store
    '62': inst_62, # Write tape character from literal
    '63': inst_63, # Write tape character from computing store
    '64': inst_64, # Show long register on display
    '65': inst_65, # Open Shutter
    '66': inst_66, # Close Shutter
    '67': inst_67, # Sector selection
    '68': inst_68, # Write backing store page from drum sector
    '69': inst_69, # Write drum sector from backing store page
    '70': inst_70, # B_register = literal plus accumulator exponent
    '71': inst_71, # B_register into accumulator exponent
    '72': inst_72,
    '73': inst_73,
    '74': inst_74,
    '75': inst_75,
    '76': inst_76,
    '77': inst_77,
    '78': inst_78, # Destandarize instruction
    '79': inst_inexistent, # Inexistent
    '80': inst_80,
    '81': inst_81,
    '82': inst_82,
    '83': inst_83,
    '84': inst_inexistent,
    '85': inst_inexistent,
    '86': inst_86, # Excecution of magnetic tape order
    '87': inst_87, # Set of magnetic tape order
    '88': inst_88,
    '89': inst_89,
    '90': inst_90, # Channel reading to sac or accumulator exponent to sac
    '91': inst_inexistent,
    '92': inst_inexistent,
    '93': inst_inexistent,
    '94': inst_inexistent,
    '95': inst_inexistent,
    '96': inst_inexistent,
    '97': inst_inexistent,
    '98': inst_inexistent,
    '99': inst_99 # Halts machine
}


#%% Sector contents in Ferranti notation
field = 2

BS_machine = np.zeros((backing_store_sectors,backing_store_wps),dtype='i') 

BS ={}
#%% Sector 0: Tele-Output -> Page 0

BS[0] = {0:['610', '2+'],
         1:['106', '-1'],
         2:['107', '0'],
         3:['090', '6'],
         4:['590', '61'],

         5:['147', '0'],
         6:['186', '5'],
         7:['206', '10'],
         8:['677', '0'],
         9:['590', '62'],
         
         10:['=2,', '=2'],
         11:['=511,', '=1'],
         12:['=2,', '=2'],
         13:['=2,', '=2'],
         14:['=2,', '=2'],
         
         15:['990', '0'],
         16:['610', '19+'],
         17:['990', '0'],
         18:['610', '53+'],
         19:['104', '0'],

         20:['300', '-99'],
         21:['620', '0'],
         22:['380', '21'],
         23:['674', '0'],
         24:['680', '2'],

         25:['620', '28'],
         26:['620', '8'],
         27:['620', '0'],
         28:['620', '4'],
         29:['620', '0'],

         30:['103', '0'],
         31:['105', '0'],
         32:['101', '41'],
         33:['205', '2.0'],
         34:['210', '39+'],

         35:['106', '-4'],
         36:['340', '0'],
         37:['186', '36'],
         38:['627', '0'],
         39:['620', '0'],
         
         40:['591', '0'],
         41:['033', '39+'],
         42:['175', '127'],
         43:['185', '33'],
         44:['303', '0'],
         
         45:['101', '47'],
         46:['590', '34'],
         47:['620', '26'],
         48:['304', '0'],
         49:['101', '51'],
         
         50:['590', '34'],
         51:['620', '2'],
         52:['300', '-9'],
         53:['174', '0'],
         54:['184', '21'],
         
         55:['990', '1.0'],
         56:['620', '30'],
         57:['300', '-9'],
         58:['620', '31'],
         59:['380', '58'],
         
         60:['590', '60'],
         61:['677', '512'],
         62:['680', '0'],
         63:['590', '15']}

#%% Sector 1: Tele-Input -> Page 0

   BS[1]={0:['215', '0'],
          1:['600', '2+'],
          2:['300', '0'],
          3:['106', '-3'],
          4:['327', '0'],
          
          5:['186', '4'],
          6:['600', '7+'],
          7:['327', '0'],
          8:['591', '0'],
          9:['210', '10+'],
          
          10:['124', '0'],
          11:['175', '0'],
          12:['185', '0'],
          13:['174', '0'],
          14:['080', '17'],
          
          15:['590', '19'],
          16:['990', '0'],
          17:['370', '1023'],
          18:['280', '16'],
          19:['101', '41'],
          
          20:['600', '21+'],
          21:['105', '0'],
          22:['175', '30'],
          23:['090', '26'],
          24:['175', '26'],
          
          25:['090', '1'],
          26:['080', '20'],
          27:['580', '0'],
          28:['300', '-25'],
          29:['380', '29'],
          
          30:['590', '27'],
          31:['087', '0'],
          32:['210', '0+'],
          33:['101', '35'],
          34:['590', '1'],
          
          35:['330', '1'],
          36:['210', '11+'],
          37:['104', '0'],
          38:['105', '-1'],
          39:['101', '9'],
          
          40:['590', '1'],
          41:['175', '28'],
          42:['090', '31'],
          43:['677', '0'],
          44:['600', '45+'],
          
          45:['300', '0'],
          46:['175', '27'],
          47:['080', '50'],
          48:['687', '0'],
          49:['590', '20'],
          
          50:['697', '0'],
          51:['106', '-5'],
          52:['327', '0'],
          53:['186', '52'],
          54:['327', '127'],
          
          55:['210', '58+'],
          56:['106', '-127'],
          57:['680', '1'],
          58:['206', '0'],
          59:['276', '1.63+'],
          
          60:['280', '60'],
          61:['186', '58'],
          62:['590', '20'],
          63:['590', '19']} #,

#%% Sector 2: Standard Page 0; Handswitch Tapping; Starting Procedures -> Page 0

  BS[2] = {0:['=0', '=0'],
           1:['=0', '=0'],
           2:['=1023', '=1023'],
           3:['=1023', '=1023'],
           4:['670', '479'],

           5:['690', '0'],
           6:['670', '478'],           
           7:['680', '0'],
           8:['597', '0'],
           9:['670', '479'],

           10:['690', '0'],
           11:['670', '5'],
           12:['680', '0'],
           13:['210', '61+'],
           14:['206', '40+'],
           
           15:['677', '0'],
           16:['176', '4'],
           17:['080', '61'],
           18:['670', '3'],
           19:['680', '1'],
           
           20:['005', '61+'],
           21:['101', '1.41'],
           22:['300', '0'],
           23:['102', '-2'],
           24:['104', '600'],
           
           25:['610', '26+'],
           26:['103', '0'],
           27:['184', '24'],
           28:['080', '25'],
           29:['610', '30+'],
           
           30:['103', '0'],
           31:['080', '33'],
           32:['590', '29'],
           33:['210', '35+'],
           34:['327', '0'],
           
           35:['327', '0'],
           36:['327', '-1'],
           37:['143', '0'],
           38:['187', '37'],
           39:['172', '0'],
           
           40:['182', '24'],
           41:['370', '0'],
           42:['591', '0'],
           43:['=9', '=6'],
           44:['=6', '=6'],
       
           45:['176', '9'],
           46:['080', '13'],
           47:['677', '0'],
           48:['680', '1'],
           49:['670', '3'],
           
           50:['590', '62'],
           51:['670', '0'],
           52:['101', '1.6'],
           53:['105', '-111'],
           54:['280', '1.4'],
           
           55:['680', '0'],
           56:['=0,', '=0'],
           57:['101', '45'],
           58:['176', '2'],
           59:['090', '22'],
           
           60:['670', '12'],
           61:['300', '!=1.2'],
           62:['680', '0'],
           63:['590', '57']}

#%% Sector 3: Punch Title; Punch SAC; Tele-Output with Tapping -> Page 0 or Page 1

   BS[3] = {0:['670', '2'],
            1:['680', '0'],
            2:['101', '51'],
            3:['590', '22'],
            4:['680', '0'],
            
            5:['210', '1.10'],
            6:['175', '-105'],
            7:['185', '33'],
            8:['590', '56'],
            9:['=0', '=27'],
            
            10:['=0', '=59'],
            11:['=2', '=0'],
            12:['015', '1.38+'],
            13:['016', '1.39+'],
            14:['210', '1.32+'],
            
            15:['106', '-30'],
            16:['105', '543'],
            17:['370', '0'],
            18:['290', '1.23'],
            19:['330', '1000'],
            
            20:['290', '1.35'],
            21:['320', '500'],
            22:['105', '404'],
            23:['125', '177'],
            24:['236', '1.40+'],
            
            25:['580', '100'],
            26:['290', '1.23'],
            27:['125', '464'],
            28:['090', '1.27'],
            29:['226', '1.40+'],
            
            30:['126', '10'],
            31:['090', '1.36'],
            32:['370', '0'],
            33:['280', '1.36'],
            34:['590', '1.16'],
            
            35:['105', '1'],
            36:['625', '0'],
            37:['080', '1.16'],
            38:['105', '0'],
            39:['106', '0'],
            
            40:['591', '0'],
            41:['670', '0'],
            42:['680', '0'],
            43:['210', '53+'],
            44:['015', '19+'],
            
            45:['300', '8'],
            46:['210', '55'],
            47:['590', '19'],
            48:['103', '0'],
            49:['590', '57'],
            
            50:['203', '63+'],
            51:['210', '56+'],
            52:['106', '-4'],
            53:['340', '0'],
            54:['186', '53'],
            
            55:['627', '0'],
            56:['620', '0'],
            57:['073', '1.61'],
            58:['183', '50'],
            59:['300', '73'],
            
            60:['400', '1.62'],
            61:['670', '4'],
            62:['680', '0'],
            63:['590', '48']}
         
#%% Sector 4: The Chapter Changing Sequence (C.C.S.) /Store Clearing; Entry -> Page 0

    BS[4] = {0:['=0,', '=0'],
             1:['=0,', '=0'],
             2:['200', '1+'],
             3:['400', '44'],
             4:['670', '478'],
             
             5:['690', '0'],
             6:['670', '479'],
             7:['680', '0'],
             8:['210', '1+'],
             9:['410', '44'],
             
             10:['300', '479'],
             11:['210', '6+'],
             12:['300', '!=46'],
             13:['400', '0'],
             14:['417', '0'],
             
             15:['200', '1+'],
             16:['330', '1'],
             17:['340', '0'],
             18:['280', '22'],
             19:['200', '12+'],
             
             20:['330', '1'],
             21:['210', '12+'],
             22:['407', '0'],
             23:['410', '0'],
             24:['200', '0+'],
             
             25:['290', '31'],
             26:['320', '512'],
             27:['210', '0+'],
             28:['200', '12+'],
             29:['320', '1'],
             
             30:['210', '12+'],
             31:['200', '0'],
             32:['210', '39+'],
             33:['200', '0+'],
             34:['280', '39'],
             
             35:['200', '0'],
             36:['210', '6+'],
             37:['300', '0'],
             38:['590', '41'],
             39:['677', '0'],
             
             40:['687', '0'],
             41:['270', '1'],
             42:['380', '39'],
             43:['590', '2'],
             44:['=0', '=0'],
             
             45:['=0', '=0'],
             46:['410', '0'],
             47:['210', '48'],
             48:['101', '0'],
             49:['370', '78'],
             
             50:['380', '47'],
             51:['670', '2'],
             52:['680', '1'],
             53:['400', '44'],
             54:['300', '!=1.16'],
             
             55:['417', '-2'],
             56:['380', '55'],
             57:['670', '479'],
             58:['690', '1'],
             59:['300', '-6'],
             
             60:['417', '1.12'],
             61:['380', '60'],
             62:['590', '31'],
             63:['590', '46']}

#%% Sector 5: Error Print -> Page 0
  
    BS[5] = {0:['620', '10'],
             1:['101', '0'],
             2:['106', '0'],
             3:['300', '0'],
             4:['101', '6'],
             
             5:['590', '1.12'],
             6:['200', '3'],
             7:['370', '206'],
             8:['380', '25'],
             9:['106', '-3'],
             
             10:['410', '18'],
             11:['100', '0'],
             12:['590', '29'],
             13:['670', '477'],
             14:['690', '1'],
             
             15:['670', '3'],
             16:['680', '1'],
             17:['011', '1+'],
             18:['016', '2+'],
             19:['106', '-8'],
             
             20:['636', '48'],
             21:['186', '20'],
             22:['106', '13'],
             23:['101', '6'],
             24:['590', '29'],
             
             25:['210', '3'],
             26:['350', '7'],
             27:['101', '0'],
             28:['106', '-2'],
             29:['620', '30'],
             
             30:['620', '13'],
             31:['620', '27'],
             32:['626', '4'],
             33:['620', '0'],
             34:['080', '1.12'],
             
             35:['620', '10'],
             36:['206', '19+'],
             37:['080', '42'],
             38:['290', '42'],
             39:['620', '11'],
             
             40:['360', '-1'],
             41:['320', '1'],
             42:['101', '49'],
             43:['590', '1.12'],
             44:['=30', '=13'],
             
             45:['=27', '=5'],
             46:['=18', '=18'],
             47:['=15', '=18'],
             48:['=0', '=0'],
             49:['176', '0'],
             
             50:['620', '15'],
             51:['186', '36'],
             52:['001', '1+'],
             53:['006', '2+'],
             54:['670', '477'],
             
             55:['680', '1'],
             56:['580', '0'],
             57:['300', '-20'],
             58:['380', '58'],
             59:['610', '60+'],
             
             60:['100', '0'],
             61:['090', '56'],
             62:['670', '479'],
             63:['680', '0']}
         
#%% Sector 6: Post Mortems 
            
    BS[6] = {0:['620', '0'],
             1:['620', '30'],
             2:['620', '13'],
             3:['620', '13'],
             4:['620', '27'],
             
             5:['102', '6'],
             6:['677', '0'],
             7:['177', '32'],
             8:['370', '0'],
             9:['290', '55'],
             
             10:['620', '19'],
             11:['680', '31'],
             12:['620', '0'],
             13:['620', '14'],
             14:['012', '41+'],
             
             15:['013', '40+'],
             16:['717', '0'],
             17:['103', '-18'],
             18:['102', '543'],
             19:['370', '0'],
             
             20:['290', '25'],
             21:['330', '1000'],
             22:['290', '36'],
             23:['320', '500'],
             24:['102', '404'],
             
             25:['122', '177'],
             26:['233', '61+'],
             27:['290', '25'],
             28:['122', '464'],
             29:['090', '28'],
             
             30:['223', '61+'],
             31:['123', '6'],
             32:['090', '37'],
             33:['=752', '=0'],
             34:['280', '37'],
             
             35:['590', '18'],
             36:['102', '1'],
             37:['622', '0'],
             38:['187', '18'],
             39:['900', '0'],
             
             40:['103', '0'],
             41:['670', '0'],
             42:['680', '0'],
             43:['290', '45'],
             44:['300', '-1'],
             
             45:['370', '32'],
             46:['290', '44'],
             47:['105', '-4'],
             48:['327', '0'],
             49:['185', '48'],
             
             50:['704', '0'],
             51:['210', '52+'],
             52:['103', '100'],
             53:['676', '1'],
             54:['680', '0'],
             
             55:['090', '10'],
             56:['620', '16'],
             57:['590', '12'],
             58:['303', '1'],
             59:['157', '31'],
             
             60:['183', '53'],
             61:['990', '0'],
             62:['304', '1'],
             63:['590', '0']}

#%% Sector 7: Post Mortems

    BS[7] = {0:['101', '512'],
             1:['590', '24'],
             2:['010', '3+'],
             3:['126', '0'],
             4:['156', '63'],
             
             5:['102', '-1'],
             6:['330', '10'],
             7:['122', '1'],
             8:['290', '6'],
             9:['717', '0'],
             
             10:['670', '8'],
             11:['185', '13'],
             12:['102', '31'],
             13:['680', '0'],
             14:['627', '0'],
             
             15:['620', '14'],
             16:['410', '44'],
             17:['205', '2.44+'],
             18:['106', '-5'],
             19:['172', '1'],
             
             20:['080', '49'],
             21:['210', '25+'],
             22:['350', '1'],
             23:['280', '0'],
             24:['205', '2.44'],
             
             25:['107', '0'],
             26:['147', '0'],
             27:['290', '31'],
             28:['127', '512'],
             29:['590', '31'],
             
             30:['126', '1'],
             31:['210', '3+'],
             32:['340', '0'],
             33:['186', '82'], #maybe 32?
             34:['006', '3+'],
             
             35:['592', '1'],
             36:['105', '768'],
             37:['403', '0'],
             38:['410', '44'],
             39:['205', '2.44'],
             
             40:['340', '0'],
             41:['340', '0'],
             42:['590', '58'],
             43:['171', '0'],
             44:['090', '46'],
             
             45:['620', '26'],
             46:['175', '771'],
             47:['185', '37'],
             48:['590', '56'],
             49:['092', '28'],
             
             50:['102', '7'],
             51:['106', '6'],
             52:['670', '6'],
             53:['620', '14'],
             54:['185', '13'],
             
             55:['590', '36'],
             56:['670', '6'],
             57:['680', '0'],
             58:['340', '632'],
             59:['290', '61'],
             
             60:['330', '64'],
             61:['670', '11'],
             62:['680', '0'],
             63:['590', '37']}

#%% Sector 8: Post Mortems

     BS[8] = {0:['207', '38'],
              1:['670', '7'],
              2:['590', '13'],
              3:['620', '30'], #maybe 80
              4:['620', '13'],
              
              5:['403', '0'],
              6:['102', '8'],
              7:['410', '44'],
              8:['280', '32'],
              9:['205', '2.44'],
              
              10:['620', '10'],
              11:['101', '-5'],
              12:['670', '6'],
              13:['680', '0'],
              14:['202', '38'],
              
              15:['627', '0'],
              16:['900', '0'],
              17:['207', '43'],
              18:['627', '0'],
              19:['620', '28'],
              
              20:['306', '0'],
              21:['102', '7'],
              22:['106', '6'],
              23:['590', '12'],
              24:['350', '15'],
              
              25:['207', '38'],
              26:['627', '0'],
              27:['300', '0'],
              28:['101', '-3'],
              29:['340', '0'],
              
              30:['181', '29'],
              31:['132', '6'],
              32:['210', '27+'],
              33:['090', '24'],
              34:['002', '27+'],
              
              35:['205', '2.44'],
              36:['350', '7'],
              37:['590', '0'],
              38:['=16', '=1'],
              39:['=2', '=19'],
              
              40:['=4', '=21'],
              41:['=22', '=7'],
              42:['=8', '=25'],
              43:['171', '0'],
              44:['181', '53'],

              45:['305', '1'],
              46:['290', '51'],
              47:['350', '1'],
              48:['107', '-1'],
              49:['175', '771'],
              
              50:['185', '58'],
              51:['670', '6'],
              52:['590', '57'],
              53:['620', '14'],
              54:['590', '43'],
              
              55:['105', '767'],
              56:['590', '45'],
              57:['680', '0'],
              58:['380', '6'],
              59:['176', '6'],
              
              60:['080', '3'],
              61:['670', '7'],
              62:['680', '0'],
              63:['590', '3']}

#%% Sector 9: Rescue
         
     BS[9] = {0:['106', '-20'],
              1:['677', '1'],
              2:['696', '31'],
              3:['320', '1'],
              4:['186', '1'],
              
              5:['670', '479'],
              6:['680', '31'],
              7:['677', '-31'],
              8:['690', '31'],
              9:['677', '0'],
              
              10:['680', '31'],
              11:['580', '0'],
              12:['300', '-30'],
              13:['380', '13'],
              14:['590', '11'],
              
              15:['680', '0'],
              16:['=0', '=0'],
              17:['=0', '=0'],
              18:['=512', '=0'], #This is -1
              19:['=512', '=0'], # Maybe is double precision
        
              20:['=976', '=576'], #This is one million
              21:['=976', '=576'],
              22:['620', '3'],
              23:['900', '256'],
              24:['590', '30'],
              
              25:['101', '3'],
              26:['440', '16'],
              27:['777', '256'],
              28:['080', '22'],
              29:['620', '14'],
              
              30:['490', '33'],
              31:['520', '18'],
              32:['101', '0'],
              33:['621', '11'],
              34:['107', '-78'],
              
              35:['280', '38'],
              36:['400', '16'],
              37:['590', '15'],
              38:['410', '60'],
              39:['700', '-1'],
              
              40:['090', '15'],
              41:['330', '6'],
              42:['540', '20'],
              43:['410', '62'],
              44:['400', '60'],

              45:['520', '20'],
              46:['440', '62'],
              47:['590', '38'],
              48:['=0', '=0'],
              49:['=0', '=0'],
              
              50:['670', '10'],
              51:['900', '256'],
              52:['290', '25'],
              53:['670', '8'],
              54:['680', '0'],
              
              55:['175', '512'],
              56:['090', '59'],
              57:['350', '3'],
              58:['280', '61'],
              59:['620', '30'],
              
              60:['620', '13'],
              61:['403', '0'],
              62:['590', '50'],
              63:['590', '0']}

#%% Sector 10: Post Mortems

     BS[10] = {0:['=-3', '=410'],
               1:['=614', '=409'],
               2:['=0', '=10'],
               3:['=0', '=10'],
               4:['625', '0'],
               
               5:['101', '-2'],
               6:['172', '-9'],
               7:['182', '21'],
               8:['620', '28'],
               9:['590', '50'],
               
               10:['620', '26'],
               11:['105', '3'],
               12:['102', '8'],
               13:['680', '0'],
               14:['=-24', '=667'],
               
               15:['=508', '=429'],
               16:['102', '13'],
               17:['101', '6'],
               18:['670', '6'],
               19:['410', '18'],
               
               20:['400', '0'],
               21:['520', '2'],
               22:['091', '28'],
               23:['590', '50'],
               24:['=931', '=330'], #This is 10^12   MSByte    X

               25:['=324', '=0'],   #                  X     LSByte
               26:['320', '76'],
               27:['620', '15'],
               28:['290', '10'],
               29:['620', '11'],
               
               30:['167', '-1'],
               31:['380', '11'],
               32:['400', '16'],
               33:['522', '-2'],
               34:['410', '16'],
               
               35:['322', '-1'],
               36:['290', '41'],
               37:['532', '-2'],
               38:['440', '18'],
               39:['490', '32'],
               
               40:['400', '16'],
               41:['332', '-2'],
               42:['132', '11'],
               43:['090', '35'],
               44:['520', '0'],
               
               45:['410', '0'],
               46:['280', '48'],
               47:['400', '14'],
               48:['520', '14'],
               49:['440', '18'],
               
               50:['105', '543'],
               51:['125', '177'],
               52:['451', '4'],
               53:['490', '51'],
               54:['441', '4'],
               
               55:['125', '464'],
               56:['090', '55'],
               57:['175', '906'],
               58:['180', '4'],
               59:['620', '1'],
               
               60:['187', '6'],
               61:['=0', '=0'],
               62:['=0', '=0'],
               63:['=0', '=0']}
#%% Sector 11: Function Table
     
     BS[11] = {0:['=0', '=0'],
               1:['=0', '=0'],
               2:['=0', '=0'],
               3:['=0', '=0'],
               4:['=0', '=0'],
               
               5:['=0', '=0'],
               6:['=0', '=0'],
               7:['=0', '=0'],
               8:['=0', '=0'],
               9:['=0', '=0'],
               
               10:['=0', '=0'],
               11:['=0', '=0'],
               12:['=0', '=0'],
               13:['=0', '=0'],
               14:['=0', '=0'],
               
               15:['=0', '=0'],
               16:['=0', '=0'],
               17:['=0', '=0'],
               18:['=0', '=0'],
               19:['=0', '=0'],
               
               20:['=0', '=0'],
               21:['=0', '=0'],
               22:['=0', '=0'],
               23:['=0', '=0'],
               24:['=0', '=0'],
               
               25:['=0', '=0'],
               26:['=0', '=0'],
               27:['=0', '=0'],
               28:['=0', '=0'],
               29:['=0', '=0'],
               
               30:['=0', '=0'],
               31:['=0', '=0'],
               32:['=0', '=0'],
               33:['=0', '=0'],
               34:['=0', '=0'],
               
               35:['=0', '=0'],
               36:['=0', '=0'],
               37:['=0', '=0'],
               38:['=0', '=0'],
               39:['=0', '=0'],
               
               40:['=0', '=0'],
               41:['=0', '=0'],
               42:['=0', '=0'],
               43:['=0', '=0'],
               44:['=0', '=0'],
               
               45:['=0', '=0'],
               46:['=0', '=0'],
               47:['=0', '=0'],
               48:['=0', '=0'],
               49:['=0', '=0'],
               
               50:['=0', '=0'],
               51:['=0', '=0'],
               52:['=0', '=0'],
               53:['=0', '=0'],
               54:['=0', '=0'],
               
               55:['=0', '=0'],
               56:['=0', '=0'],
               57:['=0', '=0'],
               58:['=0', '=0'],
               59:['=0', '=0'],
               
               60:['207', '-196'],
               61:['670', '8'],
               62:['680', '0'],
               63:['590', '60']}
           
#%% Sector 12: Fault Printing ; Manually parsed, not tested
              #R 99: FAULT PRINTING
              #Brought to page 0 and enetered at line 13 from sector 38
              
    BS[12] = {0:['=0', '=30'],  #((10
              1:['=13', '=30'],
              2:['=27', '=6'],
              3:['=1', '=21'],
              4:['=12', '=20'],
              
              5:['=0', '=14'],  #(12
              6:['626', '0'],   #(16  Punch character in B6 to tape
              7:['600', '8+'],#7:['600', '0+v7'], Tape character to CS 7
              8:['106', '0'],   #(7  #Save the character in B6
              9:['176', '30'],       #Save difference with 30 in Btest
              
              10:['080', '6'],  #     10:['080', 'v16'], Return to 6 if it is not CR character
              11:['300', '5'], #   11:['300', 'v/29'], see page 78 of Annotated IR
              12:['680', '0'],
              13:['210', '24+'],#     13:['210', '0+v5'],
              14:['106', '-12'], #    14:['106', 'v10n12'], This is relative to lavel (12, to punch "FAULT".
              
              15:['636','5+'],  #(3   15:['636','v12'],
              16:['186','15'],  #     16:['186','v3'],
              17:['200','24+'], #     17:['200','0+v5'],
              18:['670','35'],
              19:['680','12'],
              
              20:['101','24'], #      20:['101','v5'],
              21:['590','12.0'],
              22:['=0,','=0'],   #(8
              23:['=0,','=0'],
              24:['300','0'],    #(5
              
              25:['670','127'],
              26:['680','15'],
              27:['006','+2.33'],  # 27:['006','1+v/1'], page 2, line 33
              28:['620','14'],
              29:['990','0'],
              
              30:['370','9'],
              31:['280','9'],  #   31:['280','1v7'],
              32:['010','15.57'],
              33:['690','15'],
              34:['300','11.1'],  # 34:['300','1v/53'], page 11, line 1
              
              35:['590','12'],
              36:['400','22'],   #(1    36:['400','v8'],
              37:['417','-2'],
              38:['380','37'],  #      38:['380','-1*'],
              39:['300','-14'],
              
              40:['620','30'],
              41:['620','13'],
              42:['380','41'], #      42:['380','-1*'],
              43:['176','0'],
              44:['080','51'], #      44:['080','v2'],
              
              45:['300','40'],
              46:['210','53'],  #   46:['210','1v14'],
              47:['300','-63'],
              48:['677','127'],
              49:['690','31'],
              
              50:['380','48'], #     50:['380','-2*'],
              51:['300','-383'],  #(2
              52:['677','511'],   #(14
              53:['570','31'],
              54:['146','64'],
              
              55:['090','57'], #     55:['090','2*'],
              56:['620','0'],
              57:['380','52'],#     57:['380','v14'],
              58:['670','128'],
              59:['680','1'],
              
              60:['300','6'],
              61:['670','38'],
              62:['590','12'],
              63:['590','36']} #    63:['590','v1']}
      
#%% Sector 13: Chapter 1 (S13-S25)(R40,R7,R8,R6,R1,R3)
# occupies pages 1-14
# other chapter occupies pages 11-13

              #R 40 (Fault 13)
     BS[13] = {0:['',''],  #Number +101
               1:['',''],
               2:['300','13'],  #(1  Fault 13 detected
               3:['590','9'],  #To punch "fault 13"

              #R 7 (Build exact number in the Accumulator)
               4:['400','0'],
               
               5:['103','v1'],
               6:['520','16'],  #(1
               7:['440','14'],
               8:['590','v/1'], #Return to read

              #R 8 (Halve or double the contents of the
              # Accumulator according to function type
              
               9:['300','0'],
               
               10:['207','v1'],  #(3
               11:['727','0'],
               12:['717','0'],
               13:['591','0'],
               14:['=29','=0'],
               
               15:['=0','=0'],  #((1
               16:['=1','=0'],  # Table: double for types 2,5
               17:['=-1','=1'], # halve for type 4
               18:['=0','=0'],  #
               
              #R 6 (CR, ), fi? and LF entries. Start item
               19:['104','v1'],
               
               20:['592','0'],
               21:['172','v/37'],   #(2
               22:['080','v/19'],
               23:['033','0+v3/39'],
               24:['173','v5/39'],
               
               25:['080','v/19'],  #(3
               26:['103','v/9'],   #(1
               27:['010','0+v/84'],
               28:['010','0+v/18'],
               29:['400','0'],
              
               30:['410','50'],
               31:['102','v/1'],
               
               #R 1 (Read character X)
               32:['600','1+v'],
               33:['106','0'],
               34:['206','v/15'],
               
               35:['172','v/1'],
               36:['290','v2'],
               37:['597','0'],
               38:['370','10'],  #(2
               39:['297','0'],
              
               40:['210','15+'],
               41:['593','0'],
               42:['670','46'],  #(1
               43:['680','15'],  
               44:['590','v/81'],

               #R 3 (n and v entries)
               45:['330','511'],
               46:['330','1v'],
               47:['210','0+v2'],
               48:['101','v1'],
               49:['290','v/24'],
              
               50:['172','v/1'],
               51:['080','v/25'],
               52:['670','37'],
               53:['680','11'],
               54:['590','v/71'],
              
               55:['104','v2'],  #(1
               56:['592','0'],
               57:['300','0'],   #(2
               58:['210','0+v1/23'],
               59:['102','v/23'],
              
               60:['400','0'],  #(3
               61:['103','v/7'],
               62:['590','v/1'],
               63:['=0','=0']}

#%% Sector 14: Chapter 1 (R80,R10,R12)

               #R 80 (L,P or S on right hand side of an equation)
    BS[14] = {0:['181','v1'],
              1:['590','v/19'],
              2:['271','2v5/81'],  #(1
              3:['280','v'],
              4:['171','511'],
              
              5:['090','v9/81'],
              6:['015','0+v4'],
              7:['104','v2'],
              8:['592','0'],
              9:['006','0+v1/31'],  #(2
              
              10:['026','47'],
              11:['406','0'],
              12:['410','44'],
              13:['102','v3'],
              14:['590','v3/3'],
              
              15:['173','v/7'],   #(3
              16:['080','v/19'],
              17:['105','0'],     #(4
              18:['205','63'],
              19:['175','-3'],
              
              20:['080','v5'],
              21:['210','25+'],
              22:['200','62'],
              23:['210','27'],
              24:['400','26'],
              
              25:['440','24'],
              26:['590','21v/34'],
              27:['210','23'],   #(5
              28:['400','22'],
              29:['590','21v/34'],
              
             #R 10 (W, -> entries)
              30:['106','750'], #(0
              31:['300','-16'], #(1
              32:['380','*'],
              33:['580','0'],   #(2
              34:['186','v1'],
              
              35:['300','648'],
              36:['260','v2'],
              37:['210','v2'],
              38:['610','1+*'],
              39:['106','0'],  #(4
              
              40:['166','0'],  #(5
              41:['090','-1v1'],
              42:['006','0+v4'],
              43:['016','0+v3'],
              44:['090','v/1'],
              
              45:['590','v'], #goes to v0
              
              #R 12 (+ and - entries)
              46:['300','-1'],  #minus entry
              47:['210','0+v/84'],
              48:['300','2v'],
              49:['320','-3nv6'], #plus entry
              
              50:['080','v1'],
              51:['590','v/39'],
              52:['210','1+*'],  #(1
              53:['072','v6'],
              54:['370','v7'],
              
              55:['080','v2'],
              56:['177','512v6'],
              57:['090','v2/56'],
              58:['173','v1/7'],
              59:['080','4v1/13'],
              
              60:['176','26'],
              61:['080','v/19'],
              62:['290','v/19'],
              63:['440','20']}

#%% Sector 15: Chapter 1 (R12,R14,R15,R18)

     BS[15] = {0:['103','v/19'],
               1:['590','v/1'],
               2:['380','v1'], #(2
               3:['590','v/19'],
               4:['=v/57','=v/32'],  #(6
               
               5:['=v2/64','=v1/49'],
               6:['=v/31','=v2/38'], #(7
               
              #R 14 (. entry)
               7:['172','v2/50'],
               8:['080','v3'],
               9:['450','30'],
               
               10:['490','v4'],
               11:['590','v/19'],
               12:['440','30'],  #(4
               13:['590','v/1'],
               14:['173','v/7'], #(3
               
               15:['080','v1'],
               16:['590','v/1'],
               17:['173','v1/7'], #(1
               18:['080','v2'],
               19:['707','6'],
               
               20:['717','0'],
               21:['410','50'],
               22:['400','0'],    #(5
               23:['590','v/1'],
               24:['172','v/37'], #(2
               
               25:['080','v/19'],
               26:['590','v4/39'],
               
              #R 15 (Figure Shift table)
               27:['=v3/6','=1'],
               28:['=2','=v/35'],
               29:['=4','=v/5'],
               30:['=v2/6','=7'],
               
               31:['=8','=2v/13'],
               32:['=1v/13','=v/12'],
               33:['=1v/3','=v3/6'],
               34:['=v/1','=v/30'],
               
               35:['=0','=v/13'],
               36:['=1v/80','=3'],
               37:['=v/10','=5'],
               38:['=6','=v5/17'],
               39:['=v/2','=9'],
               
               40:['=3v/12','=v1/1'],
               41:['=v/14','=v/3'],
               42:['=v/6','=v/1'],
               
              #R 18 (Overflow - enter with the overflow in SAC)
               43:['100','0'],
               44:['080','v4'],
               
               45:['006','0+v/8'],
               46:['176','5'],
               47:['080','v4'],
               48:['370','2'],
               49:['290','v1'],
               
               50:['370','-2'],
               51:['290','v2'],
               52:['300','2'],   #(1
               53:['590','9'],
               54:['350','1'],   #(2
               
               55:['280','v3'],
               56:['591','0'],
               57:['006','61+'], #(3
               58:['206','63+'],
               59:['320','512'],
               
               60:['216','63+'],
               61:['591','0'],
               62:['370','0'],  #(4
               63:['280','v5']}

#%% Sector 16: Chapter 1 (R18,R2,R24,R25,R17,R26)               
      BS[16] = {0:['591','0'],
                1:['370','-1'], #(5
                2:['280','v1'],
                3:['591','0'],
                
              #R 2 (X entry)
                4:['172','v/34'],
                
                5:['080','2*'],
                6:['590','v2'],
                7:['172','v/31'],
                8:['080','v1'],
                9:['104','v3'],   #(2
                
               10:['592','0'],
               11:['102','v/34'], #(3
               12:['590','v3/3'],
               13:['102','v/22'], #(5
               14:['590','v3/3'],
               
               15:['104','v5'],   #(1
               16:['101','1v2'],
               
               #R 24 (Separate v= , x=)
               17:['172','v/1'],
               18:['080','v/25'],
               19:['106','!=24.44'],
               
               20:['171','v1/3'],
               21:['080','v1'],
               22:['106','!=27.54'],
               23:['016','0+v1/31'], #(1
               24:['102','v/31'],
               
               25:['590','v3/3'],
               
               #R 25 (Test v, n, x or * O.K.)
               26:['300','v8/5'],
               27:['210','1+*'],  #(2
               28:['072','v8/5'],
               29:['370','1v9/5'],
               
               30:['380','v4'],
               31:['590','v/19'],
               32:['080','v2'],  #(4
               33:['591','0'],
               
               #R 17 (/ entry)
               34:['300','-1'],  #(1
               
               35:['210','0+v/33'],
               36:['590','v5/14'],
               37:['300','5'],  #(2
               38:['230','0+v/8'],
               39:['290','v/19'],
               
               40:['370','-1'],
               41:['280','v3'],
               42:['172','v/32'],
               43:['080','v6'],
               44:['210','0+v/23'],  #(4
               
               45:['300','256'],
               46:['210','0+v2/3'],
               47:['010','43'],
               48:['200','0+v/8'],
               49:['210','44+'],
               
               50:['104','v2/3'],
               51:['592','0'],
               52:['172','v/22'],  #(6
               53:['080','v/19'],
               54:['590','v4'],
               
               55:['172','v2/64'], #(3
               56:['187','v/19'],
               57:['590','v4'],
               58:['172','v/23'],  #(5
               59:['080','v2'],
               
               60:['101','v1'],
               
               #R 26 (Destandarize and store label number)
               # (Entered with l in the accumulator)
               61:['440','28'],
               62:['410','40'],
               63:['200','41']}

#%% Sector 17: Chapter 1 (R26,R23,R27)
      BS[17] = {0:['220','0+v/8'],
                1:['210','44+'],
                2:['440','18'],
                3:['410','42'],
                4:['591','0'],
                
               #R 23 (Terminate v or n Reference)
                5:['100','0'],
                6:['080','v3'],
                7:['101','v2'],
                8:['590','v/26'],
                9:['200','63'],  #(2
                
               10:['590','v4'],
               11:['010','0+v'], #(3
               12:['440','18'],
               13:['410','40'],
               14:['200','41'],
               
               15:['210','44'], #(4
               16:['006','61+'],
               17:['136','1'],
               18:['306','0'],  #(1
               19:['210','45'],
               
               20:['200','62+'],
               21:['210','45+'],
               22:['101','v5'],
               23:['200','0+v/8'],
               24:['370','6'],
               
               25:['280','v/28'],
               26:['590','v2/63'],
               27:['200','0+v/8'],  #(5
               28:['370','7'],
               29:['290','11.63'],
               
               30:['700','0'],
               31:['080','v7'],
               32:['006','60+'],
               33:['300','7'],
               34:['176','!=8.44'], #maybe 5.44
               
               35:['090','9'],
               36:['400','44'],
               37:['416','16.0'],
               38:['126','1'],
               39:['016','60+'],
               
               40:['594','0'],  #(6
               41:['410','42'], #(7
               42:['101','v6'],
               
              #R 27 (Fill in Reference)
               43:['011','0+v6'],
               44:['200','43'],
               
               45:['210','23'],
               46:['007','43+'],
               47:['350','15'],
               48:['210','23+'],
               49:['400','22'],
               
               50:['010','23+'],
               51:['090','v2'],
               52:['440','20'],
               53:['101','v4'],  #(2
               54:['200','44+'],
               
               55:['350','7'],
               56:['370','3'],
               57:['280','v3/8'],
               58:['006','43+'],
               59:['156','224'],
               
               60:['176','32'],
               61:['300','4'],
               62:['080','v3'],
               63:['590','v3/8']}

#%% Sector 18: Chapter 1 (R27,R28)      
      BS[18] = {0:['176','96'],  #(3
                1:['080','v4'],
                2:['380','v3/8'],
                3:['006','45'],  #(4
                4:['090','3*'],
                
                5:['440','v1/8'],
                6:['520','2'],
                7:['156','127'],
                8:['206','1.0'],
                9:['210','23'],
                
               10:['440','22'],
               11:['440','18'],
               12:['410','40'],
               13:['200','41'],
               14:['216','1.0'],
               
               15:['200','44+'],
               16:['350','7'],
               17:['370','5'],
               18:['280','v6'],
               19:['200','41+'],
               
               20:['350','1'],
               21:['280','v5'],
               22:['590','v6'],
               23:['206','63+'],  #(5
               24:['320','512'],
               
               25:['216','63+'],
               26:['519','0'],    #(6
               
              #R 28 (Locate label)
               27:['006','44'],
               28:['076','63'],
               29:['080','v1'],
               
               30:['200','43'],
               31:['370','101'],
               32:['290','v5'],
               33:['407','27.54'],
               34:['410','42'],
               
               35:['591','0'],
               36:['300','-5'],  #(1
               37:['146','0'],   #(2
               38:['380','v2'],
               39:['126','96'],
               
               40:['676','0'],
               41:['680','15'],
               42:['006','44'],
               43:['026','44'],
               44:['156','126'],
               
               45:['206','15.0+'],
               46:['280','v3'],
               47:['400','38'],  #(5
               48:['591','0'],
               49:['206','15.0'],#(3
               
               50:['102','-4'],
               51:['340','0'],   #(4
               52:['182','v4'],
               53:['320','64'],
               54:['210','59+'],
               
               55:['677','0'],
               56:['680','31'],
               57:['206','15.0'],
               58:['350','31'],
               59:['002','44'],
               
               60:['006','43'],
               61:['407','31.0'],  #(7
               62:['410','42'],
               63:['072','42']}

#%% Sector 19: Chapter 1 (R28,R20,R4,R36)    
      BS[19] = {0:['080','v5'],
                1:['076','42+'],
                2:['080','v6'],
                3:['591','0'],
                4:['370','31'],  #(6
                
                5:['380','v7'],
                6:['200','59+'],
                7:['320','1'],
                8:['210','59+'],
                9:['677','0'],
                
                10:['680','31'],
                11:['300','0'],
                12:['590','v7'],
                
               #R 20: Inspect h
                13:['006','61+'],
                14:['126','1'],
                
                15:['156','-2'],
                16:['306','0'],
                17:['350','2'],
                18:['280','v2'],
                19:['590','v3'],
                
                20:['300','776'], #(2
                21:['216','1.0'],
                22:['126','2'],
                23:['016','61+'], #(3
                24:['176','128'],
                
                25:['081','0'],
                26:['200','62+'],
                27:['370','126'],
                28:['380','v5'],
                29:['006','63+'],
                
                30:['176','127'],
                31:['080','v5'],
                32:['590','-2v4'],
                33:['677','-1'], #(5
                34:['690','1'],
                
                35:['210','62+'],
                36:['677','0'],
                37:['680','1'],
                38:['200','62'],
                39:['320','1'],
                
                40:['210','62'],
                41:['006','58+'],
                42:['076','62'],
                43:['090','2*'],
                44:['210','58+'],
                
                45:['106','0'],
                46:['016','61+'],
                47:['370','16'],
                48:['280','v3'],
                49:['300','8'],
                
                50:['590','9'],
                51:['006','61+'], #(4
                52:['126','1'],
                53:['156','-2'],
                54:['590','v3'],
                
               #R 4: Plant ten-bit word from SAC
                55:['006','61+'],
                56:['216','1.0'],
                57:['126','1'],
                58:['016','61+'],
                59:['591','0'],
                
               #R 36: Terminate *
                60:['173','v/7'],
                61:['080','v/19'],
                62:['101','v2/11'],
                63:['011','0+v6/27']}

#%% Sector 20: Chapter 1 (R36,R33,R5,R13)
       BS[20] = {0:['101','-1v1/22'],
                 1:['200','0+v/8'],
                 2:['330','7'],
                 3:['290','v1/33'],
                 
                #R 33: Calculate *; plant x0
                 4:['300','-1'],
                 
                 5:['000','0+v/18'],
                 6:['080','v1'],
                 7:['300','-2'],
                 8:['220','61+'], #(1
                 9:['590','v1/11'],
                 
                10:['400','42'],  #(2
                11:['410','24.44'],
                12:['590','v/29'],
                
               #R 5: ( entry
                13:['080','v1'],
                14:['670','40'],
                
                15:['680','11'],
                16:['590','v1/73'],
                17:['000','61'],  #(1
                18:['300','v7'],
                19:['080','v11'], #(4
                
                20:['590','v5'],
                21:['=v2/64','=v1/49'], #((8
                22:['=v/32','=v/23'],   #((7
                23:['=v/22','=v/11'],
                24:['=v/36','=v/37'],   #((9
                
                25:['=v2/38','=v3/68'], #(3
                
                26:['210','0+v2'], #(11
                27:['072','v7'],   #(2
                28:['370','v3'],
                29:['380','v4'],
                
                30:['080','v/19'],
                31:['104','v6'],  #(5
                32:['592','0'],
                33:['102','v/11'],#(6
                34:['590','v3/3'],
                
               #R 13: >, =, != entries
                35:['320','2'],
                36:['330','2'],
                37:['320','2n'],
                38:['006','0+v/8'],
                39:['172','v/1'],
                
                40:['210','0+v/8'],
                41:['080','v1'],
                42:['006','61+'],
                43:['101','v3'],
                44:['590','v3/20'],
                
                45:['300','1'], #(3
                46:['210','0+v/18'],
                47:['300','3'],
                48:['210','61'],
                49:['102','v/32'],
                
                50:['590','v3/3'],
                51:['172','v/32'], #(1
                52:['080','v2'],
                53:['176','6'],
                54:['090','v/19'],
                
                55:['173','v/7'],
                56:['080','v/19'],
                57:['590','v/1'],
                58:['172','v/31'], #(2
                59:['080','v/19'],
                
                60:['450','v/40'],
                61:['490','v1/40'],
                62:['440','v/40'],
                63:['440','18']}

#%% Sector 21: Chapter 1 (R13,R11,R30,R38,R37)
       BS[21] = {0:['410','46'],
                 1:['590','v3/3'],
                 
                #R 11: Terminate Label Set by (
                 2:['450','v/40'],
                 3:['490','v1/40'],
                 4:['440','v/40'],
                 
                 5:['440','18'],
                 6:['410','40'],
                 7:['200','61+'],
                 8:['006','61'],
                 9:['236','32'],
                 
                10:['101','v3'],
                11:['210','25+'], #(1
                12:['400','24'],
                13:['200','62'],
                14:['210','27'],
                
                15:['440','26'],
                16:['171','-1v1/22'],
                17:['080','2*'],
                18:['590','v/8'],
                19:['440','18'],
                
                20:['410','42'],
                21:['200','63'],
                22:['210','42'],
                23:['206','35'],
                24:['220','42+'],
                
                25:['220','43+'],
                26:['330','384'],
                27:['210','43+'],
                28:['591','0'],
                29:['006','41'], #(3
                
                30:['016','42+'],
                31:['406','27.54'],
                32:['900','0'],
                33:['107','4'], #(4
                34:['280','9'],
                
                35:['400','42'],
                36:['416','27.54'],
                37:['594','0'], #(2
                
               #R 30: , entry
                38:['172','v/37'],
                39:['080','v/6'],
               
               #R 38: Read decimal exponent
                40:['101','v1'],
                41:['590','v/84'],
                42:['410','40'], #(1
                43:['102','v2'],
                44:['590','v3/3'],
                
                45:['101','v3'], #(2
                46:['590','v/84'],
                47:['440','18'], #(3
                48:['410','42'],
                49:['200','0+v2/39'],
                
                50:['220','43'],
                51:['210','0+v2/39'],
                52:['400','40'],
               
               #R 37: terminate number
                53:['101','v1'],
                54:['590','v/84'],
                
                55:['410','40'], #(1
                56:['200','0+v2/39'],
                57:['280','v2'],
                58:['590','v9'],
                59:['290','v5'], #(2
                
                60:['320','1'],
                61:['400','48'],
                62:['590','v4'],
                63:['500','48']} #(3

#%% Sector 22: Chapter 1 (R37,R9,R34)       
       BS[22] = {0:['380','v3'], #(4
                 1:['590','v8'],
                 2:['300','1'],  #(5
                 3:['230','0+v2/39'],
                 4:['400','16'],
                 
                 5:['590','v7'],
                 6:['520','16'], #(6
                 7:['380','v6'], #(7
                 8:['520','40'], #(8
                 9:['006','61+'],#(9
                 
                10:['306','4'],
                11:['210','61+'],
                12:['146','0'],
                13:['146','0'],
                14:['416','1.0'],
                 
                15:['594','0'],
                
               #R 9: Function and b-digits
                16:['102','v/19'],
                17:['106','2'],
                18:['016','61'],
                19:['210','0+v1'],
                
                20:['327','0'],
                21:['327','0'], #(1
                22:['327','0'],
                23:['210','0+v2'],
                24:['101','v/1'],
                
                25:['103','v2'],
                26:['590','v4/20'],
                27:['320','0'], #(2
                28:['207','v/16'],
                29:['210','0+v3'],
                
                30:['350','7'],
                31:['210','0+v/8'],
                32:['300','0'], #(3
                33:['350','-8'],
                34:['210','0+v4'],
                
                35:['103','v4'],
                36:['590','v/1'],
                37:['320','0'], #(4
                38:['101','v3/3'],
                39:['010','0+v/18'], #(5
                
                40:['102','v/32'],
                41:['590','v/4'],
                
               #R 34: Terminate and Fill in Preset Parameter
               # on the Right Hand Side of an Equation.
                42:['440','18'],
                43:['410','40'],
                44:['006','41'],
                
                45:['406','24.44'],
                46:['410','42'],
                47:['200','43+'],
                48:['280','3*'],
                49:['300','6'],
                
                50:['590','9'],
                51:['006','0+v1/31'],
                52:['026','47'],
                53:['406','0'],
                54:['410','44'],
                
                55:['200','43'],
                56:['210','23'],
                57:['007','43+'],
                58:['350','15'],
                59:['210','23+'],
                
                60:['400','22'],
                61:['090','2*'],
                62:['440','20'],
                63:['101','2*']}

#%% Sector 23: Chapter 1 (R34,R39,R31)   
       BS[23] = {0:['590','v/8'],
                 1:['200','45'],
                 2:['210','23'],
                 3:['200','45+'],
                 4:['350','15'],
                 
                 5:['210','23+'],
                 6:['440','22'],
                 7:['010','23+'],
                 8:['200','45+'],
                 9:['290','2*'],
                 
                10:['440','20'],
                11:['440','18'],
                12:['410','40'],
                13:['200','41'],
                14:['210','45'],
                
                15:['200','45+'],
                16:['350','480'],
                17:['220','40+'],
                18:['220','41+'],
                19:['330','384'],
                
                20:['210','45+'],
                21:['400','44'],
                22:['006','0+v1/31'],
                23:['026','47'],
                24:['416','0'],
                
                25:['594','0'],
                
              #R 39: Number Input
                26:['010','0+v2'],
                27:['010','0+v3'],
                28:['106','1'],
                29:['016','61'],
                
                30:['101','v/1'],
                31:['400','0'], #(1
                32:['103','v5'],
                33:['102','v/37'],
                34:['590','v/20'],
                
                35:['103','v2'], #(5
                36:['106','0'],  #(2
                37:['126','0'],  #(3
                38:['016','0+v2'],
                39:['520','16'],
                
                40:['440','14'],
                41:['590','v/1'],
                42:['300','-1'], #(4
                43:['310','0+v3'],
                44:['590','v/1'],
                
              #R 31: Terminate Absolute Part of Right Hand Side of Equation
                45:['300','-1'],
                46:['210','0+v/18'],
                47:['590','v/32'],
                48:['106','0'],  #(1
                49:['026','47'],
                
                50:['300','4'],
                51:['176','379'],
                52:['090','1v3'],
                53:['406','0'],
                54:['410','42'],
                
                55:['000','43+'],
                56:['080','9'],
                57:['200','63'], #(3
                58:['210','42'],
                59:['200','47'],
                
                60:['210','42+'],
                61:['200','41'],
                62:['210','43'],
                63:['200','41+']}
       
#%% Sector 24: Chapter 1 (R31,R16)
       BS[24] = {0:['350','15'],
                 1:['320','128'],
                 2:['220','40+'],
                 3:['210','43+'],
                 4:['400','42'],
                 
                 5:['416','0'],
                 6:['594','0'],
       
              #R 16 (Function Table)
                 7:['=192', '=128'],
                 8:['=448', '=81'],
                 9:['=400', '=87'],
                 
                10:['=264', '=21'],
                11:['=286', '=0'],
                12:['=12', '=0'],
                13:['=333', '=277'],
                14:['=325', '=365'],
                
                15:['=357', '=349'],
                16:['=341', '=373'],
                17:['=57', '=129'],
                18:['=75', '=27'], # 75,512 in handwritten version
                19:['=67', '=107'],
               
                20:['=99', '=91'],
                21:['=83', '=115'], 
                22:['=121', '=512'],
                23:['=461', '=405'],
                24:['=453', '=493'],
                
                25:['=485', '=477'],
                26:['=469', '=501'],
                27:['=185', '=257'],
                28:['=203', '=539'], #203, 512 in HWV
                29:['=195', '=235'],
                
                30:['=227', '=219'],
                31:['=211', '=243'],
                32:['=249', '=512'],
                33:['=268', '=284'],
                34:['=292', '=300'],
                
                35:['=308', '=316'],
                36:['=820', '=828'],
                37:['=393', '=137'],
                38:['=420', '=428'],
                39:['=436', '=444'],

                40:['=180', '=52'],
                41:['=512', '=776'],
                42:['=384', '=9'],
                43:['=21', '=149'],
                44:['=681', '=170'],

                45:['=412', '=512'],
                46:['=512', '=33'],
                47:['=161', '=41'],
                48:['=584', '=152'],
                49:['=576', '=616'],

                50:['=608', '=600'],
                51:['=592', '=624'],
                52:['=800', '=512'],
                53:['=689', '=673'], #697, 673 in HWV
                54:['=553', '=544'],

                55:['=512', '=512'],
                56:['=908', '=897'],
                57:['=649', '=641'],
                58:['=712', '=760'],
                59:['=704', '=744'],

                60:['=736', '=728'],
                61:['=720', '=752'],
                62:['=512', '=0'],
                63:['=0', '=0']}
     
#%% Sector 25: Chapter 1 (R32,R84,R35,R22)
               #R 32
      BS[25] = {0:['101','3'],   #  0:['101','v1'], return address from R84
                1:['440','50'],  #  add any stored part of absolute address (e.g. page number)
                2:['590','22'],# 2:['590','v/84'], to adjust absolute address for sign  
                3:['101','5'],  #(1  3:['101','v2'], #* to halve or double according to type
                4:['590','v/8'],#    4:['590','v/8'],                      
                
                5:['440','18'],  #(2  destandarize and plant absolute address
                6:['410','40'],
                7:['400','0'],
                8:['410','50'],
                9:['000','0+v/18'],
                
               10:['090','2*'],
               11:['590','v1/31'],
               12:['000','40+'],
               13:['300','1'],
               14:['080','9'],
               
               15:['200','41+'],
               16:['330','384'],
               17:['101','v3'],
               18:['280','v/18'],
               19:['200','41'],  #(3
               
               20:['101','v2/11'],
               21:['590','v/4'],
               
               #R 84
               22:['100','0'],
               23:['091','0'],
               24:['520','2'],
               
               25:['010','0+v'],
               26:['591','0'],
               
               #R 35
               27:['080','v1'],
               28:['000','58'],
               29:['090','v/19'],
               
               30:['010','58'],
               31:['590','v/1'],
               32:['104','v3'],    #(1
               33:['101','1v1/3'],
               34:['590','v/25'],
               
               35:['102','v/36'],  #(3
               36:['590','v3/3'],
               
               #R 22
               37:['440','18'],
               38:['410','40'],
               39:['006','41'],
               
               40:['406','24.44'],
               41:['410','42'],
               42:['200','43+'],
               43:['101','v2/11'],
               44:['280','v1'],
               
               45:['300','6'],
               46:['590','9'],
               47:['100','0'],
               48:['200','0+v/8'],  #(1
               49:['370','7'],
               
               50:['280','v2'],
               51:['080','11.63'],
               52:['440','18'],
               53:['410','42'],
               54:['200','42+'],
               
               55:['220','43+'],
               56:['210','43+'],
               57:['590','11.63'],
               58:['210','44+'],  #(2
               59:['200','61+'],
               
               60:['330','1'],
               61:['210','45'],
               62:['080','v/27'],
               63:['590','v4/27']}

#%% Sector 26: Chapter 2 (R53)
               #R 53
      BS[26] = {0:['102','v/59'],
                1:['006','63+'],
                2:['080','2*'],
                3:['590','v8'],
                4:['176','127'],
                
                5:['090','v/19'],
                6:['670','28'],
                7:['680','13'],
                8:['101','26'],
                9:['010','0+v17/51'],
                
               10:['590','v4/51'],
               11:['670','113'],  #(1
               12:['006','63+'],
               13:['176','64'],
               14:['090','2*'],
               
               15:['670','112'],
               16:['680','15'],
               17:['200','57'],  #(11
               18:['280','v3'],
               19:['300','58+'],  #300????
               
               20:['210','57'],
               21:['270','58+'],  #(3
               22:['290','v4'],
               23:['300','9'],
               24:['590','9'],
               
               25:['101','v1'],  #(5
               26:['590','2v8'],
               27:['270','62'],  #(4
               28:['280','v5'],
               29:['200','62+'],
               
               30:['026','63+'],
               31:['156','126'],
               32:['226','15.0+'],
               33:['230','62'],
               34:['216','15.0'],
               
               35:['206','15.0+'],
               36:['105','-4'],
               37:['327','0'],   #(7
               38:['185','v7'],
               39:['220','62'],
               
               40:['216','15.0+'],
               41:['690','15'],
               42:['010','62'],  #(8
               43:['101','v9'],
               44:['106','128'],
               
               45:['590','v3/20'],
               46:['010','57'],  #(9
               47:['017','58+'],
               48:['670','30'],
               49:['680','12'],
               
               50:['172','v/1'],
               51:['080','11.61'],
               52:['101','v10'],
               53:['590','v/54'],
               54:['670','33'],  #(10
               
               55:['680','12'],
               56:['102','v/55'],
               57:['590','v3/3'],
               58:['=0','=0'],
               59:['=0','=0'],
               
               60:['=0','=0'],
               61:['670','29'],
               62:['680','11'],
               63:['590','v1']}

#%% Sector 27: Chapter 2 (R51)
               #R 51
      BS[27] = {0:['011','0+v23'],  #(1
                1:['017','0+v3'],
                2:['300','-31'],
                3:['400','38'],
                4:['417','31.62'],
                
                5:['380','-1*'],
                6:['105','0'],
                7:['200','62+'],  #(24
                8:['677','0'],
                9:['690','1'],
                
               10:['590','v9'],
               11:['101','v21'],  #(19
               12:['005','47'],
               13:['300','0'],
               14:['175','9'],
               
               15:['080','v/4'],
               16:['300','3'],
               17:['590','v/4'],
               18:['400','42'],  #(21
               19:['415','30.62'],
               
               20:['002','13.0'],
               21:['005','13.0+'],
               22:['590','v24'],
               23:['410','42'],  #(5
               24:['200','45+'],
               
               25:['677','0'],
               26:['680','1'],
               27:['101','v6'],
               28:['590','v/27'],
               29:['690','1'],  #(6
               
               30:['590','v8'],
               31:['176','32'], #(22
               32:['090','9'],
               33:['016','59+'],
               34:['676','64'],
               
               35:['680','31'],
               36:['006','59'],
               37:['156','31'],
               38:['405','27.54'], #(11
               39:['707','0'],
               
               40:['080','v15'],
               41:['175','100'],  #(12
               42:['185','v11'],
               43:['200','59+'],
               44:['105','-4'],
               
               45:['327','0'],  #(13
               46:['185','v13'],
               47:['326','0'],
               48:['210','59'],
               49:['690','31'],
               
               50:['200','62+'],
               51:['677','0'],
               52:['680','1'],
               53:['590','v23'],
               54:['416','31.0'], #(15
               
               55:['400','38'],
               56:['415','27.54'],
               57:['176','31'],
               58:['186','v12'],
               59:['690','31'],
               
               60:['010','59'],
               61:['006','59+'],
               62:['126','1'],
               63:['590','v16']}
      
#%% Sector 28: Chapter 2 (R51)
   
      BS[28] = {13:['670','27'],
                14:['680','12'],
                
                15:['400','27.54'],
                16:['707','0'],
                17:['080','v1'],
                18:['590','11.63'],
                19:['175','300'],  #(17
                
                20:['090','2*'],
                21:['590','v7'],
                22:['700','0'],
                23:['186','v5'],
                24:['670','41'],
                
                25:['680','11'],
                26:['016','47'],
                27:['101','v18/67'],
                28:['011','0+v16/67'],
                29:['012','13.0'],
                
                30:['015','13.0+'],
                31:['200','62+'],
                32:['677','0'],
                33:['680','1'],
                34:['590','v/20'],
                
                35:['670','27'],  #(20
                36:['680','12'],
                37:['300','9'],
                38:['101','v19'],
                39:['590','v/4'],
                
                40:['405','16.0'],  #(2
                41:['410','44'],
                42:['200','44+'],
                43:['350','7'],
                44:['370','6'],
                
                45:['290','v7'],
                46:['006','44+'],
                47:['146','0'],
                48:['146','0'],
                49:['146','101'],
                
                50:['406','31.0'],
                51:['090','v17'],
                52:['200','44'],
                53:['370','0'],  #(3
                54:['280','v7'],
                
                55:['700','0'],
                56:['080','v5'],
                57:['400','44'],  #(7
                58:['300','0'],
                59:['417','16.0'],
                
                60:['320','1'],
                61:['210','1+v7'],
                63:['125','1']}
            
#%% Sector 29: Chapter 3 (R59,R70,Quicky 0)
               #R 59
      BS[29] = {0:['106','127'],
                1:['016','61+'],
                2:['200','57+'],
                3:['210','62+'],
                4:['677','0'],
                
                5:['680','1'],
                6:['101','v2'],
                7:['590','v/63'],
                8:['690','1'],   #(2
                9:['101','v3'],
                
               10:['590','v/54'],
               11:['105','0'],   #(3
               12:['075','60+'], #(6
               13:['080','v4'],
               14:['200','57+'],
               
               15:['677','0'],
               16:['680','1'],
               17:['670','3'],
               18:['680','0'],
               19:['590','59'],
               
               20:['670','35'],  #(4
               21:['680','12'],
               22:['405','16.0'],
               23:['410','44'],
               24:['590','v/46'],
               
               25:['200','45+'], #(5
               26:['101','2*'],
               27:['590','v/47'],
               28:['620','28'],
               29:['200','45'],
               
               30:['350','126'],
               31:['340','0'],
               32:['101','2*'],
               33:['590','v/47'],
               34:['200','45'],
               
               35:['157','1'], #157 can be X57
               36:['185','2*'],
               37:['590','v6'],
               38:['620','26'],
               39:['590','v6'],
               
               #R 70
               40:['102','2*'],
               41:['590','v3/3'],
               42:['440','18'],
               43:['410','40'],
               44:['200','41'],
               
               45:['370','11'],
               46:['290','3*'],
               47:['210','56'],
               48:['590','v/29'],
               49:['300','14'],
               
               50:['590','9'],
               
               #n printing quicky
               51:['=0','=7'],
               52:['=768','>61'],
               53:['670','479'],
               54:['690','0'],
               
               55:['670','43'],
               56:['680','0'],
               57:['210','0+'],
               58:['210','8+'],
               59:['300','8'],
               
               60:['590','v1/72'],
               61:['300','0'],
               62:['=0','=0'],
               63:['592','0']}
           
#%% Sector 30: Chapter 3 (R63,R65,R68,R54)
      BS[30] = {0:['011','0+v1'],
                1:['300','6'],
                2:['210','0+v/8'],
                3:['102','v/32'],
                4:['590','v3/3'],
                
                5:['006','60+'],  #(2
                6:['400','44'],
                7:['416','16.0'],
                8:['126','1'],
                9:['016','60+'],
                
               10:['590','0'],  #(1
                
              #R 65
               11:['670','39'],
               12:['680','11'],
               13:['590','v1/64'],
               14:['210','0+v4'],  #(1
               
               15:['200','51'],
               16:['106','-5'],
               17:['340','0'],
               18:['186','-1*'],
               19:['210','62'],
               
               20:['320','0'],   #(4
               21:['210','62+'],
               22:['677','0'],
               23:['680','1'],
               24:['590','v/29'],
               
               #R 68
               25:['102','v3'],
               26:['590','v3/3'],
               27:['300','4'],   #(3
               28:['210','61'],  #(1
               29:['300','v2'],
               
               30:['210','0+v/6'],
               31:['174','v1/6'],
               32:['084','0'],
               33:['300','v1/6'],  #(2
               34:['210','0+v/6'],
               
               35:['590','v/29'],
               
               #R 54
               36:['670','31'],
               37:['680','13'],
               38:['011','0+v9'],
               39:['105','0'],
               
               40:['590','v10'],
               41:['405','16.0'],   #(1
               42:['410','44'],
               43:['200','44+'],
               44:['350','7'],
               
               45:['370','6'],
               46:['280','v7'],
               47:['200','44+'],
               48:['340','0'],
               49:['340','0'],
               
               50:['340','0'],
               51:['210','43'],
               52:['101','v2'],
               53:['006','44'],
               54:['590','v1/28'],
               
               55:['706','0'],  #(2
               56:['080','v3'],
               57:['405','16.0'],
               58:['590','v7'],
               59:['101','v11'], #(3
               
               60:['300','-5'],
               61:['146','0'],   #(4
               62:['380','v4'],
               63:['676','96']}
      
#%% Sector 31: Chapter 3 (R54)
            
      BS[31] = {0:['680','15'],
                1:['006','42'],
                2:['026','42'],
                3:['156','126'],
                4:['206','15.0+'],
                
                5:['670','113'],
                6:['370','64'],
                7:['290','2*'],
                8:['670','112'],
                9:['680','15'],
                
               10:['327','0'],
               11:['350','126'],
               12:['210','40'],
               13:['207','15.0+'],
               14:['210','40+'],
               
               15:['350','31'],
               16:['210','41'],
               17:['200','40+'],
               18:['106','-4'],
               19:['340','0'],   #(6
               
               20:['186','v6'],
               21:['210','40+'],
               22:['200','45+'],
               23:['677','0'],
               24:['680','1'],
               
               25:['200','40'],
               26:['207','15.0'],
               27:['230','40+'],
               28:['591','0'],
               29:['006','45'],  #(11
               
               30:['136','256'],
               31:['090','3*'],
               32:['006','45'],
               33:['590','2*'],
               34:['010','43'],
               
               35:['216','62+'],
               36:['206','63'],
               37:['350','512'],
               38:['220','40+'],
               39:['216','63'],
               
               40:['200','41'],
               41:['216','63+'],
               42:['200','43'],
               43:['226','64'],
               44:['216','64'],
               
               45:['690','1'],
               46:['590','v8'],
               47:['300','0'],
               48:['417','16.0'], #(7
               49:['320','1'],
               
               50:['210','0+v7'],
               51:['125','1'],    #(8
               52:['075','60+'],  #(10
               53:['080','v1'],
               54:['200','0+v7'],
               
               55:['210','60+'],
               56:['200','62+'],
               57:['677','0'],
               58:['680','1'],
               59:['590','0']}
               
#%% Sector 32: Chapter 4 (R50,R667)   
               #R 50
      BS[32] = {0:['000','63+'],
                1:['080','2*'],
                2:['590','v/19'],
                3:['101','2*'],
                4:['590','v/20'],
                
                5:['102','v2'],
                6:['590','v3/3'],
                7:['450','30'],  #(2
                8:['101','v2/33'],
                9:['490','v6'],
                
                10:['440','30'],
                11:['440','18'],
                12:['410','40'],
                13:['200','41'],
                14:['210','63'],
                
                15:['670','28'],
                16:['680','13'],
                17:['101','32'],
                18:['590','v4/51'],
                19:['010','41'],  #(3
                
                20:['104','v4'],
                21:['101','v3/11'],
                22:['106','4'],   #(6
                23:['200','61+'],
                24:['590','v1/11'],
                
                25:['006','63'],  #(4
                26:['300','-5'],
                27:['146','0'],   #(5
                28:['380','v5'],
                29:['676','96'],
                
                30:['680','15'],
                31:['006','63'],
                32:['026','63'],
                33:['156','126'],
                34:['200','59'],
                
                35:['216','15.0'],
                36:['206','15.0+'],
                37:['280','v4/11'],
                38:['200','63+'],
                39:['216','15.0+'],
                
                40:['690','15'],
                41:['000','58'],
                42:['080','v/59'],
                43:['670','37'],
                44:['680','13'],
                
                45:['590','2.0v/66'],
                
                #R 667
                46:['200','62+'],
                47:['677','0'],
                48:['690','1'],
                49:['670','127'],
                
                50:['690','0'],
                51:['300','127'],
                52:['210','63+'],
                53:['010','61+'],
                54:['300','1'],
                
                55:['210','62'],
                56:['210','58+'],
                57:['300','114'],
                58:['210','62+'],
                59:['677','0'],
                
                60:['680','1'],
                61:['590','v/29'],
                62:['=0','=0'],
                63:['590','v3/50']}

#%% Sector 33: Chapter 4 (R55,R56,R57,R58)
               #R 55
      BS[33] = {0:['440','18'],
                1:['410','40'],
                2:['006','41'],
                3:['090','3*'],
                4:['300','13'],  #(4
                
                5:['590','9'],
                6:['176','101'],
                7:['090','-3*'],
                8:['016','63+'],
                9:['670','113'], #(1
                
                10:['176','64'],
                11:['090','2*'],
                12:['670','112'],
                13:['680','15'],
                14:['006','63+'],
                
                15:['026','63+'],
                16:['156','126'],
                17:['206','15.0'],
                18:['280','v4/11'],
                19:['200','62'],
                
                20:['216','15.0+'],
                21:['690','15'],
                22:['174','v1/6'],  #(3
                23:['084','0'],
                24:['006','58'],
                
                25:['080','v/29'],
                26:['670','37'],
                27:['680','13'],
                28:['300','3'],
                29:['590','2.2v/66'],
                
               #R 56
                30:['104','v1'],
                31:['592','0'],
                32:['102','v/57'],  #(1
                33:['590','v3/3'],
                34:['010','0+v/84'], #(2
                
                35:['104','v3'],
                36:['592','0'],
                37:['102','v1/57'],
                38:['590','v3/3'],
                
                #R57
                39:['440','18'],   #(1
                
                40:['410','40'],
                41:['200','41'],
                42:['100','-1'],   #(2
                43:['080','3*'],
                44:['210','57'],
                
                45:['590','v3/55'],
                46:['010','0+v2'],
                47:['210','62'],
                48:['210','58+'],
                49:['006','63+'],
                
                50:['590','v1/55'],
                
                #R58
                51:['104','v1'],
                52:['592','0'],
                53:['102','v2'],  #(1
                54:['590','v3/3'],
                
                55:['440','18'],  #(2
                56:['410','40'],
                57:['200','41'],
                58:['220','57+'],
                59:['210','62+'],
                
                60:['677','0'],
                61:['680','1'],
                62:['590','v3/55'],
                63:['=0','=0']}
#%% Sector 34: Chapter 5 (R60,R61,R62)
               #R60
      BS[34] = {0:['010','0+v3'],
                1:['101','v2'],
                2:['590','v/20'],
                3:['101','2*'],
                4:['590','v/61'],
                
                5:['101','2*'],
                6:['590','v3/20'],
                7:['300','512'],
                8:['216','1.0+'],
                9:['126','3'],
                
                10:['016','61+'],
                11:['101','2*'],
                12:['590','v/63'],
                13:['300','5'],
                14:['590','v1/68'],
                
                #R61
                15:['670', '30'],
                16:['680','12'],
                17:['011','0+v8'],
                18:['101','v2'],
                19:['590','v4/20'],
                
                20:['300','30'],
                21:['207','v/16'],
                22:['350','-8'],
                23:['101','v3'],
                24:['590','v/4'],
                
                25:['300','1'],
                26:['100','-1'],
                27:['090','v9'],
                28:['006','61+'],
                29:['306','7'],
                
                30:['210','25+'],
                31:['400','24'],
                32:['200','62'],
                33:['210','27'],
                34:['440','26'],
                
                35:['440','18'],
                36:['410','40'],
                37:['200','41'],
                38:['101','v5'],
                39:['590','v/4'],
                
                40:['006','61+'],
                41:['101','v6'],
                42:['590','v3/20'],
                43:['300','59'],
                44:['207','v/16'],
                
                45:['350','-8'],
                46:['101','v7'],
                47:['590','v/4'],
                48:['300','4'],
                49:['101','v8'],
                
                50:['590','v/4'],
                51:['590','0'],
                
                #R 62
                52:['010','0+v1/61'],
                53:['101','v/68'],
                54:['590','v/61'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
      
#%% Sector 35: Chapter 5 (R47,R46)
               #R 47
      BS[35] = {0:['015','0+v6'],
                1:['016','0+v7'],
                2:['210','0+v4'],
                3:['106','-30'],
                4:['105','543'],
                
                5:['370','0'],
                6:['290','v2'],
                7:['330','1000'],
                8:['290','v5'],
                9:['320','500'],
                
                10:['105','401'],
                11:['125','177'],
                12:['236','5+v5'],
                13:['570','100'],
                14:['290','v2'],
                
                15:['125','464'],
                16:['090','v3'],
                17:['226','5+v5'],
                18:['126','10'],
                19:['090','1v5'],
                
                20:['370','0'],
                21:['280','1v5'],
                22:['590','v1'],
                23:['105','1'],
                24:['625','0'],
                
                25:['080','v1'],
                26:['105','0'],
                27:['106','0'],
                28:['591','0'],
                
                #R 46
                29:['620','0'],
                
                30:['620','30'],
                31:['620','13'],
                32:['620','12'],
                33:['200','44+'],
                
                35:['340','0'],
                36:['340','0'],
                37:['340','0'],
                38:['101','v1'],
                39:['280','v/47'],
                
                40:['620','23'],
                41:['200','44'],
                42:['101','v2'],
                43:['590','v/47'],
                44:['106','v5n6'],
                
                45:['206','v6'],
                46:['627','0'],
                47:['186','v3'],
                48:['106','-876'],
                49:['580','0'],
                
                50:['300','-15'],
                51:['380','*'],
                52:['186','v7'],
                53:['590','v5/59'],
                54:['=14','=27'],
                
                55:['=14','=15'],
                56:['=20','=0'],
                57:['=14','=27'],
                58:['=19','=5'],
                59:['=20','=0'],
                
                60:['=14','=11'],
                61:['=14','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
#%% Sector 36: Chapter 6 (R49)
                #R 49
      BS[36] = {0:['300','7'],
                1:['210','0+v/8'],
                2:['102','v1'],
                3:['590','v3/3'],
                4:['101','2*'],
                
                5:['590','1v32'],
                6:['410','50'],
                7:['400','0'],
                8:['410','42'],
                9:['174','v1/6'],
                
                10:['084','0'],
                11:['200','43'],
                12:['210','23'],
                13:['007','43+'],
                14:['350','1'],
                
                15:['210','23+'],
                16:['400','22'],
                17:['090','2*'],
                18:['440','20'],
                19:['440','50'],
                
                20:['440','18'],
                21:['410','50'],
                22:['010','23+'],
                23:['200','51'],
                24:['220','51'],
                
                25:['350','126'],
                26:['000','50+'],
                27:['090','2*'],
                28:['320','1'],
                29:['210','61+'],
                
                30:['200','62+'],
                31:['677','0'],
                32:['690','1'],
                33:['200','51'],
                34:['106','-5'],
                
                35:['340','0'],
                36:['186','-1*'],
                37:['056','51+'],
                38:['080','2*'],
                39:['590','2*'],
                
                40:['320','16'],
                41:['210','0+v5'],
                42:['230','62'],
                43:['220','62+'],
                44:['677','0'],
                
                45:['680','1'],
                46:['210','62+'],
                47:['300','0'],
                48:['210','62'],
                49:['270','58+'],
                
                50:['290','2*'],
                51:['590','2*'],
                52:['210','58+'],
                53:['590','v/29'],
                54:['174','v1/6'],
                
                55:['080','v/19'],
                56:['700','0'],
                57:['080','v4'],
                58:['300','5'],
                59:['590','9'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['590','v2']}
#%% Sector 37: Chapter 7 (R71,R66)
                #R71            
      BS[37] = {0:['070','62'],
                1:['090','v/19'],
                2:['610','1+*'],
                3:['300','0'],
                4:['350','16'],
                
                5:['280','v/29'],
                6:['200','56'],
                7:['280','2*'],
                8:['590','v/29'],
                9:['090','v8'],
                
                10:['102','-4'],
                11:['105','0'],
                12:['101','v3'],
                13:['590','v4/20'],
                14:['620','27'],
                
                15:['205','v5'],
                16:['101','2*'],
                17:['590','v/4'],
                18:['165','1'],
                19:['182','v3'],
                
                20:['090','v7'],
                21:['200','56+'],
                22:['320','1'],
                23:['210','56+'],
                24:['210','0+v5'],
                
                25:['590','v4'],
                26:['010','47'],
                27:['670','41'],
                28:['680','11'],
                29:['080','v6'],
                
                30:['200','56'],
                31:['370','8'],
                32:['280','3*'],
                33:['010','0+v5'],
                34:['590','v4'],
                
                35:['210','0+v5'],
                36:['300','776'],
                37:['210','v5'],
                38:['101','v3'],
                39:['590','v/20'],
                
                #R 66
                40:['300','18'],
                41:['106','4'],
                42:['670','35'],
                43:['680','12'],
                44:['620','30'],
                
                45:['620','13'],
                46:['080','2.2*'],
                47:['620','13'],
                48:['620','27'],
                49:['627','0'],
                
                50:['620','0'],
                51:['101','2.0v3'],
                52:['206','2.0+v2'],
                53:['280','2.0v4'],
                54:['590','5'],
                
                55:['=3','=2'],
                56:['=0','=4'],
                57:['=-36','=0'],
                58:['620','14'],
                59:['590','2.0v1'],
                
                60:['207','61'],
                61:['186','v/47'],
                62:['=0','=0'],
                63:['=0','=0']}
#%% Sector 38: Chapter 14 (R102)
                #R 102         
      BS[38] = {0:['',''], #Change to +0
                1:['',''],
                2:['',''], #Change to -1
                3:['',''],
                4:['=0','=0'],
                
                5:['300','15'],
                6:['330','18'],
                7:['590','52'],
                8:['300','3'],
                9:['670','127'],
                
                10:['690','0'],
                11:['670','12'],
                12:['680','0'],
                13:['597','0'],
                14:['=9','=0'],
                
                15:['=0','=0'],
                16:['',''],  #Change to +10
                17:['',''],
                18:['=19','=0'],
                19:['=0','=384'],
                
                20:['',''], # +0.5
                21:['',''],
                22:['=19','=0'],
                23:['=0','=0'],
                24:['=8','=0'],
                
                25:['=0','=0'],
                26:['=25','=0'],
                27:['=0','=0'],
                28:['=16','=0'],
                29:['=0','=384'],
                
                30:['',''], # +1000
                31:['',''],
                32:['=0','=4'],
                33:['=2','=1'],
                34:['=4','=8'],
                
                35:['=0','=32'],
                36:['=64','=96'],
                37:['=128','=0'],
                38:['=0','=0'],
                39:['=0','=0'],
                
                40:['=0','=0'],
                41:['=0','=0'],
                42:['=0','=0'],
                43:['=0','=0'],
                44:['=0','=0'],
                
                45:['=0','=0'],
                46:['=0','=0'],
                47:['=0','=0'],
                48:['',''], # +0.1
                49:['',''],
                
                50:['=0','=0'],
                51:['=0','=0'],
                52:['677','25'],
                53:['687','14'],
                54:['380','52'],
                
                55:['590','v1/6'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
#%% Sectoy 39: Chapter 8 (R64)
                #R 64
      BS[39] = {0:['680','11'],
                1:['102','v/65'],
                2:['670','26'],
                3:['590','v'],
                4:['101','v4'],
                
                5:['590','v/54'],
                6:['=25','=0'],
                7:['=0','=384'], #Maybe 284
                8:['010','63+'],
                9:['010','63'],
                
                10:['300','7'],
                11:['210','0+v/8'],
                12:['102','v2'],
                13:['590','v3/3'],
                14:['101','2*'],
                
                15:['590','1v32'],
                16:['410','50'],
                17:['174','v2/3'],
                18:['080','v5'],
                19:['400','0'],
                
                20:['594','0'],
                21:['174','v1/6'],
                22:['080','v/19'],
                23:['007','45'],
                24:['700','0'],
                
                25:['187','3*'],
                26:['300','5'],
                27:['590','9'],
                28:['090','2*'],
                29:['590','v/19'],
                
                30:['300','0'],
                31:['080','2*'],
                32:['200','43'],
                33:['210','23'],
                34:['400','22'],
                
                35:['000','43+'],
                36:['090','2*'],
                37:['440','20'],
                38:['440','50'],
                39:['440','18'],
                
                40:['410','50'],
                41:['200','51'],
                42:['220','51'],
                43:['350','126'],
                44:['000','50+'],
                
                45:['090','2*'],
                46:['320','1'],
                47:['210','61+'],
                48:['006','42'],
                49:['101','v1/65'],
                
                50:['590','1v3/54'],
                51:['174','v1/6'],
                52:['080','v/19'],
                53:['440','v6'],
                54:['410','40'],
                
                55:['200','40+'],
                56:['106','-2'],
                57:['340','0'],
                58:['186','-1*'],
                59:['210','61+'],
                
                60:['200','41'],
                61:['590','1v4/65'],
                62:['=0','=0'],
                63:['590','v3']}
#%% Sector 40: Chapter 9 (R48,R73)
            #R48
      BS[40] = {0:['101','v7'],
                1:['102','1'],
                2:['103','0'],
                3:['600','0+v2'],
                4:['300','0'],
                
                5:['280','v3'],
                6:['591','0'],
                7:['370','31'],
                8:['290','v1'],
                9:['101','v7'],
                
                10:['627','0'],
                11:['162','1'],
                12:['080','v6'],
                13:['106','-4'],
                14:['327','0'],
                
                15:['186','v5'],
                16:['213','1.0'],
                17:['590','v1'],
                18:['223','1.0'],
                19:['213','1.0'],
                
                20:['173','122'],
                21:['183','v1'],
                22:['300','10'],
                23:['590','9'],
                24:['101','v8'],
                
                25:['590','v4'],
                26:['013','1.61'],
                27:['590','v/29'],
                
                #R 73
                28:['200','58'],
                29:['280','3*'],
                
                30:['620','30'],
                31:['106','13'],
                32:['101','v/29'],
                33:['280','v2'],
                34:['626','0'],
                
                35:['600','1+*'],
                36:['106','0'],
                37:['080','2*'],
                38:['101','v/29'],
                39:['176','31'],
                
                40:['090','v2'],
                41:['176','27'],
                42:['080','2*'],
                43:['101','v3'],
                44:['176','30'],
    
                45:['080','v3'],
                46:['591','0'],
                47:['300','6'],
                48:['210','0+v4'],
                49:['590','-1v3'],
                
                50:['=0','=0'],
                51:['=0','=0'],
                52:['=0','=0'],
                53:['=0','=0'],
                54:['=0','=0'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
#%% Sector 41: Chapter 15 (R67)
                #R 67
      BS[41] = {0:['101','2*'],
                1:['590','v/20'],
                2:['010','61'],
                3:['102','v13'],
                4:['590','v3/3'],
                
                5:['204','2.0'],
                6:['340','0'],
                7:['340','0'],
                8:['214','2.0'],
                9:['125','2'],
                
                10:['175','0'],
                11:['080','v3'],
                12:['105','1'],
                13:['675','12'],
                14:['685','1'],
                
                15:['175','0'],
                16:['185','v11'],
                17:['101','v20/51'],
                18:['100','0'],
                19:['080','v4/20'],
                
                20:['590','v/29'],
                21:['440','18'],
                22:['410','46'],
                23:['300','v1'],
                24:['210','0+v/6'],
                
                25:['174','v1/6'],
                26:['084','0'],
                27:['300','v1/6'],
                28:['210','0+v/6'],
                29:['670','42'],
                
                30:['680','12'],
                31:['101','v15'],
                32:['200','61+'],
                33:['106','4'],
                34:['590','v1/11'],
                
                35:['006','47'],
                36:['176','29'],
                37:['090','v17'],
                38:['026','47'],
                39:['206','v12'],
                
                40:['280','3*'],
                41:['300','11'],
                42:['590','9'],
                43:['210','0+v2'],
                44:['206','0+v12'],
                
                45:['350','-256'],
                46:['105','0'],
                47:['675','0'],
                48:['685','2'],
                49:['137','256'],
                
                50:['185','v2'],
                51:['015','0+v10'],
                52:['206','0+v12'],
                53:['350','255'],
                54:['210','2+*'],
                
                55:['004','1+*'],
                56:['105','0'],
                57:['102','1'],
                58:['207','2.0+'],
                59:['210','0+v9'],
                
                60:['006','61+'],
                61:['101','2*'],
                62:['590','v3/20'],
                63:['205','2.1']}
#%% Sector 42: Chapter 15 (R67)     
      BS[42] = {0:['101','2*'],
                1:['590','v/4'],
                2:['204','2.0'],
                3:['350','3'],
                4:['207','2*'],
                
                5:['597','0'],
                6:['=v4','=v5'],
                7:['=v6','=v7'],
                8:['172','5'],
                9:['182','v14'],
                
                10:['102','1'],
                11:['134','1'],
                12:['590','v8'],
                13:['200','43'],
                14:['226','63+'],
                
                15:['216','63+'],
                16:['590','v4'],
                17:['200','43'],
                18:['340','0'],
                19:['590','1v5'],
                
                20:['206','63+'],
                21:['340','0'],
                22:['027','43'],
                23:['206','63+'],
                24:['220','43'],
                
                25:['220','43'],
                26:['216','63+'],
                27:['090','v4'],
                28:['206','63'],
                29:['320','512'],
                
                30:['216','63'],
                31:['590','v4'],
                
                32:['=29','=360'],
                33:['=49','=269'],
                34:['=49','=581'],
                
                35:['=0','=0'],
                36:['=50','=274'],
                37:['=50','=637'],
                38:['=51','=638'],
                39:['=52','=597'],
                
                40:['=53','=295'],
                41:['=53','=888'],
                42:['=55','=558'],
                43:['=56','=642'],
                44:['=57','=590'],
                
                45:['=0','=0'],
                46:['=58','=286'],
                47:['=58','=900'],
                48:['=60','=547'],
                49:['=0','=0'],
                
                50:['=61','=266'],
                51:['=47','=791'],
                52:['=0','=0'],
                53:['=0','=0'],
                54:['=0','=0'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
#%% Sector 43: Chapter 27 (R72)
                #R 72
      BS[43] = {0:['410','1.0'],
                1:['400','v1'],
                2:['290','v10'],
                3:['620','30'],
                4:['620','13'],
                
                5:['670','479'],
                6:['300','0'],    #(5
                7:['680','0'],
                8:['210','0+v5'],
                9:['200','1.1'],
                
                10:['380','v2'],
                11:['200','1.0+'],
                12:['370','520'],
                13:['290','1v2'],
                14:['207','-5v9'],
                
                15:['290','v3'],   #(2
                16:['210','1.1'],
                17:['330','521'],
                18:['380','v4'],
                19:['000','1.0'],  #(3
                
                20:['300','776'],
                21:['210','1.0'],
                22:['300','32'],
                23:['210','1.1'],
                24:['300','479'],
                
                25:['210','1.1+'],
                26:['200','0+v5'],
                27:['340','0'],
                28:['377','1'],
                29:['590','v6'],
                
                30:['620','0'],    #(1
                31:['210','0+v5'],
                32:['340','0'],
                33:['410','v1'],   #(6
                34:['407','-8'],
                
                35:['410','2v1'],
                36:['400','1.0'],
                37:['417','-8'],
                38:['400','2v1'],
                39:['590','0'],
                
                40:['300','10'],  #(10
                41:['080','2*'],
                42:['300','0'],
                43:['090','2*'],
                44:['300','-5'],
                
                45:['210','1.0'],
                46:['627','16'],
                47:['010','1.1'],
                48:['107','13'],
                49:['590','2v4'],
                
                50:['100','0'],   #(4
                51:['380','v7'],
                52:['210','0+v8'],
                53:['620','30'],  #(7
                54:['620','13'],
                
                55:['620','27'],
                56:['620','2'],   #(8
                57:['620','0'],
                58:['670','44'],
                59:['590','v5'],
                
                60:['=520','=513'], #(9
                61:['620','27'],
                62:['620','?'], #letter
                63:['=0','=0']}
#%% Sector 44: Chapter 77 (R722)
                #R 722
      BS[44] = {0:['106','0'],  #(6
                1:['620','15'],
                2:['186','v7'],
                3:['105','0'],  #(1
                4:['106','0'],
                
                5:['300','0'],
                6:['670','43'],
                7:['680','0'],
                8:['015','0+v1'], #(5
                9:['016','1+v1'],
                
                10:['210','2+v1'],
                11:['080','v20'],
                12:['200','1.1'],
                13:['350','511'],
                14:['370','8'],
                
                15:['290','2*'],
                16:['637','v8'],
                17:['620','10'],
                18:['290','v3'],
                19:['320','200'],
                
                20:['210','v4'],
                21:['200','1.1+'],
                22:['300','0'],     #(4
                23:['210','0+v22'], #(20
                24:['106','-30'],
                
                25:['105','543'],
                26:['290','v23'],
                27:['330','1000'],
                28:['290','v24'],
                29:['320','500'],
                
                30:['105','404'],
                31:['125','177'],  #(23
                32:['236','5+v24'],
                33:['570','100'],
                34:['290','v23'],
                
                35:['125','464'],  #(26
                36:['090','v26'],
                37:['226','5+v24'],
                38:['126','10'],
                39:['090','1v24'],
                
                40:['177','0'],    #(22
                41:['080','1v24'],
                42:['590','2v20'],
                43:['105','1'],    #(24
                44:['625','0'],
                
                45:['080','2v20'],
                46:['590','v1'],   #(13
                47:['106','-3'],   #(3
                48:['010','0+v13'],
                49:['410','v5'],
                
                50:['100','0'],
                51:['206','1+v5'],  #(7
                52:['016','0+v6'],
                53:['080','v20'],
                54:['290','v20'],
                
                55:['167','-1'],
                56:['620','11'],
                57:['380','v20'],
                58:['=16','=1'], #((8
                59:['=2','=19'],
                
                60:['=4','=21'],
                61:['=22','=7'],
                62:['=0','=0'],
                63:['=0','=0']}
#%% Sector 45: Chapter 30 (R666,R52)
                #R 666
      BS[45] = {0:['670','127'],
                1:['680','0'],
                2:['200','62+'],
                3:['677','0'],
                4:['680','1'],
                
                5:['300','6'],
                6:['590','6'],
                7:['200','62+'],  #(1
                8:['677','0'],
                9:['690','1'],
                
                10:['670','28'],
                11:['680','13'],
                12:['006','63+'],
                13:['176','127'],
                14:['080','v3'],
                
                15:['670','127'],
                16:['680','14'],
                17:['200','14.60+'],
                18:['210','0+v17/51'],
                19:['101','45'],  #(3
                
                20:['010','0+v16/51'],
                21:['590','v4/51'],
                22:['670','45'],   #(2
                23:['680','15'],
                24:['006','63+'],
                
                25:['136','127'],
                26:['080','v4'],
                27:['105','-1'],
                28:['200','58+'],
                29:['370','526'],
                
                30:['290','2v7'],
                31:['300','8'],
                32:['590','9'],
                33:['126','29'],  #(7
                34:['016','0+v7'],
                
                35:['205','14.59'],
                36:['090','2*'],
                37:['215','59'],
                38:['185','v7'],
                39:['670','127'],  #(4
                
                40:['690','0'],
                41:['670','2'],
                42:['680','0'],
                43:['590','4.1*'],
                44:['300','-12'],
                
                45:['677','126'],  #(5
                46:['687','13'],
                47:['380','4.0v5'],
                48:['590','1.0'],
                
                #R 52
                49:['000','63+'],
                
                50:['080','v/19'],
                51:['102','v1'],
                52:['590','v3/3'],
                53:['440','18'],  #(1
                54:['410','40'],
                
                55:['200','41'],
                56:['210','57+'],
                57:['210','62+'],
                58:['677','0'],
                59:['680','1'],
                
                60:['590','v/29'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['590','v2/666']}
#%% Sector 46: Chapter 28 (R81,R45)
                #R 81
      BS[46] = {0:['600','0+v3'],
                1:['106','0'],    #(3
                2:['080','3*'],
                3:['185','v6'],   #(2
                4:['590','v/19'],
                
                5:['176','31'],
                6:['090','v'],
                7:['600','1+v/1'],
                8:['000','1+v/1'],
                9:['080','-2*'],
                
                10:['172','v/1'],
                11:['080','v1'],
                12:['206','16v/45'], #(9
                13:['677','0'],
                14:['680','11'],
                
                15:['205','0+v11'],
                16:['080','2*'],
                17:['206','v/45'],
                18:['597','0'],
                19:['=4','=7'],   #(5
                
                #20:['=7 v2/58 n/57','=7 v/55 n/57'],
                #21:['=7 v/31 n/57','=7 v/34 n/57'],
               
                20:['306', '-12'],  #(1
                21:['101', '-4'],
                22:['280', '2*'],
                23:['101', '-1'],
                24:['105', '-3'],
                
                25:['275', '0+v5'], #(6
                26:['280', 'v2'],
                27:['302', '7n/57'],
                28:['590', 'v1/80'],
                29:['=v/56', '=v/58'],  #(11
                
                #R 45
                30:['=v/19', '=v/60'],
                31:['=v/19', '=1v/53'],
                32:['=v1/60', '=v/53'],
                33:['=v/52', '=v/19'],
                34:['=v/19', '=v/667'],
                
                35:['=v1/666', '=v/19'],
                36:['=v/49', '=1v/64'],
                37:['=v/73', '=v/19'],
                38:['=v/19', '=v/67'],
                39:['=v/50', '=v/19'],
                
                40:['=v/48', '=v/62'],
                41:['=v/19', '=v/10'],
                42:['=v/19', '=v/19'],
                43:['=v/19', '=v/19'],
                44:['=v/19', '=v/70'],
                
                45:['=v/19', '=v/19'],
                46:['=22', '=34'],
                47:['=22', '=26'],
                48:['=34', '=26'],
                49:['=45', '=22'],
                
                50:['=22', '=32'],
                51:['=45', '=22'],
                52:['=22', '=32'],
                53:['=45', '=22'],
                54:['=36', '=39'],
                
                55:['=40', '=22'],
                56:['=26', '=41'],
                57:['=32', '=26'],
                58:['=40', '=34'],
                59:['=22', '=22'],
                
                60:['=22', '=22'],
                61:['=22', '=22'],
                62:['=22', '=29'],
                63:['=22', '=22']}


#%% Sector 47: Quicky 1, Quicky 2
# A' = 1/A

      BS[47] = {0:['707','-259'],
                1:['300','1'],
                2:['090','9'],
                3:['210','2'],
                4:['410','32'],
                
                5:['410','34'],
                6:['230','32'],
                7:['210','34'],
                8:['300','749'],
                9:['230','33+'],
                
                10:['490','v1'],
                11:['330','475'],
                12:['210','35+'],  #(1
                13:['300','-1'],
                14:['510','34'],
                
                15:['430','2'],   #(2
                16:['500','34'],
                17:['410','34'],
                18:['510','32'],
                19:['380','v2'],
                
                20:['010','2'],
                21:['450','2'],
                22:['500','34'],
                23:['420','34'],
                
                #Quicky 2
                # A' = A^(-1/2)
                24:['410','32'],
                25:['490','v1'],
                26:['300','2'],  #(6
                27:['590','9'],
                28:['=1','=0'],  #(2
                29:['=0','=-384'],
                
                30:['=0','=0'],
                31:['=0','=-256'],
                32:['410','34'], #(1
                33:['707','512'],
                34:['347','-257'],
                
                35:['210','34'],
                36:['707','-1'],
                37:['210','32'],
                38:['157','1'],
                39:['230','33+'],
                
                40:['290','v6'],
                41:['080','v3'],
                42:['320','247'],
                43:['340','13'],  #(3
                44:['210','35+'],
                
                45:['400','34'],
                46:['300','-2'],
                47:['590','v5'],
                48:['430','v2'],  #(4
                49:['500','34'],
                
                50:['410','34'],
                51:['510','32'],  #(5
                52:['500','34'],
                53:['380','v4'],
                54:['430','2v2'],
                
                55:['500','34'],
                56:['420','34'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
      

#%% Sector 48: Quicky 6 and Quicky 7 (1st part) 
#Q6: A' = sin(A) or cos(A)
#Q7: A' = cos(A)
                
                #Begin of Q6
      BS[48] = {0:['590','v1'],
                1:['420','v5'],
                2:['500','v7'],  #(1
                3:['410','32'],
                4:['420','v6'],
                
                5:['410','34'],
                6:['450','v6'],
                7:['450','32'],
                8:['410','32'],
                9:['500','32'],
                
               10:['410','36'],
               11:['500','v3'],
               12:['300','-3'],
               13:['427','v4'],  #(2
               14:['500','36'],
               
               15:['380','v2'],
               16:['420','v5'],
               17:['200','34+'],
               18:['350','2'],
               19:['280','v8'],
               
               20:['510','32'],
               21:['590','1v8'],
               22:['=-18','=451'],  #(3
               23:['=722','=-465'],
               24:['=-12','=245'],
               
               25:['=220','=336'],
               26:['=-7','=714'],
               27:['=183','=-307'],
               28:['=-3','=80'],
               29:['=431','=326'],
               
               30:['=0','=794'],  #(4
               31:['=272','=-331'],
               32:['=1','=852'],  #(5
               33:['=126','=402'],
               34:['=29','=1'],   #(6
               
               35:['=0','=640'],
               36:['=0','=110'],  #(7
               37:['=972','=325'],
               38:['=500','=32'], #(8
               39:['=0','=0'],

               #Beginning of Q7
               40:['500','v7'],  #(1
               41:['410','32'],
               42:['440','v6'],
               43:['410','34'],
               44:['450','v6'],
                
               45:['450','2'],
               46:['450','32'],
               47:['410','32'],
               48:['500','32'],
               49:['410','36'],
                
               50:['500','v3'],
               51:['300','-3'],
               52:['427','v4'],  #(2
               53:['500','36'],
               54:['380','v2'],
                
               55:['420','v5'],
               56:['250','34+'],
               57:['280','2v7'],
               58:['500','32'],
               59:['590','3v7'],
                
               60:['=-18','=519'], #(3
               61:['=950','=-455'],
               62:['=-12','=812'],
               63:['=877','=335']}


#%% Sector 49: Quicky 7 (2nd part), Q8
#Q7: A' = cos(A)
#Q8 Print SAC (signed integer) 

      BS[49] = {0:['=-7','=694'],
                1:['=191','=-307'],
                2:['=-3','=992'],
                3:['=430','=326'],
                4:['=0','=794'],  #(4
                
                5:['=272','=-331'],
                6:['=1','=852'],  #(5
                7:['=126','=402'],
                8:['=30','=0'],   #(6
                9:['=0','=640'],
                
                10:['=0','=110'],  #(7
                11:['=972','=325'],
                12:['510','32'],
                13:['=0','=0'],

                #Begin of Q8
                14:['620','0'],    #x Punch FS, CR, LF and CR
                
                15:['620','30'],   #x
                16:['620','13'],   #x
                17:['620','30'],   #x
                18:['015','0+v7'], #y Store B5, B6                
                19:['016','0+v8'], #y
                
                20:['370','0'],    #x Ensure St=S
                21:['290','v1'],   #y Punch sp or -; form S'=|S|
                22:['620','11'],   #y
                23:['167','-1'],   #y
                24:['380','1v1'], #y
                
                25:['620','14'],  #(1
                26:['106','-30'], #x Set digit count in B6
                27:['210','0+v5'],#y Store SAC for zero-suppresion
                28:['105','542'], #(2   x
                29:['125','177'], #(3   x Form digit to be punched
                
                30:['570','100'], #     x using clutched count in B5
                31:['236','5+v6'],#     x
                32:['290','v3'],  #     x
                33:['125','464'], #(4   x
                34:['090','v4'],  #x
                
                35:['126','10'],  #     y Count digits    
                36:['226','0+v6'],#     x Restore S>=0
                37:['090','v6'],  #     y Jump on last digit
                38:['370','0'],  #(5    x Suppress non-significant zeros
                39:['290','v2'], #      x
                
                40:['625','1'],  #(6    y Punch digits
                41:['080','v2'], #      y
                42:['105','0'],  #(7    x Restore B5, B6
                43:['106','0'],  #(8    x
                44:['620','14'], #      y Punch two spaces
                
                45:['620','14'], #      y
                46:['=0','=0'],
                47:['=0','=0'],
                48:['=0','=0'],
                49:['=0','=0'],
                
                50:['=0','=0'],
                51:['=0','=0'],
                52:['=0','=0'],
                53:['=0','=0'],
                54:['=0','=0'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
          

#%% Sector 50: Quicky 9 (1st part)
# Print Accumulator Fixed Point    

      BS[50] = {0:['620','0'],    #x Punch FS, CR, LF and CR
                1:['620','30'],
                2:['620','13'],
                3:['620','30'],
                4:['016','0+v9'],
                
                5:['011','34'],
                6:['006','34'],
                7:['026','34'],
                8:['206','8.2'],
                9:['210','0+v5'],
                
                10:['206','8.2+'],
                11:['171','4.0'],
                12:['090','4*'],
                13:['206','0.2'],
                14:['210','0+v5'],
                
                15:['206','0.2+'],
                16:['210','0+v1'],
                17:['337','0'],  #(1
                18:['410','32'],
                19:['400','2v3'],
                
                20:['590','2*'],
                21:['500','v3'],
                22:['380','-1*'],
                23:['410','34'],
                24:['440','32'],
                
                25:['106','14'],
                26:['490','5*'],
                27:['400','32'],
                28:['520','2'],
                29:['440','34'],
                
                30:['106','11'],
                31:['410','32'],
                32:['400','v2'],
                33:['590','3v4'],
                34:['',''],  #(2   poner +10
                
                35:['',''],
                36:['=-3','=410'], #(3
                37:['=614','=409'],
                38:['=0','=0'],
                39:['=0','=256'],
                
                40:['320','1'],   #(4
                41:['400','34'],
                42:['520','v2'],
                43:['410','34'],
                44:['400','32'],
                
                45:['450','34'],
                46:['490','v4'],
                47:['330','0'],  #(5
                48:['290','4*'],
                49:['320','1'],
                
                50:['620','14'],
                51:['380','-1*'],
                52:['626','0'],
                53:['106','0'],
                54:['400','34'], #(6
                
                55:['520','v3'],
                56:['410','34'],
                57:['400','32'],
                58:['300','543'], #(7
                59:['410','32'],
                
                60:['450','34'],
                61:['320','177'],
                62:['490','1v7'],
                63:['320','464']}

#%% Sector 51: Quicky 9 (2nd part), Q4
#Q9: Print Accumulator Fixed Point    
#Q4: A' = exp(A)

      BS[51] = {0:['290','-1*'],
                1:['627','0'],
                2:['080','-4v9'],  #(8
                3:['200','34'],
                4:['370','2'],
                
                5:['290','v6'],
                6:['036','0+v1'],
                7:['090','v9'],
                8:['620','28'],
                9:['400','32'],
                
                10:['520','v2'],
                11:['010','0+v1'],
                12:['186','v7'],
                13:['106','0'],  #(9
                14:['620','14'],
                
                15:['620','14'],
                16:['=0','=0'],
                
                #Begin of Q4
                17:['500','2v3'],
                18:['410','32'],
                19:['450','v3'],
                
                20:['300','4'],
                21:['490','9'],
                22:['400','32'],
                23:['440','v3'],
                24:['450','2'],
                
                25:['300','-5'],
                26:['490','v7'],
                27:['400','0'],
                28:['590','1v9'],
                29:['=8','=0'],  #(3
                
                30:['=0','=255'],
                31:['=0','=869'],
                32:['=337','=369'],
                33:['=-8','=532'], #(4
                34:['=817','=-349'],
                
                35:['=-6','=238'],
                36:['=453','=-307'],
                37:['=-4','=863'],
                38:['=911','=350'],
                39:['=-2','=399'],
                
                40:['=904','=-316'],
                41:['=-1','=84'],
                42:['=707','=454'],
                43:['=0','=454'],
                44:['=16','=-492'],
                
                45:['=1','=766'], #(5
                46:['=912','=354'],
                47:['=28','=0'],  #(6
                48:['=0','=640'],
                49:['400','32'],  #(7
                
                50:['440','v6'],
                51:['410','34'],
                52:['450','v6'],
                53:['450','32'],
                54:['410','32'],
                
                55:['400','v4'],
                56:['500','32'], #(8
                57:['437','v5'],
                58:['380','v8'],
                59:['500','32'],
                
                60:['450','2'],
                61:['900','0'],
                62:['220','34+'],
                63:['717','0']}  #(9
                      
#%% Sector 52: Quicky 10 (1st part)
# Print Accumulator Floating Point
                
      BS[52] = {0:['620','0'],
                1:['620','30'],
                2:['620','13'],
                3:['620','30'],
                4:['015','0+v24'],
                
                5:['016','0+v25'],
                6:['330','2'],
                7:['210','0+v19'],
                8:['105','1'],
                9:['490','v3'],
                
                10:['520','2'],
                11:['135','3'],
                12:['300','0'], #(3
                13:['410','32'],#(4
                14:['700','-1'],
                
                15:['090','1v8'],
                16:['330','6'],
                17:['290','v8'],
                18:['540','2v11'],
                19:['410','34'],
                
                20:['400','32'],
                21:['520','2v11'],
                22:['440','34'],
                23:['590','v4'],
                24:['',''],  #(5  poner +10
                
                25:['',''],
                26:['300','0'],  #(8
                27:['625','13'],
                28:['400','v6'], # (+1) written afterwards
                29:['106','20'],

                30:['590','v13'],
                31:['125','464'], #(18
                32:['090','v18'],
                33:['625','0'],
                34:['440','34'],
                
                35:['520','v5'],
                36:['176','0'],  #(19
                37:['080','v15'],
                38:['106','11'],
                39:['290','v9'],
                
                40:['167','-1'],
                41:['380','1v9'],
                42:['=-3','=410'], #(11
                43:['=614','=409'],
                44:['',''], # 1E6
                
                45:['',''],
                46:['',''], # 1E12
                47:['',''],
                48:['',''], # 1 (6
                49:['',''],
                
                50:['106','9'],  #(12
                51:['400','34'],
                52:['526','-18v5'],
                53:['326','-8'],
                54:['410','34'], #(13
                
                55:['536','-18v5'],
                56:['440','32'],
                57:['490','1v12'],
                58:['136','11'],
                59:['400','34'],
                
                60:['090','1v13'],
                61:['005','0+v19'],
                62:['520','v11'],  #(14
                63:['135','1']}
      
#%% Sector 53: Quicky 10 (2nd part), Q0
#Q10: Print Accumulator Floating Point
#Q0:?
           
      BS[53] = {0:['090','v14'],
                1:['725','0'],
                2:['715','0'],
                3:['440','32'],
                4:['176','4'],  #(15
                
                5:['186','v16'],
                6:['620','14'],
                7:['080','v17'],#(16
                8:['620','28'],
                9:['105','543'],#(17
                
                10:['125','177'],
                11:['450','34'],
                12:['490','1v17'],
                13:['175','442'],
                14:['080','v18'],
                
                15:['590','v12'],
                16:['106','26'], #(9
                17:['620','15'],
                18:['105','9'],
                19:['370','10'],
                
                20:['290','3*'],
                21:['620','14'],
                22:['105','0'],
                23:['626','0'],
                24:['106','543'], #(20
                
                25:['126','177'],
                26:['335','1'],
                27:['290','1v20'],
                28:['126','464'],  #(21
                29:['090','v21'],
                
                30:['626','0'],
                31:['325','1'],
                32:['135','9'],
                33:['090','v20'],
                34:['105','0'],  #(24
                
                35:['106','0'],  #(25
                36:['620','14'],
                37:['620','14'],
                38:['=0','=0'],
                39:['=0','=0'],

                #Beginning of Quicky 0                
                40:['570','?'], #Number
                41:['670','479'],
                42:['690','0'],
                43:['670','43'],
                44:['680','0'],
                
                45:['210','0+'],
                46:['210','8+'],
                47:['300','8'],
                48:['590','v1/72'],
                49:['300','0'],

                50:['=0','=0'],
                51:['=0','=0'],
                52:['=0','=0'],
                53:['=0','=0'],
                54:['=0','=0'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
      

#%% Sector 54: Quicky 11, Quicky 12 (1st part)
#Q11: Print SAC (unsigned integer)
#Q12: A' = A**(1/2)


      BS[54] = {0:['620','0'],
                1:['620','30'],
                2:['620','13'],
                3:['620','30'],
                4:['015','0+v6'],
                
                5:['016','0+v7'],
                6:['210','0+v4'],
                7:['106','-30'],
                8:['105','543'],  #(1
                9:['370','0'],
                
                10:['290','v2'],
                11:['330','1000'],
                12:['290','v5'],
                13:['320','500'],
                14:['105','404'],
                
                15:['125','177'], #(2
                16:['236','5+v5'],
                17:['570','100'],
                18:['290','v2'],
                19:['125','464'], #(3
                
                20:['090','v3'],
                21:['226','5+v5'],
                22:['126','10'],
                23:['090','1v5'],
                24:['370','0'],  #(4
                
                25:['280','1v5'],
                26:['590','v1'],
                27:['105','1'], #(5
                28:['625','0'],
                29:['080','v1'],
                
                30:['105','0'], #(6
                31:['106','0'], #(7
                32:['620','14'],
                33:['620','14'],
                34:['=0','=0'],
                
                #Beginning of Q12
                35:['410','32'],
                36:['490','v1'],
                37:['300','12'],
                38:['590','9'],
                39:['=1','=0'],
                
                40:['=0','=-384'],  #(2
                41:['=-1','=0'],
                42:['=0','-512'],
                43:['410','34'],    #(1
                44:['410','36'],
                
                45:['707','512'],
                46:['347','-257'],
                47:['210','34'],
                48:['707','-1'],
                49:['210','32'],
                
                50:['157','1'],
                51:['230','33+'],
                52:['290','1v6'],
                53:['080','v3'],
                54:['320','247'],
                
                55:['340','13'], #(3
                56:['210','35+'],
                57:['400','34'],
                58:['300','-2'],
                59:['590','v5'],
                
                60:['430','v2'], #(4
                61:['500','34'],
                62:['410','34'],
                63:['510','32']} #(5
                

#%% Sector 55: Quicky 12 (2nd part), Q14
#Q12: A' = A**(1/2)
#Q14: ln(A)

      BS[55] = {0:['500','34'],                
                1:['380','v4'],
                2:['430','2v2'],
                3:['500','34'],
                4:['420','34'],
                
                5:['500','36'], #(6
                6:['=0','=0'],

                #Beginning of Q14
                7:['900','0'],
                8:['370','257'],
                9:['290','2*'],
                
                10:['490','v6'],
                11:['300','14'],
                12:['590','9'],
                13:['=0','=767'],
                14:['=912','=354'], #(2
                
                15:['=9','=0'],
                16:['=0','=0'],     #(1
                17:['=1016','=680'],
                18:['=221','=498'],#(3
                19:['=1019','=381'],
                
                20:['=841','=642'],
                21:['=1021','=162'],
                22:['=246','=274'],
                23:['=1022','=263'],
                24:['=823','=378'],
                
                25:['=1022','=776'],
                26:['=272','=519'],
                27:['=1023','=632'],
                28:['=844','=340'],
                29:['=1023','=777'],
                
                30:['=37','=512'],
                31:['=0','=476'],
                32:['=1023','=511'],  #(4
                33:['=210','v1'],     #(6
                34:['300','1'],
                
                35:['717','0'],
                36:['440','2'],
                37:['410','32'],
                38:['500','v3'],
                39:['300','!=2v3n4'],
                
                40:['427','v4'],   #(7
                41:['500','32'],
                42:['380','v7'],
                43:['410','32'],
                44:['400','v1'],
                
                45:['440','2'],
                46:['500','v2'],
                47:['420','32'],
                48:['=0','=0'],
                49:['=0','=0'],
                
                50:['=0','=0'],
                51:['=0','=0'],
                52:['=0','=0'],
                53:['=0','=0'],
                54:['=0','=0'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
                
#%% Sector 56: Quicky 15
# A' = arctan(y/x)

      BS[56] = {0:['007','33+'],
                1:['067','35+'],
                2:['400','34'],
                3:['090','2*'],
                4:['520','2'],
                
                5:['410','34'],
                6:['430','32'],
                7:['410','36'],
                8:['400','32'],
                9:['420','34'],
                
                10:['410','32'],
                11:['300','1'],
                12:['230','32'],
                13:['210','34'],
                14:['370','767'],
                
                15:['290','v4'],
                16:['300','15'],
                17:['590','9'],
                18:['',''],  #(3  poner -2
                19:['',''],
                
                20:['=2','=852'], #(12
                21:['=126','=402'],
                22:['=0','=852'], #(13
                23:['=126','=402'],
                24:['=-8','=788'],
                
                25:['=336','=314'], #(14
                26:['=-6','=0'],
                27:['=262','=-464'],
                28:['=-4','=253'],
                29:['=325','=322'],
                
                30:['=-3','=657'],
                31:['=325','=-295'],
                32:['=-3','=866'],
                33:['=163','=429'],
                34:['=-2','=207'],
                
                35:['=112','=-290'],
                36:['=-2','=419'],
                37:['=297','=409'],
                38:['=-1','=157'],
                39:['=691','=-342'],
                
                40:['=0','=955'],
                41:['=1023','=511'],  #(15
                42:['=300','=749'],   #(4
                43:['=230','=33+'],
                44:['=490','=2*'],
                
                45:['=330','=475'],
                46:['=210','=35+'],
                47:['=300','=-1'],
                48:['=510','=34'],
                49:['=430','=v3'],  #(2
                
                50:['=500','=34'],
                51:['=410','=34'],
                52:['=510','=32'],
                53:['=380','=v2'],
                54:['=450','=2'],
                
                55:['=500','=34'],
                56:['=420','=34'],
                57:['=510','=36'],
                58:['=410','=36'],
                59:['=500','=36'],
                
                60:['=410','=34'],
                61:['=400','=v14'],
                62:['=300','!=2v14n15'],
                63:['=500','=34']}

#%% Sector 57: Quicky 15 (continued) and Quicky 16
# A' = arctan(y/x)

      BS[57] = {0:['427','v15'],
                1:['380','-2*'],
                2:['500','36'],
                3:['420','v13'],
                4:['090','3*'],
                
                5:['520','2'],
                6:['420','v12'],
                7:['200','33+'],
                8:['290','2*'],
                9:['420','v12'],
                
# Quicky 16: A' = arcsin(A)                
               10:['300','16'],
               11:['490','v1'],
               12:['377','0'],
               13:['520','2'],
               14:['700','511'], #(1
               
               15:['090','v8'],
               16:['520','2'],   #(5
               17:['770','0'],
               18:['090','v10'],
               19:['590','9'],  #Interesante... una referencia absoluta...estoy en la página 0?
                
               20:['=-5','=983'], #(2
               21:['=507','=468'],
               22:['=-6','=395'],
               23:['=900','=464'],
               24:['=-5','=533'],
               
               25:['=230','=479'],
               26:['=-4','=433'],
               27:['=637','=390'],
               28:['=-3','=1008'],
               29:['=621','=434'],
               
               30:['=0','=100'],  #(3
               31:['=972','=325'],
               32:['=1','=852'],
               33:['=126','=402'],
               34:['420','34'],  #(7
               
               35:['420','2'],
               36:['137','1'],
               37:['700','0'],  #(8
               38:['410','32'],
               39:['500','32'],
               
               40:['410','34'],
               41:['090','v7'],
               42:['017','0+v4'],
               43:['107','-4'],
               44:['400','v2'],
               
               45:['500','34'], #(9
               46:['427','v3'],
               47:['187','v9'],
               48:['510','32'],
               49:['450','2'],
               
               50:['707','-16'],
               51:['127','0'],  #(4
               52:['717','0'],
               53:['440','2'],
               54:['510','2v3'], #(10
               
               55:['280','3v10'],
               56:['520','2'],
               57:['=0','=0'],
               58:['=0','=0'],
               59:['=0','=0'],
               
               60:['=0','=0'],
               61:['=0','=0'],
               62:['=0','=0'],
               63:['=0','=0']}
      
#%% Sector 58: Quicky 18
# Read integer to sac

      BS[58] = {0:['016','0+v9'],
                1:['010','0+v11'],
                2:['107','200'],
                3:['017','v11'],
                4:['017','0+v5'],
                
                5:['600','1+*'], #(1
                6:['106','0'],
                7:['306','16'],
                8:['166','16'],
                9:['357','-1'],
                
                10:['280','-2*'],
                11:['176','10'],
                12:['090','v4'],
                13:['300','-9'],
                14:['026','0+v11'],
                
                15:['380','-1*'],
                16:['016','0+v11'],
                17:['010','0+v5'],  #(2
                18:['590','v1'],
                19:['=76v7n6','=76'], #((3
                
                20:['=76v12n6','=76v8n6'],
                21:['=76v10n6','=76v1n6'],
                22:['=76v8n6','=239'],  #((6
                23:['017','v11'],
                24:['280','v2'], #(7
                
                25:['280','v1'], #(8
                26:['300','18'], #(12
                27:['106','0'],  #(9
                28:['590','9'],
                29:['176','529'],#(4
                
                30:['206','-5v3'],
                31:['377','0'], #(5
                32:['097','-76v6'],
                33:['176','30'],
                34:['080','v12'],
                
                35:['280','v1'], #(10
                36:['990','0'],  #(11
                37:['006','0+v9'],
                38:['=0','=0'],
                39:['=0','=0'],
                
                40:['=0','=0'],
                41:['=0','=0'],
                42:['=0','=0'],
                43:['=0','=0'],
                44:['=0','=0'],
                
                45:['=0','=0'],
                46:['=0','=0'],
                47:['=0','=0'],
                48:['=0','=0'],
                49:['=0','=0'],
                
                50:['=0','=0'],
                51:['=0','=0'],
                52:['=0','=0'],
                53:['=0','=0'],
                54:['=0','=0'],
                
                55:['=0','=0'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
                
#%% Sector 59: Quicky 19 (1st part)
# Read fixed or floating point decimal number to the accumulator

      BS[59] = {0:['015','0+v19'],
                1:['016','0+v20'],
                2:['300','v12n6'],
                3:['210','1v7'],
                4:['210','4+v7'],
                
                5:['400','0'],  #(1
                6:['105','0'],
                7:['300','304'],
                8:['210','v3'],
                9:['300','77'],
                
                10:['210','v4'],
                11:['600','1+*'], #(2
                12:['106','0'],
                13:['306','16'],
                14:['166','16'],
                
                15:['357','-1'],
                16:['280','-2*'],
                17:['016','v9'],
                18:['136','10'],
                19:['090','v21'],
                
                20:['520','v8'],
                21:['990','!=v9'], #(3
                22:['990','-1'],   #(4
                23:['590','v2'],
                24:['176','7'],    #(21
                
                25:['090','v22'],
                26:['206','v7'],   #(5
                27:['175','0'],
                28:['597','v6'],
                29:['106','v14n6'], #(23
                
                30:['600','1+v2'],
                31:['036','1+v2'],
                32:['376','31'],
                33:['290','-4*'],
                34:['376','14'],
                
                35:['287','-1v11n14v6'],
                36:['070','4+v7'],
                37:['090','v26'],
                38:['305','0'],
                39:['590','1v18'],
                
                40:['=213','=1001'],
                41:['=960','=388'],
                42:['=107','=437'],
                43:['=557','=315'],
                44:['=54','=312'],
                
                45:['=222','=284'],
                46:['=27','=0'],
                47:['=481','=381'],
                48:['=14','=0'],
                49:['=512','=312'],
                
                50:['=7','=0'],
                51:['=0','=400'],
                52:['=4','=0'],  #((8
                53:['=0','=320'],
                54:['=9','=0'],
                
                55:['=0','=0'],  #(9
                56:['=29','=0'],
                57:['=0','=384'],
                58:['=-212','=325'],
                59:['=1023','=336'],
                
                60:['=-106','=982'],
                61:['=392','=415'],
                62:['=-53','=664'],
                63:['=172','=461']}
                
#%% Sector 60: Quicky 19 (2nd part)
# Read fixed or floating point decimal number to the accumulator

      BS[60] = {0:['=-26','=738'],
                1:['=611','=343'],
                2:['=-13','=747'],
                3:['=440','=419'],
                4:['=-6','=328'],
                
                5:['=696','=327'],
                6:['=-3','=410'],  #(10
                7:['=614','=409'],
                8:['=v11n6','=v11n6'], #((7  -13,-13
                9:['=0','=v15n6'],     #       0, -7
                10:['=v14n6','=v2n6'], #      -9, -80
                
                11:['=v15n6','=0'],    #      -7, 0
                12:['=1v14n6','=0'],   #      -8, 0
                13:['590','1v2'],
                14:['080','v6'],  #(11
                
                15:['300','312'],
                16:['105','-1'],  #(25
                17:['596','2v1'],
                18:['080','v23'], #(14
                19:['080','v23'],
                
                20:['080','v6'],  #(15
                21:['590','v2'],
                22:['107','69'],  #(24
                23:['186','v25'],
                24:['136','12'],  #(22
                
                25:['176','8'],
                26:['090','v5'],
                27:['300','19'], #(6
                28:['590','v19'],
                29:['090','v6'],
                
                30:['010','4+v7'],
                31:['410','32'],
                32:['015','0+v18'],
                33:['590','v1'],
                34:['010','1v7'], #(12
                
                35:['596','-2v24'],
                36:['440','2v9'], #(26
                37:['410','34'],
                38:['400','32'],
                39:['200','34+'],
                
                40:['320','0'],  #(18
                41:['327','2'],
                42:['290','4*'],
                43:['106','!=v10'],
                44:['360','-1'],
                
                45:['380','2*'],
                46:['106','!=v8'],
                47:['016','3+*'],
                48:['106','-8'],
                49:['290','2*'],
                
                50:['526','0'],
                51:['327','0'],
                52:['186','-3*'],
                53:['105','0'],  #(19
                54:['106','0'],  #(20
                
                55:['280','9'],
                56:['=0','=0'],
                57:['=0','=0'],
                58:['=0','=0'],
                59:['=0','=0'],
                
                60:['=0','=0'],
                61:['=0','=0'],
                62:['=0','=0'],
                63:['=0','=0']}
                

#%% Conversion between programmer codes and machine codes

# This dictionary takes the User function value (human friendly) and returns
# the machine code equivalent
True_function_value = {0:328, 1:272, 2:320, 3:360, 4:352,
                       5:344, 6:336, 7:368, 8:56, 9:128,
                       10:72, 11:'Not used', 12:64, 13:104, 14:96,
                       15:88, 16:80, 17:112, 18:120, 19:'Not used',
                       20:456, 21:400, 22:448, 23:488, 24:480,
                       25:472, 26:464, 27:496, 28:184, 29:256,
                       30:200, 31:'Not used', 32:192, 33:232, 34:224,
                       35:216, 36:208, 37:240, 38:248, 39:'Not used',
                       40:264, 41:280, 42:288, 43:296, 44:304,
                       45:312, 46:816, 47:'Not used', 48:392, 49:136,
                       50:416, 51:424, 52:432, 53:440, 54:176,
                       55:48, 56:'Not used', 57:24, 58:384, 59:8,
                       60:16, 61:144, 62:680, 63:168, 64:408,
                       65:'Not used', 66:'Not used', 67:32, 68:160, 69:40,
                       70:584, 71:152, 72:576, 73:616, 74:608,
                       75:600, 76:592, 77:624, 78:'Not used', 79:'Not used',
                       80:712, 81:'Not used', 82:704, 83:744, 84:736,
                       85:728, 86:720, 87:752, 88:'Not used', 89:'Not used',
                       90:90, 91:'Not used', 92:'Not used', 93:'Not used', 94:'Not used',
                       95:'Not used', 96:'Not used', 97:'Not used', 98:'Not used', 99:0                       
                       }

# This dictionary takes the function machine code and returns
# User function value (human friendly)
User_function_value = {328:0, 272:1, 320:2, 360:3, 352:4,
                       344:5, 336:6, 368:7, 56:8, 128:9,
                       72:10, 64:12, 104:13, 96:14,
                       88:15, 80:16, 112:17, 120:18,
                       456:20, 400:21, 448:22, 488:23, 480:24,
                       472:25, 464:26, 496:27, 184:28, 256:29,
                       200:30, 192:32, 232:33, 224:34,
                       216:35, 208:36, 240:37, 248:38,
                       264:40, 280:41, 288:42, 296:43, 304:44,
                       312:45, 816:46, 392:48, 136:49,
                       416:50, 424:51, 432:52, 440:53, 176:54,
                       48:55, 24:57, 384:58, 8:59,
                       16:60, 144:61, 680:62, 168:63, 408:64,
                       32:67, 160:68, 40:69,
                       584:70, 152:71, 576:72, 616:73, 608:74,
                       600:75, 592:76, 624:77,  
                       712:80, 704:82, 744:83, 736:84,
                       728:85, 720:86, 752:87,
                       90:90,0:99                       
                       }

#%% Parser
# This cell do not emulate any task performed by Ferranti Mercury Computer.
# This cell simply reads an anotated program (using Ferranti's notation)
# and translates it into machine code ready to be excecuted by the instruction
# interpreter (the emulator).

# First, one must select the number of sectors available to parse.
sectors_to_parse = [0,1,2,3,4,5,6,7,8,9,10,11,12]

for sector in sectors_to_parse:#range(12):
    # Each sector contains 64 words (20 bits/word)
    for elemento in range(64):
        # First, we assume that the field contains more than just a number.
        first_field_isnumber = False
        print('-----Begin of a new instruction-----')
        print('Sector: '+str(sector)+', Elemento: '+str(elemento))
        # The list "BS" contains the "raw" instruction (human friendly).
        # BS was constructed by typing in the handwritten
        # "Annotated Input Routine".
        # BS is a 2-dimensional list of strings.
        instruction = list(BS[sector][elemento])

        if instruction[0].find('v') != -1 or instruction[0].find('/') != -1 or instruction[0].find('*') != -1:
            BS_machine[sector][elemento] = 10000000
            continue
        if instruction[1].find('v') != -1 or instruction[1].find('/') != -1 or instruction[1].find('*') != -1:
            BS_machine[sector][elemento] = 10000000
            continue


        print('Compiling first field...')#-----------------------------------
        try:
            # If the string is just a number, make an integer from the string.
            instruction_number = int(instruction[0])
            print('Found instruction '+str(instruction_number))
            # This first field contains the instruction (human friendly number)
            first_field = instruction_number
        except:
            
            if instruction[1].find('v') != -1 or instruction[1].find('/') != -1 or instruction[1].find('*') != -1:
                BS_machine[sector][elemento] = 0
                continue
                
            # When the first field was more than just a number,
            # eliminate commas if present.
            instruction[0] = instruction[0].replace(',','')
            # Then looks for specific key characters...
            
            # The following characters are used when an arbitrary number
            # must be stored in the Computing Store.
            if instruction[0].find('=') != -1:
                instruction[0] = instruction[0].replace('=','')
                first_field = int(instruction[0])
            if instruction[0].find('>') != -1:
                instruction[0] = instruction[0].replace('>','')
                first_field = 2*int(instruction[0])
            if instruction[0].find('!=') != -1:
                instruction[0] = instruction[0].replace('!=','')
                first_field = int(instruction[0])/2
            print('Its not an instruction, but a number: '+instruction[0])
            first_field_isnumber = True

        # Now, let's analyze the second field...
        plus_sign = instruction[1].find('+')
        dot_sign = instruction[1].find('.')
        right_bracket_sign = instruction[1].find(')')
        equal_sign = instruction[1].find('=')   
        minus_sign = instruction[1].find('-')   
        notequ_sign = instruction[1].find('!=')
 

        if instruction[1].find('v') != -1 or instruction[1].find('/') != -1 or instruction[1].find('*') != -1:
             BS_machine[sector][elemento] = 0
             continue
 
           
        print('Compiling second field...')#--------------------------------
        # If there is a dot, we must work a little bit...
        if dot_sign != -1:
            if plus_sign != -1:
                instruction[1] = instruction[1].replace('+','')
                print('Plus sign present')
            # The field must be splitted in two.
            elements = instruction[1].split(sep='.', maxsplit = 2)
            # If inequality sign is present, address is obtained as 32*a+b
            if notequ_sign != -1:
                elements[0] = elements[0].replace('!=','')
                address = 32*int(elements[0])+int(int(elements[1])/2)
            # If it is not present, address is obtained as 64*a+b
            else:
                address = 64*int(elements[0])+int(elements[1])
                
            # According to the type of instruction, the Address field must be
            # modified.
            if (int(first_field/10) == 60) or (int(first_field/10) == 61) or (int(first_field/10) == 63) or (int(first_field/10) <= 7) or (int(first_field/10) >=20 and int(first_field/10) <= 27):
                if plus_sign != -1:
                    second_field = address*2+1
                else:
                    second_field = address*2
            else:
                second_field = address
        else:
            if right_bracket_sign == -1 and equal_sign == -1:                
                if (int(first_field/10) == 60) or (int(first_field/10) == 61) or (int(first_field/10) == 63) or (int(first_field/10) <= 7) or (int(first_field/10) >=20 and int(first_field/10) <= 27):
                    if plus_sign != -1:
                        instruction[1] = instruction[1].replace('+','')
                        print('Plus sing present')
                        address = int(instruction[1])
                        address = address*2+1
                        second_field = address
                    else:
                        address = int(instruction[1])
                        second_field = address*2
                else:
                    second_field = int(instruction[1])
                    
        if minus_sign != -1:
            address = 1024 + int(instruction[1])
            second_field = address

        if equal_sign != -1 and notequ_sign == -1:
            instruction[1] = instruction[1].replace('=','')            
            second_field = int(instruction[1])
            print('Is not an address, is number '+ str(second_field))

                                        #to refer to second page of memory

        print('Original second field was ' + BS[sector][elemento][1])
        print('Compiled second field is ' + str(second_field))

        if first_field_isnumber == False:
            machine_instruction = (True_function_value[int(first_field/10)]+(first_field%10))*1024+second_field
        else:
            machine_instruction = first_field*1024 + second_field
            
        print('Machine value = '+str(machine_instruction))
        BS_machine[sector][elemento] = machine_instruction
        

#%% Computing Store initial state for Tele-Output
# If this cell is executed, next cell (Tele-Input) must be avoided.

# Tele-Output just needs Sector 0 and 1 from drum to be loaded at page 0 and 1
# in the Magnetic Core Memory (Computing Store).
# Then it automatically loads Sector 3 in page 1 to perform some tasks.
computing_store[128:] = 0
computing_store[:64] = list(BS_machine[0])
computing_store[64:128] = list(BS_machine[1])

# These lines make the Magnetic Drum Memory (Drum) sectors available to the
# emulator.
backing_store_sectorized[0:12] = list(BS_machine[0:12])
#backing_store_sectorized[1] = list(BS_machine[1])
#backing_store_sectorized[2] = list(BS_machine[2])
#backing_store_sectorized[3] = list(BS_machine[3])
#backing_store_sectorized[4] = list(BS_machine[4])
#backing_store_sectorized[5] = list(BS_machine[5])
#backing_store_sectorized[6] = list(BS_machine[6])
backing_store_sectorized[24] = list(BS_machine[24])


# To make a "fresh" start, machine virtual registers must be cleared 
#Clear B_register
B_register = np.zeros(8, dtype='i')

# Clear tape (this is not emulated machine memory, but a virtual storage media)
# The size of this media is arbitrary (It's just a virtual paper tape!).
# Size 400 is enough to accomodate a single backed-up sector.
tape = np.zeros(1200, dtype='i') 
# This index tells the emulator at which position is the virtual tape reader.
tape_index = 0

#Clear test_registers
B_test = 0
sac_test = 0

#Default... maybe not necessary
sector_selected = 0

#Selects Tele-output program
switches = '0b0000001000'

#Tele-output starts at address 0 or 63 (See Annotated Input Routine) 
program_counter = 0

# Reset instruction counter (this is a debugging variable, not part of the
# original machine)
instructions_executed = 0

#For emulation, to introduce switches interaction automatically
tele_output = True

#Activate while loop
run = True

#Set True for more information while debugging
verbose = False


#%% Computing Store initial state for Tele-input
# Reads tape, assembles binary instructions (20 bits) from 4 x 5bit characters,
# and loads data in computing_store[128:192] (page 3 of magnetic core memory).
# and in Drum sector indicated in tape footer.

# First, It's necessary to load sector 1 of drum memory (storage memory).
# into page 0 of magnetic core memory (computing memory).
computing_store[:64] = list(BS_machine[1])

# Tele-imput starts at address 63
program_counter = 63

# Introduce a virtual tape in the virtual reader.
tape_index = 0

# Reset instruction counter (this is a debugging variable, not part of the
# machine)
instructions_executed = 0

# Activate while loop
run = True

tele_output = False

# Set True for more information while debugging
verbose = False
        
#%% Main Loop
# This is the core of the emulator.

while run == True:
    #This is an instruction counter for debugging
    instructions_executed = instructions_executed + 1
    
    # This load the instruction for emulation from Magnetic Core Memory
    # (Computing Store)
    # The instruction is a 20 bit word:
    # Bits 0-9: Address/literal
    # Bits 10-12: B-Register selector (and other special uses)
    # Bits 13-19: Machine Instruction
    fetched_instruction = computing_store[program_counter]

    # This obtain the Machine Instruction (13-19 bits) from the complete
    # instruction (20 bits).
    # The Machine Instruction must be converted to a the Human Readable
    # Instruction,
    # by using "User_function_value" table... so we obtain the
    # "base_instruction".
    base_instruction = User_function_value[int(fetched_instruction/8192)*8]

    # This "base_instruction" must be formatted as a two digit string, so the
    # emulator can search for one specific action to be taken
    # (~92 instructions were available in Ferranti Mercury).
    if base_instruction < 10:
        base_instruction = '0'+str(base_instruction)
    else:
        base_instruction = str(base_instruction)        

    # This obtain the B-Register (10-12 bits) from the complete instruction
    # (20 bits).
    fetched_B_register = int(fetched_instruction/1024)%8
    
    # This obtain the Address or literal -numeric constant- (0-9 bits) from
    # the complete instruction (20 bits).    
    literal = fetched_instruction%1024

    # If "verbose" flag is set, the action of each emulation step is shown.
    if verbose == True:
        print('Program_counter: '+str(program_counter))
        print('Fetched_Instruction: '+ str(fetched_instruction))
        print('Instruction: '+ base_instruction)
        print('B-Register: '+ str(fetched_B_register))
        print('Literal: '+ str(literal))
        print ('Action: '+ str(commands[base_instruction][0]))

    # This line selects the emulator function to perform the task indicated by
    # the "base_instruction" 
    func = switcher.get(str(base_instruction),lambda: "Inexistent instruction")
    # This line executes the instruction
    func()

    # "program_counter" is an emulator register that indicates which
    # position of the Computing Store will be read in the next step.
    # When a Jump is needed, the emulator changes this variable considering
    # that a 1 is going to be added anyway.
    program_counter = program_counter + 1
    
    # This automatic actions on the switches are needed when "Tele-output"
    # routine is activated.
    # Introduce sectors for tele-output automatically.
    if tele_output == True:        
        if instructions_executed == 23:    # First Sector Input Sequence:
            switches = '0b0000000000'      # Tele-output waits for the switched
        if instructions_executed == 1720:  # to be cleared before starting (*).
            switches = '0b0000000001'      # "Hundreds" digit tapped.
        if instructions_executed == 1732:
            switches = '0b0000000000'      # Tele-output waits for the switched
        if instructions_executed == 3428:  # to be released.
            switches = '0b0000000001'      # "Tens" digit tapped.
        if instructions_executed == 3440:
            switches = '0b0000000000'      # Tele-output waits for the switched
        if instructions_executed == 5136:  # to be released.
            switches = '0b0000010000'      # "Units" digit tapped.
        if instructions_executed == 5171:  
            switches = '0b0000000000'      # Last Sector Input Sequence:
        if instructions_executed == 6867:  # (*)
            switches = '0b0000000001'      # "Hundreds" digit tapped.
        if instructions_executed == 6879:
            switches = '0b0000000000'
        if instructions_executed == 8574:
            switches = '0b0000000001'      # "Tens" digit tapped.
        if instructions_executed == 8587:
            switches = '0b0000000000'
        if instructions_executed == 10282:
            switches = '0b0000010000'      # "Units" digit tapped.
        if instructions_executed == 33000:
            switches = '0b0000000000'        
        if instructions_executed == 35000: # Tele-output waits for a final
            switches = '0b0000000001'      # tapping. Eg: "000"
        if instructions_executed == 37000:
            switches = '0b0000000000'
        if instructions_executed == 39000:
            switches = '0b0000000001'
        if instructions_executed == 41000:
            switches = '0b0000000000'
        if instructions_executed == 43000:
            switches = '0b0000000001'
        if instructions_executed == 45000:
            switches = '0b0000000000'

    # Again, "verbose" flag allows extra informations about emulator state.
    if verbose == True:
        print('Instructions excecuted: ' + str(instructions_executed))
        print('                          ')
        print('-----NEXT_INSTRUCTION-----')

# Some additional execution contron can be used while debugging the emulator.
#        if instructions_executed > 11000: #767: #
#        if tape_index >= 300:
#            input('Press Enter to continue...')  #For debugging purposes only
    
# It is possible to force the emulator to stop when a certain condition is met.
#        if program_counter >64:
#            run = False


#%% Tape visualizer
# This cell allows to visualize the contents of paper tape punched through
# tele-output.

plt.plot(tape[:])
        
#%% Backing Store visualizer
#backing_store_sectorized[2]=np.zeros(64,dtype=int)
#backing_store_sectorized[3]=np.zeros(64,dtype=int)
#backing_store_sectorized[4]=np.zeros(64,dtype=int)
#backing_store_sectorized[5]=np.zeros(64,dtype=int)
#backing_store_sectorized[6]=np.zeros(64,dtype=int)

plt.imshow(backing_store_sectorized[:25], cmap='jet')
#%%
plt.imshow(BS_machine[:25], cmap='jet')

#%% Backing Store Instruction visualizer
graficar_BSS = np.zeros((25,64))
for i in range(64):
    for j in range(25):
        try:
            graficar_BSS[j][i] = User_function_value[int(backing_store_sectorized[j][i]/8192)*8]
        except:
            print(int(backing_store_sectorized[j][i]/8192)*8)
            graficar_BSS[j][i] = 0
plt.imshow(graficar_BSS, cmap='jet', vmax=100)

#%% Backing Store Address visualizer
graficar_BSS = np.zeros((12,64))
for i in range(64):
    for j in range(12):
        graficar_BSS[j][i] = backing_store_sectorized[j][i]%1024

plt.imshow(graficar_BSS, cmap='jet', vmax=1024)

#%% Backing Store B-register visualizer
graficar_BSS = np.zeros((12,64))
for i in range(64):
    for j in range(12):
        graficar_BSS[j][i] = int(backing_store_sectorized[j][i]/8192)%8

plt.imshow(graficar_BSS, cmap='jet')

#%% Computing Store visualizer
plt.plot(computing_store[:])
plt.xlim(0, 556-1)
#%% Computing Store Instruction Visualizer
plt.plot([int(number/1024) for number in computing_store[:]])
plt.xlim(0, 556-1)


#%% Sector visualizer
plt.plot(backing_store_sectorized[14])


    




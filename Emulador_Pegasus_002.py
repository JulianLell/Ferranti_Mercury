#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 22 23:23:09 2020

@author: julian
"""
import numpy as np

MEM_REG = np.zeros(64, dtype=np.int64)
# Memoria de programa y registros
# Bloques 0 a 5 memoria de programa, de 8 words por bloque
# Bloque 7 Acumuladores,son 8 words de 39 bits
# Special Registers son 15,16,17,24, 32-37
MEM_REG[0o32:0o40] = [-1, 0.5, 2**-10, 2**-13, 2**-16, 7/8]
# Parte de los registros especiales contienen constantes. 

MEM_MAIN = np.zeros(9088, dtype=np.int64)
# 16 bloques de 8 words de delay line memory = 128 words
# Memoria de tambor R/W: 55 pistas de 16 bloques, 8 words por bloque = 7040 words 
# Memoria de tambor ROM: 16 pistas de 16 bloques, 8 words por bloque = 2048 words
# Solo se pueden acceder a 8192 words, con un address de 13 bit.
# Hay un switch manual que conecta la ROM1 o la ROM2, a los 1024 words finales. 
MEM_MAIN[:128] = 0  #Borro los 16 primeros bloques, porque es RAM (delay line)


Program_ASM = np.zeros([9088,4], dtype=np.int)
Program = np.zeros(9088, dtype=np.int64)


orden = np.zeros(2, dtype=np.int64)

OVR = False

Program_ASM = np.loadtxt('test_001.asm', dtype=int, delimiter=',')

for j in range(int(len(Program_ASM)/2)):
    Program[j] = (8*int(Program_ASM[2*j,0]/10) + (Program_ASM[2*j,0]%10))*(2**30) 
    Program[j] += Program_ASM[2*j,1]*(2**27)
    Program[j] += (8*int(Program_ASM[2*j,2]/10) + (Program_ASM[2*j,2]%10))*(2**21)
    Program[j] += Program_ASM[2*j,3]*(2**18)

    Program[j] += (8*int(Program_ASM[2*j+1,0]/10) + (Program_ASM[2*j+1,0]%10))*(2**12) 
    Program[j] += Program_ASM[2*j+1,1]*(2**9)
    Program[j] += (8*int(Program_ASM[2*j+1,2]/10) + (Program_ASM[2*j+1,2]%10))*(8)
    Program[j] += Program_ASM[2*j+1,3]
    
print(Program_ASM)
print(oct(Program[0]))


#Hasta que programe la parte del "Initial Orders", debo pasar la MAIN MEMORY
#a mano a la ORDINARY MEMORY
for k in range(0,64):
    MEM_REG[k] = Program[k]





#%%
    
#Instrucciones:
# Los bits se van a numerar de izquierda a derecha, para compatibilidad con la bibliografía original
# Instrucción "a" (1-19)
# bit 0 -> COMPLETAR
# bit 1-7 -> Registro ordinario
# bit 8-10 -> Acumulador
# bit 11-16 -> Instrucción
# bit 17-19 -> Modificador

# Instrucción "b" (20-38)
# bit 20-26 -> Registro ordinario
# bit 27-29 -> Acumulador
# bit 30-35 -> Instrucción
# bit 36-38 -> Modificador


#00.01.02.03.04.05.06.07.08.09.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29.30.31.32.33.34.35.36.37.38    
#38.37.36.35.34.33.32.31.30.29.28.27.26.25.24.23.22.21.20.19.18.17.16.15.14.13.12.11.10.09.08.07.06.05.04.03.02.01.00
    

#np.savetxt('memory.fer', Program, delimiter=',')






#pc = -1
pc = 2
run = True
Accumulator = 0
multiplication = np.zeros(0, dtype=np.float128)
multiplication_buf = np.zeros(0, dtype=np.float128)

Program_ASM = [2**22 , 0 , 0, 0]

while run == True:
    pc += 1
    if pc == 0o60:
        pc = 0
    print('PC =',pc)    

    orden[0] = int((MEM_REG[pc] & 0o3777776000000)/2**18)
    orden[1] = MEM_REG[pc] & 0o1777777

#Desde aquí el núcleo del emulador
    for i in range(0,2):
     if run == True:   
        inst_field = int((orden[i] & 0o770)/8)  #0o770 es una máscara para seleccionar los bits 11-16 (Función)
#        print('inst_field',oct(inst_field))
        acum_field = int((orden[i] & 0o7000)/(2**9))+0o70
#        print('acum_field',oct(acum_field))
        reg_field = int((orden[i] & 0o1770000)/(2**12))
#        print('reg_field',oct(reg_field))
#        print('parte',i)

        if inst_field == 0o0: 
            print('Instrucción 00')
            MEM_REG[acum_field] = MEM_REG[reg_field]
            
        if inst_field == 0o1:
            print('Instrucción 01')
            MEM_REG[acum_field] += MEM_REG[reg_field]
            
        if inst_field == 0o2:
            print('Instrucción 02')
            MEM_REG[acum_field] = (-1)*MEM_REG[reg_field]

        if inst_field == 0o3:
            print('Instrucción 03')
            MEM_REG[acum_field] -= MEM_REG[reg_field]

        if inst_field == 0o4:
            print('Instrucción 04')
            MEM_REG[acum_field] = MEM_REG[reg_field] - MEM_REG[acum_field]

        if inst_field == 0o5:
            print('Instrucción 05')
            MEM_REG[acum_field] = MEM_REG[acum_field] & MEM_REG[reg_field]

        if inst_field == 0o6:
            print('Instrucción 06')
            MEM_REG[acum_field] ^= MEM_REG[reg_field]



        if inst_field == 0o10: 
            print('Instrucción 10')
            MEM_REG[reg_field] = MEM_REG[acum_field]
            
        if inst_field == 0o11:
            print('Instrucción 11')
            MEM_REG[reg_field] += MEM_REG[acum_field]
            
        if inst_field == 0o12:
            print('Instrucción 12')
            MEM_REG[reg_field] = (-1)*MEM_REG[acum_field]

        if inst_field == 0o13:
            print('Instrucción 13')
            MEM_REG[reg_field] -= MEM_REG[acum_field]

        if inst_field == 0o14:
            print('Instrucción 14')
            MEM_REG[reg_field] = MEM_REG[acum_field] - MEM_REG[reg_field]

        if inst_field == 0o15:
            print('Instrucción 15')
            MEM_REG[reg_field] = MEM_REG[reg_field] & MEM_REG[acum_field]

        if inst_field == 0o16:
            print('Instrucción 16')
            MEM_REG[reg_field] ^= MEM_REG[acum_field]



        if inst_field == 0o20: 
            print('Instrucción 20')
            multiplication = MEM_REG[reg_field]*MEM_REG[acum_field]
            MEM_REG[0o7] = multiplication & 0o3777777777777
            MEM_REG[0o6] = int(multiplication/2**39)
            
        if inst_field == 0o21:
            print('Instrucción 21')
            multiplication = MEM_REG[reg_field]*MEM_REG[acum_field]
            MEM_REG[0o7] = multiplication & 0o3777777777777
            MEM_REG[0o6] = int(multiplication/(2**39))
            #Tengo que redondear para arriba lo que va en 07??
            
        if inst_field == 0o22:
            print('Instrucción 22')
            multiplication = MEM_REG[reg_field]*MEM_REG[acum_field]
            multiplication_buf = MEM_REG[0o7] + MEM_REG[0o6]*(2**38) 
            MEM_REG[0o7] = (multiplication + multiplication_buf) & 0o3777777777777
            MEM_REG[0o6] = int((multiplication + multiplication_buf)/(2**39))

        if inst_field == 0o23:
            print('Instrucción 23')
            #Pendiente

        if inst_field == 0o24:
            print('Instrucción 24')
            MEM_REG[0o7] = int((MEM_REG[acum_field]*2**38 + MEM_REG[0o7])/MEM_REG[reg_field]) 
            MEM_REG[0o6] = (MEM_REG[acum_field]*2**38 + MEM_REG[0o7])%MEM_REG[reg_field] 

        if inst_field == 0o25:
            print('Instrucción 25')
            #Es similar a 24, ver luego
            MEM_REG[0o7] = int((MEM_REG[acum_field]*2**38 + MEM_REG[0o7])/MEM_REG[reg_field]) 
            MEM_REG[0o6] = (MEM_REG[acum_field]*2**38 + MEM_REG[0o7])%MEM_REG[reg_field] 

        if inst_field == 0o26:
            print('Instrucción 26')
            MEM_REG[0o7] = int(MEM_REG[acum_field]/MEM_REG[reg_field]) 
            MEM_REG[0o6] = MEM_REG[acum_field]%MEM_REG[reg_field]

        if inst_field == 0o27:
            print('Instrucción 27')
            if acum_field == 7:
                MEM_REG[0o7] = 2*MEM_REG[reg_field]*MEM_REG[0o7] + (int(MEM_REG[0o6]/(2**30)) & 0o17)
                MEM_REG[0o6] = MEM_REG[0o6]*(2**6)
            else:
                MEM_REG[0o7] = 2*MEM_REG[reg_field]*MEM_REG[0o7] + MEM_REG[acum_field]               
                MEM_REG[0o6] = 0


        if inst_field == 0o37:
            print('Instrucción 37')
            MEM_REG[0o7] = (2*MEM_REG[reg_field]*MEM_REG[0o7]) % MEM_REG[acum_field]
            MEM_REG[0o6] = (2**6)*MEM_REG[0o6] + int((2*MEM_REG[reg_field]*MEM_REG[0o7])/MEM_REG[acum_field])
    
    
        if inst_field == 0o40:
            print('Instrucción 40')
            MEM_REG[acum_field] = reg_field
    
        if inst_field == 0o41:
            print('Instrucción 41')
            MEM_REG[acum_field] += reg_field
    
        if inst_field == 0o42:
            print('Instrucción 42')
            MEM_REG[acum_field] = (-1)*reg_field
    
        if inst_field == 0o43:
            print('Instrucción 43')
            MEM_REG[acum_field] -= reg_field

        if inst_field == 0o44:
            print('Instrucción 44')
            MEM_REG[acum_field] = reg_field - MEM_REG[acum_field]
            
        if inst_field == 0o45:
            print('Instrucción 45')
            MEM_REG[acum_field] = MEM_REG[acum_field] & reg_field
            
        if inst_field == 0o46:
            print('Instrucción 46')
            MEM_REG[acum_field] = MEM_REG[acum_field] ^ reg_field        



        if inst_field == 0o50:
            print('Instrucción 50')
            MEM_REG[acum_field] = (2**reg_field)*MEM_REG[acum_field]        
    
        if inst_field == 0o51:
            print('Instrucción 51')
            MEM_REG[acum_field] = round(MEM_REG[acum_field]/(2**reg_field))        
    
        if inst_field == 0o52:
            print('Instrucción 52')
            MEM_REG[acum_field] = ((2**reg_field)*MEM_REG[acum_field]) & 3777777777777       
    
        if inst_field == 0o53:
            print('Instrucción 53')
            MEM_REG[acum_field] = int(MEM_REG[acum_field]/(2**reg_field))        

        if inst_field == 0o54:
            print('Instrucción 54')
            MEM_REG[0o7] = ((2**reg_field)*MEM_REG[0o7]) & 3777777777777       
            MEM_REG[0o6] = ((2**reg_field)*MEM_REG[0o6]) + ((2**reg_field)*MEM_REG[0o7]) & 77777774000000000000       
            #Verificar, sobre todo el último "and"

        if inst_field == 0o55:
            print('Instrucción 55')
            if reg_field > 0:
                MEM_REG[0o7] = int(MEM_REG[0o7]/(2**reg_field)) + (MEM_REG[0o6]%(2**reg_field))*(2**(39-reg_field))       
                MEM_REG[0o6] = int(MEM_REG[0o6]/(2**reg_field))
            #Verificar, sobre todo el último "and"

        if inst_field == 0o56:
            print('Instrucción 56: Normalize')
            #Pendiente

        if inst_field == 0o57:
            print('Instrucción 57')
            #Pendiente



        if inst_field == 0o60:
            print('Instrucción 60')
            if MEM_REG[acum_field] == 0:
                pc = reg_field

        if inst_field == 0o61:
            print('Instrucción 61')
            if MEM_REG[acum_field] != 0:
                pc = reg_field

        if inst_field == 0o62:
            print('Instrucción 62')
            if MEM_REG[acum_field] >= 0:
                pc = reg_field

        if inst_field == 0o63:
            print('Instrucción 63')
            if MEM_REG[acum_field] < 0:
                pc = reg_field

        if inst_field == 0o64:
            print('Instrucción 64')
            if OVR == False:
                pc = reg_field
            else:
                OVR = False

        if inst_field == 0o65:
            print('Instrucción 65')
            if OVR == True:
                pc = reg_field
                OVR = False

        if inst_field == 0o66:
            print('Instrucción 66')
            #Esto es con el modificador (Los últimos bit de la instrucción)
    
        if inst_field == 0o67:
            print('Instrucción 67')
            #Esto es con el modificador (Los últimos bit de la instrucción)



        if inst_field == 0o70:
            print('Instrucción 70: Single-word read')
            MEM_REG[0o1] = MEM_MAIN[reg_field*8+acum_field]

        if inst_field == 0o71:
            print('Instrucción 71: Single-word write')
            if OVR == True:
                run = False
            else:
                MEM_MAIN[reg_field*8+acum_field] = MEM_REG[0o1]

        if inst_field == 0o72:
            print('Instrucción 72: Block read')
            MEM_PROG[acum_field*8+1:acum_field*8+8] =  MEM_MAIN[reg_field*8+1:reg_field*8+8]
    
        if inst_field == 0o73:
            print('Instrucción 73: Block write')
            if OVR == True:
                run = False
            else:
                MEM_MAIN[reg_field*8+1:reg_field*8+8] = MEM_PROG[acum_field*8+1:acum_field*8+8]
    
        if inst_field == 0o74:
            print('Instrucción 74: External conditioning')
            #Completar
    
        if inst_field == 0o76:
            print('Instrucción 76: Buffer transfer')
            #Completar

        if inst_field == 0o77:
            print('Instrucción 77: Stop')
            run = False

    
#    if pc + 1 == 20:#len(Program):
#        run = False
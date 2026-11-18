10 REM FLOAT: what an empty sideways socket (bank 8) reads on a Master
20 REM The screen filled with one byte V; 64 reads of bank 8's &8008; the values read, counted
30 DIM C% 200,B% 64,H%(255),S$(3)
40 FOR I%=0 TO 2 STEP 2:P%=C%
50 [OPT I%
60 .rd SEI:LDA &F4:PHA:LDA #8:STA &F4:STA &FE30:LDX #63
70 .l LDA &8008:STA B%,X:DEX:BPL l
80 PLA:STA &F4:STA &FE30:CLI:RTS
90 ]:NEXT
100 FOR R%=0 TO 3
110 M%=7-6*(R% DIV 2):V%=&41+&19*(R% MOD 2)
120 MODE M%:VDU 23,1,0;0;0;0;
130 IF M%=7 S%=&7C00 ELSE S%=&3000
140 FOR A%=S% TO &7FFC STEP 4:!A%=V%*&1010101:NEXT
150 CALL rd
160 FOR I%=0 TO 255:H%(I%)=0:NEXT
170 FOR I%=0 TO 63:H%(B%?I%)=H%(B%?I%)+1:NEXT
180 S$(R%)="MODE "+STR$M%+", screen &"+STR$~V%+": "
190 FOR I%=0 TO 255:IF H%(I%) S$(R%)=S$(R%)+"&"+STR$~I%+"x"+STR$H%(I%)+" "
200 NEXT
210 NEXT
220 MODE 7
230 PRINT "Bank 8 in the ROM table: &";~?&2A9
240 FOR R%=0 TO 3:PRINT S$(R%):NEXT

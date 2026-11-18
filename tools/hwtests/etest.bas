10 REM ETEST: code run from HAZEL (Y set): which RAM does it see at &3000?
20 REM main &3000 = &11, shadow &3000 = &22; both put back after
30 DIM C% 300
40 FOR I%=0 TO 2 STEP 2:P%=C%
50 [OPT I%
60 .rd LDA &3000:STA &70:RTS
70 .run SEI:LDA &FE34:STA acc
80 LDX #5
90 .sv LDA &DE00,X:STA save,X:LDA rd,X:STA &DE00,X:DEX:BPL sv
100 LDA &3000:STA m0:LDA #&11:STA &3000
110 LDA acc:ORA #4:STA &FE34:LDA &3000:STA s0:LDA #&22:STA &3000
120 LDA acc:AND #&F1:ORA flags:STA &FE34
130 JSR &DE00
140 LDA acc:ORA #4:STA &FE34:LDA s0:STA &3000
150 LDA acc:STA &FE34:LDA m0:STA &3000
160 LDX #5
170 .rs LDA save,X:STA &DE00,X:DEX:BPL rs
180 CLI:RTS
190 .acc EQUB 0:.m0 EQUB 0:.s0 EQUB 0:.flags EQUB 0:.save EQUS "      "
200 ]:NEXT
210 PRINT "ACCCON was &";~?&FE34
220 FOR F%=0 TO 3:?flags=8+2*(F% AND 1)+4*(F% DIV 2):CALL run
230 PRINT "Y=1 E=";F% AND 1;" X=";F% DIV 2;": &3000 read &";~?&70;
240 IF ?&70=&11 PRINT " (main)" ELSE IF ?&70=&22 PRINT " (shadow)" ELSE PRINT " (?)"
250 NEXT

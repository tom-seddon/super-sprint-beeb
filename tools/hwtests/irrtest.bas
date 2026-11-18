10 REM IRRTEST: does ACCCON bit 7 (IRR) raise an IRQ?
20 REM Both VIAs' interrupts off; a short CLI window; IRQs counted through IRQ1V
30 DIM C% 300
40 FOR I%=0 TO 2 STEP 2:P%=C%
50 [OPT I%
60 .h INC cnt:LDA &FE34:STA seen:AND #&7F:STA &FE34:LDA &FC:RTI
70 .run SEI:LDA &FE4E:STA ier1:LDA &FE6E:STA ier2:LDA #&7F:STA &FE4E:STA &FE6E
80 LDA &204:STA old:LDA &205:STA old+1:LDA #h MOD 256:STA &204:LDA #h DIV 256:STA &205
90 LDA #0:STA cnt:STA seen
100 LDA &FE34:AND #&7F:ORA mode:STA &FE34:LDA &FE34:STA back
110 CLI:LDX #0
120 .w DEX:BNE w
130 SEI:LDA &FE34:AND #&7F:STA &FE34
140 LDA old:STA &204:LDA old+1:STA &205
150 LDA ier1:ORA #&80:STA &FE4E:LDA ier2:ORA #&80:STA &FE6E:CLI:RTS
160 .cnt EQUB 0:.seen EQUB 0:.back EQUB 0:.old EQUW 0:.ier1 EQUB 0:.ier2 EQUB 0:.mode EQUB 0
170 ]:NEXT
180 ?mode=0:CALL run
190 PRINT "IRR clear: ";?cnt;" IRQs, ACCCON read &";~?back
200 ?mode=&80:CALL run
210 PRINT "IRR set:   ";?cnt;" IRQs, ACCCON read &";~?back
220 IF ?cnt>0 PRINT "  ACCCON in the handler: &";~?seen

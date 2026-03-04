
CoordMode "Mouse", "Screen"
SetDefaultMouseSpeed 8
MouseMove 1834, 488
Sleep 100          ; <-- Garante que o mouse parou antes de clicar
Click "Down"
Sleep 80           ; <-- Clique seco mas firme
Click "Up"
Sleep 150          ; <-- PAUSA VITAL: Espera o jogo processar o clique antes de mover
MouseMove 1894, 488, 10 ; <-- Desvia suavemente para limpar o hover

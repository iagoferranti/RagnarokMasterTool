; pressionar_tecla.ahk - VERSÃO SEGURANÇA TOTAL (ANTI-MINIMIZAR)
#Requires AutoHotkey v2.0
CoordMode "Mouse", "Screen"

; Bloqueia teclas que o Windows usa para minimizar janelas
LWin::Return
RWin::Return
!Tab::Return
!Esc::Return
#d::Return
#m::Return

OnExit(LiberaMouse)

tecla := A_Args[1]

; --- BLOCO 1: LIMPEZA BRUTA COM TRAVA ---
if (tecla = "limpar" && A_Args.Length >= 3) {
    posX := A_Args[2]
    posY := A_Args[3]
    
    BlockInput "MouseMove"
    MouseMove posX, posY, 0
    Sleep 200
    Click "Down", posX, posY
    Sleep 50
    Click "Up", posX, posY
    Sleep 300
    
    Loop 45 {
        Send "{Backspace}"
        Send "{Delete}"
    }
    BlockInput "MouseMoveOff"
}

; --- BLOCO 2: CLIQUE SIMPLES COM TRAVA ---
else if (A_Args.Length >= 2 && IsNumber(A_Args[1])) {
    posX := A_Args[1]
    posY := A_Args[2]
    
    BlockInput "MouseMove"
    MouseMove posX, posY, 0
    Sleep 150
    Click "Down", posX, posY
    Sleep 50
    Click "Up", posX, posY
    BlockInput "MouseMoveOff"
}

; --- BLOCO 3: TECLAS ESPECÍFICAS ---
else if (tecla = "tab") {
    Send "{Tab}"
} else if (tecla = "enter") {
    Send "{Enter}"
} else if (tecla = "esc") {
    Send "{Esc}"
}

LiberaMouse(*) {
    BlockInput "MouseMoveOff"
}

ExitApp
; digitar.ahk - v3 (Segurança para senhas com símbolos)
#Requires AutoHotkey v2.0

texto := A_Args[1]

if (texto != "") {
    ; O modo {Raw} faz o # ser apenas um # e não a tecla Windows
    Send "{Raw}" . texto
}
ExitApp
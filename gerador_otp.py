import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Tenta importar pyotp
try:
    import pyotp
    TEM_PYOTP = True
except ImportError:
    TEM_PYOTP = False

# === INTEGRAÇÃO COM A ARQUITETURA ===
from fabricador import config
from fabricador.modules.files import carregar_json_seguro, salvar_json_seguro

# Tenta importar o gerenciador de prêmios para o reprocessamento
try:
    import premios_manager
except ImportError:
    premios_manager = None

# --- CONFIGURAÇÕES VISUAIS PREMIUM ---
COR_FUNDO = "#1e1e1e"       
COR_FUNDO_CAMPO = "#2d2d30" 
COR_TEXTO = "#ffffff"       
COR_TEXTO_SEC = "#cccccc"   
COR_DESTAQUE = "#007acc"    
COR_BOTAO = "#3e3e42"       
COR_SUCESSO = "#28a745"     
COR_ERRO = "#d9534f"

# Caminho para o arquivo de prêmios
PREMIOS_FILTRADOS_REL = os.path.join(config.BASE_PATH, "premios", "filtrado", "premios_filtrados.txt")

def carregar_emails_e_premios_filtrados():
    path = PREMIOS_FILTRADOS_REL
    emails = set()
    premios_map = {}
    if not os.path.exists(path): return emails, premios_map

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or " | " not in s: continue
                try:
                    after = s.split("] ", 1)[1]
                    email = after.split(" | ", 1)[0].strip().lower()
                    if not email: continue
                    emails.add(email)
                    if email not in premios_map: premios_map[email] = []
                    if s not in premios_map[email]: premios_map[email].append(s)
                except: continue
    except: pass
    return emails, premios_map

class OTPManager:
    def __init__(self, root, modo="todos"):
        self.root = root
        self.modo = modo # "todos", "premios", "apenas_novas"
        self.root.title(f"Ragnarok Helper | Modo: {modo.upper()}")
        self.root.geometry("500x680")
        self.root.configure(bg=COR_FUNDO)
        self.root.resizable(False, False)

        self.emails_com_premio, self.premios_map = carregar_emails_e_premios_filtrados()
        self.contas = self.carregar_e_filtrar_dados()
        self.conta_atual = None

        self.setup_styles()
        self.criar_interface()
        self.atualizar_loop()

    def carregar_e_filtrar_dados(self):
        db_global = {}
        arquivos = [config.ARQUIVO_PRINCIPAL, config.ARQUIVO_SALVAR] 
        for caminho in arquivos:
            if os.path.exists(caminho):
                dados = carregar_json_seguro(caminho)
                for c in dados:
                    email = c.get("email", "").strip().lower()
                    if email: db_global[email] = c

        contas_filtradas = []
        if self.modo == "apenas_novas":
            contas_filtradas = [c for c in db_global.values() if c.get('char_created') is False]
        elif self.modo == "premios":
            contas_filtradas = [c for c in db_global.values() if c['email'] in self.emails_com_premio and not c.get('reward_claimed', False)]
        else:
            contas_filtradas = list(db_global.values())

        contas_filtradas.sort(key=lambda x: x.get("email", "").lower())
        return contas_filtradas

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Horizontal.TProgressbar", thickness=10, troughcolor=COR_FUNDO_CAMPO)
        self.style.map('TCombobox', fieldbackground=[('readonly', COR_FUNDO_CAMPO)])

    def criar_interface(self):
        topo = tk.Frame(self.root, bg=COR_FUNDO)
        topo.pack(pady=15)
        
        txt_titulo = {"todos": "TODAS AS CONTAS", "premios": "PRÊMIOS PENDENTES", "apenas_novas": "FILA DE CRIAÇÃO (CHAR)"}
        cor_tit = {"todos": COR_DESTAQUE, "premios": COR_SUCESSO, "apenas_novas": "#f1c40f"}
        
        tk.Label(topo, text=txt_titulo.get(self.modo), font=("Segoe UI", 16, "bold"), bg=COR_FUNDO, fg=cor_tit.get(self.modo)).pack()
        tk.Label(topo, text=f"{len(self.contas)} Contas na Fila", font=("Segoe UI", 9), bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack()

        self.var_busca = tk.StringVar()
        entry_busca = tk.Entry(self.root, textvariable=self.var_busca, bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, relief="flat", highlightthickness=1)
        entry_busca.pack(pady=5, padx=20, fill="x", ipady=3)
        entry_busca.bind("<KeyRelease>", lambda e: self.aplicar_filtro_busca())

        self.emails_all = [c.get('email', '') for c in self.contas]
        self.combo = ttk.Combobox(self.root, values=self.emails_all, width=55, font=("Segoe UI", 10), state="readonly")
        self.combo.pack(pady=5, ipady=4)
        self.combo.bind("<<ComboboxSelected>>", self.ao_selecionar)

        self.frame_dados = tk.Frame(self.root, bg=COR_FUNDO); self.frame_dados.pack(pady=10, padx=20, fill="x")
        self.var_email_entry = self.criar_linha_copia(self.frame_dados, "E-mail:")
        self.var_senha_entry = self.criar_linha_copia(self.frame_dados, "Senha:")
        self.criar_linha_otp(self.frame_dados)

        self.frame_acoes = tk.Frame(self.root, bg=COR_FUNDO); self.frame_acoes.pack(pady=10)
        if self.modo == "apenas_novas":
            tk.Button(self.frame_acoes, text="✅ CHAR CRIADO", command=lambda: self.marcar_e_pular("char_created"), 
                      bg=COR_SUCESSO, fg="white", font=("Segoe UI", 10, "bold"), width=20).pack(side="left", padx=5)
        if self.modo == "premios":
            tk.Button(self.frame_acoes, text="🎁 RESGATADO", command=lambda: self.marcar_e_pular("reward_claimed"), 
                      bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 10, "bold"), width=20).pack(side="left", padx=5)

        self.txt_premios = tk.Text(self.root, height=5, font=("Consolas", 9), bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, relief="flat")
        self.txt_premios.pack(pady=5, padx=20, fill="both", expand=True)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=440, mode="determinate", style="Horizontal.TProgressbar")
        self.progress.pack(pady=10)

        if self.contas: 
            self.combo.current(0); self.ao_selecionar(None)

    def criar_linha_copia(self, parent, label_text):
        f = tk.Frame(parent, bg=COR_FUNDO); f.pack(fill="x", pady=4)
        tk.Label(f, text=label_text, width=8, anchor="w", font=("Segoe UI", 9, "bold"), bg=COR_FUNDO, fg=COR_TEXTO_SEC).pack(side="left")
        e = tk.Entry(f, font=("Consolas", 10), bg=COR_FUNDO_CAMPO, fg=COR_TEXTO, relief="flat"); e.pack(side="left", fill="x", expand=True, padx=5, ipady=3)
        tk.Button(f, text="COPIAR", font=("Segoe UI", 8, "bold"), bg=COR_BOTAO, fg="white", width=8, command=lambda: self.copiar_texto(e.get(), f.winfo_children()[-1])).pack(side="right")
        return e

    def criar_linha_otp(self, parent):
        f = tk.Frame(parent, bg=COR_FUNDO); f.pack(fill="x", pady=10)
        self.lbl_otp = tk.Label(f, text="--- ---", font=("Consolas", 24, "bold"), bg=COR_FUNDO, fg=COR_DESTAQUE); self.lbl_otp.pack(side="left", fill="x", expand=True)
        tk.Button(f, text="COPIAR", bg=COR_DESTAQUE, fg="white", width=8, command=lambda: self.copiar_texto(self.lbl_otp.cget("text").replace(" ",""), f.winfo_children()[-1])).pack(side="right")

    def marcar_e_pular(self, flag):
        email = self.conta_atual['email']
        for caminho in [config.ARQUIVO_PRINCIPAL, config.ARQUIVO_SALVAR]:
            if os.path.exists(caminho):
                db = carregar_json_seguro(caminho)
                for c in db:
                    if c['email'].lower() == email.lower(): c[flag] = True; break
                salvar_json_seguro(caminho, db)
        
        idx = self.combo.current()
        self.contas.pop(idx); self.emails_all.pop(idx); self.combo['values'] = self.emails_all
        if self.contas:
            self.combo.current(idx if idx < len(self.contas) else 0); self.ao_selecionar(None)
        else: self.limpar_campos(); messagebox.showinfo("Fim", "Fila concluída!")

    def copiar_texto(self, texto, botao):
        if not texto or "---" in texto: return
        self.root.clipboard_clear(); self.root.clipboard_append(texto)
        botao.config(text="OK!", bg=COR_SUCESSO)
        self.root.after(800, lambda: botao.config(text="COPIAR", bg=COR_BOTAO if "Senha" in texto or "@" in texto else COR_DESTAQUE))

    def aplicar_filtro_busca(self):
        termo = self.var_busca.get().lower()
        filtrados = [e for e in self.emails_all if termo in e.lower()]
        self.combo["values"] = filtrados
        if filtrados: self.combo.set(filtrados[0]); self.ao_selecionar(None)

    def ao_selecionar(self, event):
        email_sel = self.combo.get()
        self.conta_atual = next((c for c in self.contas if c['email'] == email_sel), None)
        if self.conta_atual:
            for e, v in [(self.var_email_entry, 'email'), (self.var_senha_entry, 'password')]:
                e.config(state="normal"); e.delete(0, tk.END); e.insert(0, self.conta_atual[v]); e.config(state="readonly")
            self.txt_premios.config(state="normal"); self.txt_premios.delete("1.0", tk.END)
            for p in self.premios_map.get(email_sel.lower(), []): self.txt_premios.insert(tk.END, p + "\n")
            self.txt_premios.config(state="disabled")

    def atualizar_loop(self):
        restante = 30 - (time.time() % 30)
        self.progress['value'] = (restante / 30) * 100
        if self.conta_atual and TEM_PYOTP:
            seed = self.conta_atual.get('seed_otp', '').replace(" ", "")
            if len(seed) > 8:
                try:
                    cod = pyotp.TOTP(seed).now()
                    self.lbl_otp.config(text=f"{cod[:3]} {cod[3:]}", fg=COR_TEXTO)
                except: self.lbl_otp.config(text="ERRO SEED", fg=COR_ERRO)
            else: self.lbl_otp.config(text="SEM OTP", fg=COR_ERRO)
        self.root.after(500, self.atualizar_loop)

    def limpar_campos(self):
        self.lbl_otp.config(text="--- ---"); self.combo.set(""); self.var_email_entry.config(state="normal"); self.var_email_entry.delete(0, tk.END)

def executar(modo="todos"):
    if premios_manager: premios_manager.reprocessar_todos_logs()
    root = tk.Tk(); OTPManager(root, modo=modo); root.mainloop()

if __name__ == "__main__":
    executar()
# fabricador/modules/excluir_conta.py

import json
import os
import tkinter as tk
from tkinter import messagebox


def menu_deletar_conta():
    """
    Abre uma janela Tkinter para buscar e excluir contas do arquivo
    accounts.json de forma interativa.
    """

    caminho_arquivo = "accounts.json"

    def carregar_contas():
        """Carrega a lista de contas do JSON. Retorna [] em caso de erro."""
        if not os.path.exists(caminho_arquivo):
            return []
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def limpar_dados():
        """Reseta os labels de resultado e desativa o botão deletar."""
        lbl_res_email.config(text="-")
        lbl_res_senha.config(text="-")
        lbl_res_seed.config(text="-")
        lbl_res_status.config(text="-")
        btn_deletar.config(state=tk.DISABLED, bg="#555555")

    def buscar(event=None):
        """
        Busca a conta digitada no entry e exibe os dados.
        Habilita o botão de deletar se encontrada.
        """
        email_busca = entry_email.get().strip()

        if not email_busca:
            messagebox.showwarning("Aviso", "Digite um e-mail para buscar.")
            return

        contas = carregar_contas()

        conta_encontrada = next(
            (c for c in contas if c.get("email") == email_busca),
            None,
        )

        if conta_encontrada:
            lbl_res_email.config(text=conta_encontrada.get("email", ""))
            lbl_res_senha.config(text=conta_encontrada.get("senha", ""))
            lbl_res_seed.config(text=conta_encontrada.get("seed", "N/A"))
            lbl_res_status.config(text=conta_encontrada.get("status", "N/A"))

            # Habilita o botão deletar em vermelho
            btn_deletar.config(state=tk.NORMAL, bg="#e74c3c")
        else:
            messagebox.showinfo(
                "Não encontrada",
                "Nenhuma conta com este e-mail no registro.",
            )
            limpar_dados()

    def deletar():
        """
        Confirma e executa a exclusão permanente da conta do accounts.json.
        """
        email_alvo = lbl_res_email.cget("text")

        if not email_alvo or email_alvo == "-":
            return

        resposta = messagebox.askyesno(
            "Confirmar Exclusão",
            "⚠️ ATENÇÃO!\n\nTem certeza que deseja DELETAR permanentemente a conta:\n\n"
            f"{email_alvo}?",
        )

        if not resposta:
            return

        contas = carregar_contas()

        contas_filtradas = [
            c for c in contas if c.get("email") != email_alvo
        ]

        if len(contas) != len(contas_filtradas):
            try:
                with open(caminho_arquivo, "w", encoding="utf-8") as f:
                    json.dump(
                        contas_filtradas, f, indent=4, ensure_ascii=False
                    )

                messagebox.showinfo(
                    "Sucesso",
                    "✅ Conta deletada com sucesso do accounts.json!",
                )
                limpar_dados()
                entry_email.delete(0, tk.END)

            except Exception as e:
                messagebox.showerror(
                    "Erro",
                    f"Erro ao salvar arquivo:\n{e}",
                )
        else:
            messagebox.showerror(
                "Erro",
                "Conta não encontrada na hora de deletar.",
            )

    # ── Janela principal ────────────────────────────────────────────────
    root = tk.Tk()
    root.title("Ragnarok Helper | Gestor de Exclusão")
    root.geometry("500x480")
    root.configure(bg="#1e1e1e")
    root.resizable(False, False)

    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass

    # ── Cores e fontes ──────────────────────────────────────────────────
    BG_COLOR   = "#1e1e1e"
    FG_COLOR   = "#ffffff"
    FG_AZUL    = "#3498db"
    FONT_TITLE  = ("Segoe UI", 16, "bold")
    FONT_LABEL  = ("Segoe UI", 10, "bold")
    FONT_VALUE  = ("Consolas", 11)

    # ── Título ──────────────────────────────────────────────────────────
    lbl_titulo = tk.Label(
        root,
        text="BUSCAR E EXCLUIR",
        bg=BG_COLOR,
        fg=FG_AZUL,
        font=FONT_TITLE,
    )
    lbl_titulo.pack(pady=(25, 10))

    # ── Frame de busca ──────────────────────────────────────────────────
    frame_busca = tk.Frame(root, bg=BG_COLOR)
    frame_busca.pack(fill=tk.X, padx=40, pady=10)

    lbl_instrucao = tk.Label(
        frame_busca,
        text="Cole o E-mail da conta:",
        bg=BG_COLOR,
        fg="#aaaaaa",
        font=FONT_LABEL,
    )
    lbl_instrucao.pack(anchor=tk.W, pady=(0, 5))

    entry_email = tk.Entry(
        frame_busca,
        font=("Segoe UI", 12),
        bg="#2d2d2d",
        fg=FG_COLOR,
        insertbackground=FG_COLOR,
        relief=tk.FLAT,
    )
    entry_email.pack(fill=tk.X, ipady=6)
    entry_email.bind("<Return>", buscar)

    btn_buscar = tk.Button(
        frame_busca,
        text="BUSCAR CONTA",
        bg="#0275d8",
        fg=FG_COLOR,
        font=FONT_LABEL,
        relief=tk.FLAT,
        cursor="hand2",
        command=buscar,
    )
    btn_buscar.pack(pady=15, fill=tk.X, ipady=4)

    # ── Frame de resultado ──────────────────────────────────────────────
    frame_res = tk.Frame(
        root,
        bg="#252525",
        bd=1,
        relief=tk.SOLID,
    )
    frame_res.pack(
        fill=tk.X, padx=40, pady=10, ipadx=10, ipady=10
    )

    def criar_linha_info(parent, texto_label: str):
        """
        Cria uma linha de informação no painel de resultado.
        Retorna o Label de valor (editável via .config(text=...)).
        """
        frame = tk.Frame(parent, bg="#252525")
        frame.pack(fill=tk.X, pady=4)

        lbl = tk.Label(
            frame,
            text=texto_label,
            bg="#252525",
            fg="#888888",
            font=FONT_LABEL,
            width=8,
            anchor=tk.E,
        )
        lbl.pack(side=tk.LEFT, padx=5)

        val = tk.Label(
            frame,
            text="-",
            bg="#252525",
            fg=FG_COLOR,
            font=FONT_VALUE,
            anchor=tk.W,
        )
        val.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return val

    lbl_res_email  = criar_linha_info(frame_res, "E-mail:")
    lbl_res_senha  = criar_linha_info(frame_res, "Senha:")
    lbl_res_seed   = criar_linha_info(frame_res, "Seed:")
    lbl_res_status = criar_linha_info(frame_res, "Status:")

    # ── Botão deletar ────────────────────────────────────────────────────
    btn_deletar = tk.Button(
        root,
        text="DELETAR DEFINITIVAMENTE",
        bg="#555555",
        fg=FG_COLOR,
        font=("Segoe UI", 12, "bold"),
        relief=tk.FLAT,
        cursor="hand2",
        state=tk.DISABLED,
        command=deletar,
    )
    btn_deletar.pack(pady=(15, 20), padx=40, fill=tk.X, ipady=8)

    entry_email.focus()
    root.mainloop()
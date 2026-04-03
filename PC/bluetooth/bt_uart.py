# Interface pour tester la connexion BT avec le Pico (PING / réponses)
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time

def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]

def make_msg(tag, payload=""):
    return "START:{}:{}:END\n".format(tag, payload)

def parse_msg(line):
    line = line.strip()
    if line.startswith("START:") and line.endswith(":END"):
        body = line[6:-4]
        if ":" in body:
            tag, payload = body.split(":", 1)
            return tag.strip(), payload.strip()
    return None, None


class App:
    def __init__(self):
        self.ser = None
        self.root = tk.Tk()
        self.root.title("BT Test")
        self.root.geometry("500x400")
        self.build()

    def build(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Port :").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(frame, textvariable=self.port_var, width=12)
        self.port_box["values"] = list_ports()
        if self.port_box["values"]:
            self.port_box.current(0)
        self.port_box.grid(row=0, column=1, padx=6)

        ttk.Label(frame, text="Baud :").grid(row=1, column=0, sticky="w")
        self.baud_var = tk.StringVar(value="38400")
        ttk.Entry(frame, textvariable=self.baud_var, width=8).grid(row=1, column=1, padx=6)

        self.conn_btn = ttk.Button(frame, text="Connecter", command=self.toggle)
        self.conn_btn.grid(row=2, column=0, columnspan=2, pady=8, sticky="ew")

        self.status = ttk.Label(frame, text="Déconnecté")
        self.status.grid(row=3, column=0, columnspan=2)

        ttk.Button(frame, text="Envoyer PING", command=self.send_ping).grid(
            row=4, column=0, columnspan=2, pady=6, sticky="ew")

        self.log = tk.Text(frame, height=12, width=55, state="disabled")
        self.log.grid(row=5, column=0, columnspan=2, pady=6)

    def log_line(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", "[{}] {}\n".format(ts, text))
        self.log.see("end")
        self.log.config(state="disabled")

    def toggle(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self.status.config(text="Déconnecté")
            self.conn_btn.config(text="Connecter")
            self.log_line("Déconnecté")
        else:
            port = self.port_var.get()
            try:
                baud = int(self.baud_var.get())
                self.ser = serial.Serial(port, baudrate=baud, timeout=1)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                return
            self.status.config(text="Connecté sur {}".format(port))
            self.conn_btn.config(text="Déconnecter")
            self.log_line("Connecté sur {} @ {} baud".format(port, baud))
            threading.Thread(target=self.reader, daemon=True).start()

    def send_ping(self):
        if not self.ser or not self.ser.is_open:
            messagebox.showwarning("BT", "Pas connecté")
            return
        self.ser.write(make_msg("PING").encode())
        self.log_line("> PING envoyé")

    def reader(self):
        # lecture en continu dans un thread séparé
        while self.ser and self.ser.is_open:
            try:
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode(errors="ignore").strip()
                tag, payload = parse_msg(line)
                if tag:
                    self.root.after(0, lambda t=tag, p=payload:
                        self.log_line("< {} | {}".format(t, p)))
                else:
                    self.root.after(0, lambda l=line: self.log_line("< " + l))
            except:
                time.sleep(0.1)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
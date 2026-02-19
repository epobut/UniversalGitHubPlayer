import os
import sys
import re
import json
import shutil
import zipfile
import threading
import subprocess
import requests
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from pathlib import Path

# Налаштування інтерфейсу
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GitHubPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal GitHub Player v1.0")
        self.geometry("1000x700")

        # Шляхи внутрішньої архітектури
        self.base_dir = Path(__file__).parent.absolute()
        self.engine_dir = self.base_dir / "core" / "python_env" # Папка для портативного Python
        self.storage_dir = self.base_dir / "projects" # Папка для проектів з GitHub
        self.python_exe = self.engine_dir / "python.exe"

        # Створюємо необхідні папки
        self.engine_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # --- UI СТРУКТУРА ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Верхня панель: Введення посилання
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Вставте посилання на GitHub репозиторій...", width=600)
        self.url_entry.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        self.btn_run = ctk.CTkButton(self.top_frame, text="🚀 PLAY / RUN", fg_color="#28a745", hover_color="#218838", command=self.start_workflow)
        self.btn_run.pack(side="right", padx=10)

        # 2. Інформаційна панель
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.status_lbl = ctk.CTkLabel(self.info_frame, text="Готовий до роботи. Вставте посилання.")
        self.status_lbl.pack(pady=5)

        # 3. Термінал
        self.terminal_text = tk.Text(self, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10))
        self.terminal_text.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # Старт перевірки оточення
        self.check_engine()

    def log(self, text):
        """Вивід повідомлень у вбудований термінал."""
        self.terminal_text.insert(tk.END, f"{text}\n")
        self.terminal_text.see(tk.END)

    def check_engine(self):
        """Перевірка наявності портативного Python."""
        if not self.python_exe.exists():
            self.log("[!] Портативний Python не знайдено. Потрібне завантаження (~25MB).")
            self.status_lbl.configure(text="Статус: Потрібно завантажити Engine")
        else:
            self.log(f"[OK] Engine знайдено: Python {sys.version.split()[0]}")

    def download_engine(self):
        """Завантаження та налаштування портативного Python (Embeddable)."""
        # Посилання на Python 3.11 Embeddable (стабільний для більшості бібліотек)
        url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        zip_path = self.base_dir / "python_engine.zip"
        
        self.log("[*] Завантаження Python Engine...")
        r = requests.get(url, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        self.log("[*] Розпакування Engine...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.engine_dir)
        
        os.remove(zip_path)

        # --- ВАЖЛИВИЙ ФІКС ДЛЯ ПОРТАТИВНОГО ПІТОНА ---
        # Потрібно дозволити йому бачити встановлені бібліотеки
        pth_file = list(self.engine_dir.glob("python311._pth"))[0]
        content = pth_file.read_text().replace("#import site", "import site")
        pth_file.write_text(content)

        # Встановлення PIP
        self.log("[*] Встановлення PIP менеджеру...")
        pip_script = self.base_dir / "get-pip.py"
        r = requests.get("https://bootstrap.pypa.io/get-pip.py")
        pip_script.write_text(r.text)
        
        subprocess.run([str(self.python_exe), str(pip_script)], creationflags=0x08000000)
        os.remove(pip_script)
        self.log("[OK] Engine готовий!")

    def start_workflow(self):
        """Запуск процесу завантаження та виконання."""
        url = self.url_entry.get().strip()
        if not url:
            self.log("[!] Помилка: Введіть посилання на GitHub.")
            return
        
        self.terminal_text.delete("1.0", tk.END)
        threading.Thread(target=self.workflow_thread, args=(url,), daemon=True).start()

    def workflow_thread(self, url):
        """Фоновий потік для автоматизації всіх кроків."""
        try:
            # 1. Перевірка Engine
            if not self.python_exe.exists():
                self.download_engine()

            # 2. Завантаження проекту з GitHub
            # Перетворюємо посилання на прямий лінк до ZIP архіву
            zip_url = url.rstrip('/') + "/archive/refs/heads/main.zip"
            project_name = url.split('/')[-1]
            project_dir = self.storage_dir / project_name
            
            if project_dir.exists():
                shutil.rmtree(project_dir)
            
            self.log(f"[*] Завантаження проекту {project_name}...")
            r = requests.get(zip_url)
            if r.status_code != 200:
                # Спроба через гілку master
                zip_url = url.rstrip('/') + "/archive/refs/heads/master.zip"
                r = requests.get(zip_url)
            
            temp_zip = self.base_dir / "temp_project.zip"
            temp_zip.write_bytes(r.content)

            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(self.storage_dir)
            
            # GitHub розпаковує в папку 'repo-main', знайдемо її реальний шлях
            extracted_dir = next(self.storage_dir.glob(f"{project_name}-*"))
            shutil.move(str(extracted_dir), str(project_dir))
            os.remove(temp_zip)

            self.log(f"[OK] Проект розпаковано у: {project_dir}")

            # 3. Встановлення залежностей
            req_file = project_dir / "requirements.txt"
            if req_file.exists():
                self.log("[*] Встановлення залежностей через requirements.txt...")
                subprocess.run([str(self.python_exe), "-m", "pip", "install", "-r", str(req_file)], 
                               cwd=project_dir, creationflags=0x08000000)
            else:
                self.log("[*] requirements.txt не знайдено. Спроба авто-аналізу імпортів...")
                # Тут можна інтегрувати наш сканер імпортів, але для початку ставимо базові
                pass

            # 4. Пошук точки входу (Entry Point)
            files = [f.name for f in project_dir.glob("*.py")]
            entry_point = None
            for priority in ["main.py", "bot.py", "run.py", "start.py"]:
                if priority in files:
                    entry_point = priority
                    break
            
            if not entry_point and files:
                entry_point = files[0] # Беремо перший попавшийся .py файл

            if not entry_point:
                self.log("[!] Помилка: Не знайдено файл для запуску.")
                return

            # 5. ЗАПУСК
            self.log(f"[▶️] ЗАПУСК: {entry_point}")
            self.log("-" * 60)
            
            # Форсуємо UTF-8 та безбуферний вивід
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"

            process = subprocess.Popen(
                [str(self.python_exe), "-u", entry_point],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=project_dir,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=0x08000000
            )

            for line in iter(process.stdout.readline, ""):
                self.log(line.strip())
            
            process.stdout.close()
            self.log("-" * 60)
            self.log("[*] Виконання завершено.")

        except Exception as e:
            self.log(f"[КРИТИЧНА ПОМИЛКА]: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    app = GitHubPlayer()
    app.mainloop()
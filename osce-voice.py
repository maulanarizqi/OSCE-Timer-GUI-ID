"""
OSCE Circuit Timer - GUI & Google Voice Edition

Original CLI Project by: Quinexus (https://github.com/Quinexus/OSCE-Timer)
GUI Modification & gTTS Integration by: Maulana (beserta tambahan UI dan fitur Kustomisasi)
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import uuid 

# Menggunakan gTTS (Google TTS) dan pygame untuk audio
try:
    from gtts import gTTS
    import pygame
    # Inisialisasi mixer pygame untuk memutar audio
    pygame.mixer.init()
    GOOGLE_TTS_AVAILABLE = True
except Exception as e:
    print(f"Peringatan: Sistem audio gagal dimuat. Detail: {e}")
    GOOGLE_TTS_AVAILABLE = False

def speak_text(text):
    """Fungsi untuk mengambil suara dari Google dan memutarnya di background."""
    if not GOOGLE_TTS_AVAILABLE:
        print(f"Audio (gtts/pygame belum siap): {text}")
        return

    def run_tts():
        # LOKASI AMAN: Simpan di folder AppData/Local/OSCETimer (Bukan folder Temp Windows)
        # Folder ini sangat aman dan memiliki izin tulis (write permission) penuh dari Windows
        app_data_dir = os.path.join(os.getenv('LOCALAPPDATA'), "OSCETimer")
        
        # Buat foldernya jika belum ada
        os.makedirs(app_data_dir, exist_ok=True)
        
        unique_filename = f"temp_voice_{uuid.uuid4().hex}.mp3"
        # Gabungkan folder aman dengan nama file
        filepath = os.path.join(app_data_dir, unique_filename)
        
        try:
            # Buat objek suara bahasa Indonesia ('id')
            tts = gTTS(text=text, lang='id')
            
            # Simpan file di folder aman
            tts.save(filepath)
            
            # Putar menggunakan pygame dari folder aman
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            
            # Tunggu sampai selesai berbunyi
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # Unload audio agar file bisa dihapus dengan aman
            pygame.mixer.music.unload()
            
        except Exception as e:
            print(f"Error Google TTS: {e}")
        finally:
            # Selalu bersihkan file temporary setelah selesai atau jika terjadi error
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as cleanup_error:
                    print(f"Gagal menghapus file audio sementara: {cleanup_error}")
            
    # Jalankan di thread terpisah agar UI tidak freeze
    threading.Thread(target=run_tts, daemon=True).start()

class OSCETimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OSCE Circuit Timer - Google Voice")
        self.root.geometry("950x750") # Disesuaikan agar panel tidak terpotong
        self.root.configure(padx=20, pady=20)

        # Variabel Suara Opsional
        self.use_opening = tk.BooleanVar(value=True)
        self.opening_text = tk.StringVar(value="Rangkaian OSCE akan segera dimulai.")
        
        self.use_ending = tk.BooleanVar(value=True)
        self.ending_text = tk.StringVar(value="Seluruh rangkaian OSCE telah selesai. Terima kasih.")

        self.use_cancel = tk.BooleanVar(value=True)
        self.cancel_text = tk.StringVar(value="Timer OSCE dibatalkan.")

        # Data Fase Default
        self.phases = [
            {"name": "Waktu Membaca", "duration": 60, "text": "Waktu membaca dimulai dari sekarang."},
            {"name": "Waktu Tindakan", "duration": 780, "text": "Waktu tindakan dimulai."},
            {"name": "Sisa 1 Menit", "duration": 60, "text": "Waktu tersisa satu menit."},
            {"name": "Waktu Feedback", "duration": 180, "text": "Waktu evaluasi dan feedback dimulai."},
            {"name": "Pergantian", "duration": 30, "text": "Waktu habis, silakan berpindah ke stasiun berikutnya."}
        ]

        self.is_running = False
        self.current_station = 1
        self.total_stations = 1
        self.timer_id = None
        self.time_left = 0
        self.settings_visible = True # Status tampilan panel kiri

        self.setup_ui()
        self.refresh_listbox()

    def setup_ui(self):
        # --- PANEL KIRI: Pengaturan Timeline ---
        self.left_frame = ttk.LabelFrame(self.root, text="Pengaturan Timeline & Stasiun", padding=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        station_frame = ttk.Frame(self.left_frame)
        station_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(station_frame, text="Total Stasiun:").pack(side=tk.LEFT)
        self.entry_stations = ttk.Entry(station_frame, width=10)
        self.entry_stations.insert(0, "1")
        self.entry_stations.pack(side=tk.LEFT, padx=5)

        self.listbox = tk.Listbox(self.left_frame, height=5, font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_frame = ttk.Frame(self.left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="↑ Naik", command=self.move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="↓ Turun", command=self.move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="❌ Hapus", command=self.delete_phase).pack(side=tk.RIGHT, padx=2)

        add_frame = ttk.LabelFrame(self.left_frame, text="Tambah / Edit Fase", padding=10)
        add_frame.pack(fill=tk.X, pady=5)

        ttk.Label(add_frame, text="Nama Fase:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_name = ttk.Entry(add_frame)
        self.entry_name.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(add_frame, text="Durasi (detik):").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_duration = ttk.Entry(add_frame)
        self.entry_duration.grid(row=1, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(add_frame, text="Teks Suara:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_text = ttk.Entry(add_frame)
        self.entry_text.grid(row=2, column=1, sticky="ew", pady=2, padx=5)
        
        add_frame.columnconfigure(1, weight=1)
        ttk.Button(add_frame, text="➕ Tambahkan ke Timeline", command=self.add_phase).grid(row=3, column=0, columnspan=2, pady=5)

        # --- PANEL KIRI BAWAH: PENGATURAN SUARA TAMBAHAN ---
        extra_frame = ttk.LabelFrame(self.left_frame, text="Suara Tambahan (Opsional)", padding=10)
        extra_frame.pack(fill=tk.X, pady=5)

        chk_open = ttk.Checkbutton(extra_frame, text="Aktifkan Suara Pembuka", variable=self.use_opening)
        chk_open.grid(row=0, column=0, sticky="w", pady=2, columnspan=2)
        ttk.Label(extra_frame, text="Teks Pembuka:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(extra_frame, textvariable=self.opening_text).grid(row=1, column=1, sticky="ew", pady=2, padx=5)

        chk_end = ttk.Checkbutton(extra_frame, text="Aktifkan Suara Penutup", variable=self.use_ending)
        chk_end.grid(row=2, column=0, sticky="w", pady=(5, 2), columnspan=2)
        ttk.Label(extra_frame, text="Teks Penutup:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(extra_frame, textvariable=self.ending_text).grid(row=3, column=1, sticky="ew", pady=2, padx=5)

        chk_cancel = ttk.Checkbutton(extra_frame, text="Aktifkan Suara Dibatalkan", variable=self.use_cancel)
        chk_cancel.grid(row=4, column=0, sticky="w", pady=(5, 2), columnspan=2)
        ttk.Label(extra_frame, text="Teks Dibatalkan:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(extra_frame, textvariable=self.cancel_text).grid(row=5, column=1, sticky="ew", pady=2, padx=5)

        extra_frame.columnconfigure(1, weight=1)

        # --- PANEL TENGAH: TOMBOL TOGGLE (PEMBATAS KIRI DAN KANAN) ---
        self.middle_frame = tk.Frame(self.root)
        self.middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Tombol ramping dengan ikon panah
        self.btn_toggle = tk.Button(self.middle_frame, text="◀", font=("Helvetica", 14, "bold"), 
                                    command=self.toggle_settings, width=2, cursor="hand2", 
                                    bg="#e0e0e0", relief="raised")
        self.btn_toggle.pack(expand=True, fill=tk.Y)


        # --- PANEL KANAN: Tampilan Timer ---
        self.right_frame = ttk.Frame(self.root, padding=10)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Status peringatan jika belum instal gtts atau audio bermasalah
        if not GOOGLE_TTS_AVAILABLE:
            lbl_warn = tk.Label(self.right_frame, text="⚠️ Sistem audio bermasalah / Library belum lengkap!\nCek koneksi internet.", fg="orange", font=("Helvetica", 10, "bold"))
            lbl_warn.pack(pady=5)

        self.lbl_station = tk.Label(self.right_frame, text="Stasiun: - / -", font=("Helvetica", 20, "bold"))
        self.lbl_station.pack(pady=(20, 10))

        self.lbl_phase = tk.Label(self.right_frame, text="Siap Dimulai", font=("Helvetica", 24), fg="blue")
        self.lbl_phase.pack(pady=10)

        self.lbl_timer = tk.Label(self.right_frame, text="00:00", font=("Helvetica", 70, "bold"), fg="red")
        self.lbl_timer.pack(pady=30)

        self.btn_start = tk.Button(self.right_frame, text="MULAI OSCE", font=("Helvetica", 16, "bold"), bg="green", fg="white", command=self.start_osce)
        self.btn_start.pack(fill=tk.X, pady=10)
        
        self.btn_stop = tk.Button(self.right_frame, text="BERHENTI", font=("Helvetica", 16, "bold"), bg="red", fg="white", command=self.stop_osce, state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X)

        # --- TAMBAHAN TRADEMARK ---
        self.lbl_trademark = tk.Label(self.right_frame, text="watermark disini", font=("Helvetica", 10, "italic"), fg="gray")
        self.lbl_trademark.pack(side=tk.BOTTOM, pady=20)

    def toggle_settings(self):
        """Menyembunyikan atau menampilkan panel kiri (pengaturan)"""
        if self.settings_visible:
            # Sembunyikan panel kiri
            self.left_frame.pack_forget()
            # Ubah ikon panah ke kanan
            self.btn_toggle.config(text="▶")
            self.settings_visible = False
        else:
            # Munculkan kembali di sebelah kiri, letakkan sebelum panel tengah (middle_frame)
            self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), before=self.middle_frame)
            # Ubah ikon panah ke kiri
            self.btn_toggle.config(text="◀")
            self.settings_visible = True

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for phase in self.phases:
            display_text = f"[{phase['duration']}s] {phase['name']} -> \"{phase['text']}\""
            self.listbox.insert(tk.END, display_text)

    def add_phase(self):
        name = self.entry_name.get().strip()
        duration_str = self.entry_duration.get().strip()
        text = self.entry_text.get().strip()

        if not name or not duration_str or not text:
            messagebox.showwarning("Peringatan", "Semua kolom harus diisi!")
            return
        try:
            duration = int(duration_str)
        except ValueError:
            messagebox.showerror("Error", "Durasi harus berupa angka (detik)!")
            return

        self.phases.append({"name": name, "duration": duration, "text": text})
        self.refresh_listbox()
        self.entry_name.delete(0, tk.END)
        self.entry_duration.delete(0, tk.END)
        self.entry_text.delete(0, tk.END)

    def delete_phase(self):
        selected = self.listbox.curselection()
        if not selected: return
        del self.phases[selected[0]]
        self.refresh_listbox()

    def move_up(self):
        selected = self.listbox.curselection()
        if not selected: return
        index = selected[0]
        if index > 0:
            self.phases[index], self.phases[index - 1] = self.phases[index - 1], self.phases[index]
            self.refresh_listbox()
            self.listbox.select_set(index - 1)

    def move_down(self):
        selected = self.listbox.curselection()
        if not selected: return
        index = selected[0]
        if index < len(self.phases) - 1:
            self.phases[index], self.phases[index + 1] = self.phases[index + 1], self.phases[index]
            self.refresh_listbox()
            self.listbox.select_set(index + 1)

    def start_osce(self):
        if not self.phases:
            messagebox.showwarning("Peringatan", "Timeline masih kosong!")
            return
        try:
            self.total_stations = int(self.entry_stations.get())
            if self.total_stations < 1: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Total stasiun harus berupa angka minimal 1.")
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.current_station = 1
        
        # Mengecek apakah fitur suara pembuka diaktifkan
        opening_txt = self.opening_text.get().strip()
        if self.use_opening.get() and opening_txt:
            speak_text(opening_txt)
            
            # Menghitung durasi jeda agar audio selesai sebelum timer jalan
            word_count = len(opening_txt.split())
            delay_ms = max(3500, (word_count // 2) * 1000)
            self.root.after(delay_ms, self.run_station)
        else:
            # Langsung jalan tanpa jeda suara pembuka
            self.run_station()

    def stop_osce(self):
        self.is_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        if GOOGLE_TTS_AVAILABLE:
            pygame.mixer.music.stop()
        self.lbl_station.config(text="Stasiun: - / -")
        self.lbl_phase.config(text="Dibatalkan")
        self.lbl_timer.config(text="00:00")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        
        # Mengecek apakah fitur suara batal diaktifkan
        cancel_txt = self.cancel_text.get().strip()
        if self.use_cancel.get() and cancel_txt:
            speak_text(cancel_txt)

    def run_station(self):
        if not self.is_running: return
        
        # Cek apakah seluruh stasiun telah selesai
        if self.current_station > self.total_stations:
            self.lbl_station.config(text="SELESAI")
            self.lbl_phase.config(text="Seluruh Rangkaian OSCE Selesai")
            
            # Mengecek apakah fitur suara penutup diaktifkan
            ending_txt = self.ending_text.get().strip()
            if self.use_ending.get() and ending_txt:
                speak_text(ending_txt)
                
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.is_running = False
            return

        self.lbl_station.config(text=f"Stasiun: {self.current_station} / {self.total_stations}")
        self.phase_index = 0
        self.run_phase()

    def run_phase(self):
        if not self.is_running: return
        if self.phase_index < len(self.phases):
            current_phase = self.phases[self.phase_index]
            self.lbl_phase.config(text=current_phase["name"])
            speak_text(current_phase["text"])
            self.time_left = current_phase["duration"]
            self.update_timer_display()
            self.countdown()
        else:
            self.current_station += 1
            self.run_station()

    def countdown(self):
        if not self.is_running: return
        if self.time_left > 0:
            self.update_timer_display()
            self.time_left -= 1
            self.timer_id = self.root.after(1000, self.countdown)
        else:
            self.update_timer_display()
            self.phase_index += 1
            self.run_phase()

    def update_timer_display(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.lbl_timer.config(text=f"{minutes:02d}:{seconds:02d}")

if __name__ == "__main__":
    root = tk.Tk()
    app = OSCETimerApp(root)
    root.mainloop()
"""
Cliente Tkinter para Sistema de Processamento de Vídeos
Interface gráfica para upload e visualização de vídeos processados
Versão corrigida para corresponder ao servidor atual
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from pathlib import Path
from PIL import Image, ImageTk
import cv2
import logging

# Configuração de logging
Path('logs').mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurações
SERVER_URL = "http://localhost:5000"
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

class VideoPlayerWindow:
    """Janela para reprodução de vídeos lado a lado"""
    
    def __init__(self, parent, original_path, processed_path, title="Video Comparison"):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("1200x600")
        
        # Frame principal
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Labels
        ttk.Label(main_frame, text="🎬 Original", font=('Arial', 12, 'bold')).grid(
            row=0, column=0, pady=5
        )
        ttk.Label(main_frame, text="🎨 Processado", font=('Arial', 12, 'bold')).grid(
            row=0, column=1, pady=5
        )
        
        # Canvas para vídeos
        self.canvas_original = tk.Canvas(main_frame, bg='black', width=550, height=400)
        self.canvas_original.grid(row=1, column=0, padx=5, pady=5)
        
        self.canvas_processed = tk.Canvas(main_frame, bg='black', width=550, height=400)
        self.canvas_processed.grid(row=1, column=1, padx=5, pady=5)
        
        # Controles
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.play_button = ttk.Button(control_frame, text="▶️ Play", command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="⏹️ Stop", command=self.stop).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Variáveis de controle
        self.is_playing = False
        self.original_path = original_path
        self.processed_path = processed_path
        
        # Capturar vídeos
        self.cap_original = None
        self.cap_processed = None
        
        # Iniciar thread de reprodução
        self.play_thread = None
        
        # Carregar primeiro frame
        self.load_first_frame()
    
    def load_first_frame(self):
        """Carrega o primeiro frame de cada vídeo"""
        try:
            # Original
            cap = cv2.VideoCapture(self.original_path)
            ret, frame = cap.read()
            if ret:
                self.display_frame(frame, self.canvas_original)
            cap.release()
            
            # Processed
            cap = cv2.VideoCapture(self.processed_path)
            ret, frame = cap.read()
            if ret:
                self.display_frame(frame, self.canvas_processed)
            cap.release()
        except Exception as e:
            logger.error(f"Error loading first frame: {e}")
    
    def display_frame(self, frame, canvas):
        """Exibe um frame no canvas"""
        try:
            # Converter BGR para RGB
            if len(frame.shape) == 2:  # Grayscale
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Redimensionar para caber no canvas
            height, width = frame_rgb.shape[:2]
            canvas_width = canvas.winfo_width() if canvas.winfo_width() > 1 else 550
            canvas_height = canvas.winfo_height() if canvas.winfo_height() > 1 else 400
            
            # Calcular proporção
            scale = min(canvas_width/width, canvas_height/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Redimensionar
            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
            
            # Converter para PIL Image
            image = Image.fromarray(frame_resized)
            photo = ImageTk.PhotoImage(image)
            
            # Limpar canvas e exibir
            canvas.delete("all")
            canvas.create_image(
                canvas_width//2, canvas_height//2,
                image=photo, anchor=tk.CENTER
            )
            canvas.image = photo  # Manter referência
            
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")
    
    def toggle_play(self):
        """Alterna entre play e pause"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
    
    def play(self):
        """Inicia reprodução dos vídeos"""
        if not self.is_playing:
            self.is_playing = True
            self.play_button.config(text="⏸️ Pause")
            
            # Iniciar thread de reprodução
            self.play_thread = threading.Thread(target=self.play_videos, daemon=True)
            self.play_thread.start()
    
    def pause(self):
        """Pausa a reprodução"""
        self.is_playing = False
        self.play_button.config(text="▶️ Play")
    
    def stop(self):
        """Para a reprodução e fecha os vídeos"""
        self.is_playing = False
        self.play_button.config(text="▶️ Play")
        
        if self.cap_original:
            self.cap_original.release()
            self.cap_original = None
        
        if self.cap_processed:
            self.cap_processed.release()
            self.cap_processed = None
        
        # Recarregar primeiro frame
        self.load_first_frame()
        self.progress['value'] = 0
    
    def play_videos(self):
        """Thread para reproduzir vídeos simultaneamente"""
        try:
            # Abrir vídeos
            self.cap_original = cv2.VideoCapture(self.original_path)
            self.cap_processed = cv2.VideoCapture(self.processed_path)
            
            # Obter informações
            fps = self.cap_original.get(cv2.CAP_PROP_FPS)
            total_frames = int(self.cap_original.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_delay = 1/fps if fps > 0 else 0.033
            
            frame_count = 0
            
            while self.is_playing:
                # Ler frames
                ret1, frame1 = self.cap_original.read()
                ret2, frame2 = self.cap_processed.read()
                
                if not ret1 or not ret2:
                    # Fim do vídeo
                    self.stop()
                    break
                
                # Exibir frames
                self.display_frame(frame1, self.canvas_original)
                self.display_frame(frame2, self.canvas_processed)
                
                # Atualizar progress bar
                frame_count += 1
                progress_value = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                self.progress['value'] = progress_value
                
                # Delay para manter FPS
                time.sleep(frame_delay)
            
        except Exception as e:
            logger.error(f"Error playing videos: {e}")
            self.stop()
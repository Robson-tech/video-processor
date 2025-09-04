"""
Cliente Tkinter para Sistema de Processamento de Vídeos
Interface gráfica para upload e visualização de vídeos processados
Versão corrigida para corresponder ao servidor atual
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import threading
import time
from pathlib import Path
from PIL import Image, ImageTk
import cv2
import webbrowser
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


class VideoProcessingClient:
    """Cliente principal para processamento de vídeos"""
    
    def setup_styles(self):
        """Configura estilos personalizados"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Cores
        colors = {
            'primary': '#667eea',
            'secondary': '#764ba2',
            'success': '#4CAF50',
            'danger': '#f44336',
            'warning': '#ff9800',
            'dark': '#2c3e50',
            'light': '#ecf0f1'
        }
        
        # Configurar estilos
        style.configure('Title.TLabel', font=('Arial', 24, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Success.TLabel', foreground=colors['success'])
        style.configure('Error.TLabel', foreground=colors['danger'])
        style.configure('Primary.TButton', font=('Arial', 11, 'bold'))
        
        # Frame com gradiente (simulado)
        style.configure('Gradient.TFrame', background=colors['light'])
    
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Container principal
        main_container = ttk.Frame(self.root, style='Gradient.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            title_frame,
            text="🎬 Video Processing System",
            style='Title.TLabel'
        ).pack()
        
        ttk.Label(
            title_frame,
            text="Upload and process videos with custom filters",
            font=('Arial', 11)
        ).pack()
        
        # Status do servidor
        self.server_status = ttk.Label(
            title_frame,
            text="⚪ Checking server...",
            font=('Arial', 10)
        )
        self.server_status.pack(pady=5)
        
        # Notebook para abas
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Aba de Upload
        self.create_upload_tab()
        
        # Aba de Histórico
        self.create_history_tab()
        
        # Aba de Configurações
        self.create_settings_tab()
    
    def create_upload_tab(self):
        """Cria aba de upload de vídeos"""
        upload_frame = ttk.Frame(self.notebook)
        self.notebook.add(upload_frame, text="📤 Upload Video")
        
        # Frame de seleção de arquivo
        file_frame = ttk.LabelFrame(upload_frame, text="Select Video File", padding=15)
        file_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Botão de seleção
        ttk.Button(
            file_frame,
            text="📂 Choose File",
            command=self.select_file,
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        # Label do arquivo selecionado
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=20)
        
        # Frame de preview
        preview_frame = ttk.LabelFrame(upload_frame, text="Video Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Canvas para preview
        self.preview_canvas = tk.Canvas(preview_frame, bg='black', height=300)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Frame de filtros
        filter_frame = ttk.LabelFrame(upload_frame, text="Processing Options", padding=15)
        filter_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(filter_frame, text="Select Filter:").pack(side=tk.LEFT, padx=5)
        
        filters = ['grayscale', 'blur', 'edge', 'pixelate', 'sepia', 'negative']
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.selected_filter,
            values=filters,
            state='readonly',
            width=15
        )
        filter_combo.pack(side=tk.LEFT, padx=10)
        
        # Descrição do filtro
        self.filter_description = ttk.Label(filter_frame, text="Convert to black and white")
        self.filter_description.pack(side=tk.LEFT, padx=20)
        
        # Atualizar descrição quando mudar filtro
        filter_combo.bind('<<ComboboxSelected>>', self.update_filter_description)
        
        # Frame de upload
        upload_action_frame = ttk.Frame(upload_frame)
        upload_action_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Botão de upload
        self.upload_button = ttk.Button(
            upload_action_frame,
            text="🚀 Upload & Process",
            command=self.upload_video,
            style='Primary.TButton',
            state='disabled'
        )
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.upload_progress = ttk.Progressbar(
            upload_action_frame,
            mode='indeterminate',
            length=300
        )
        self.upload_progress.pack(side=tk.LEFT, padx=20)
        
        # Label de status
        self.upload_status = ttk.Label(upload_action_frame, text="")
        self.upload_status.pack(side=tk.LEFT, padx=10)
    
    def create_history_tab(self):
        """Cria aba de histórico de vídeos"""
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="📜 History")
        
        # Frame de controles
        control_frame = ttk.Frame(history_frame)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            control_frame,
            text="🔄 Refresh",
            command=self.load_history
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="🌐 Open Gallery",
            command=lambda: webbrowser.open(f"{SERVER_URL}/gallery")
        ).pack(side=tk.LEFT, padx=5)
        
        # Label de contagem
        self.history_count = ttk.Label(control_frame, text="0 videos")
        self.history_count.pack(side=tk.RIGHT, padx=10)
        
        # Frame da lista
        list_frame = ttk.Frame(history_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Treeview para histórico
        columns = ('ID', 'Name', 'Filter', 'Date', 'Duration', 'Size')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configurar colunas
        self.history_tree.heading('ID', text='ID')
        self.history_tree.heading('Name', text='File Name')
        self.history_tree.heading('Filter', text='Filter')
        self.history_tree.heading('Date', text='Date')
        self.history_tree.heading('Duration', text='Duration')
        self.history_tree.heading('Size', text='Size')
        
        # Larguras das colunas
        self.history_tree.column('ID', width=100)
        self.history_tree.column('Name', width=250)
        self.history_tree.column('Filter', width=100)
        self.history_tree.column('Date', width=150)
        self.history_tree.column('Duration', width=80)
        self.history_tree.column('Size', width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame de ações
        action_frame = ttk.Frame(history_frame)
        action_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            action_frame,
            text="▶️ Play Comparison",
            command=self.play_selected_video
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            action_frame,
            text="📥 Download Original",
            command=lambda: self.download_video('original')
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            action_frame,
            text="📥 Download Processed",
            command=lambda: self.download_video('processed')
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            action_frame,
            text="🗑️ Delete",
            command=self.delete_video
        ).pack(side=tk.LEFT, padx=5)
        
        # Bind double-click
        self.history_tree.bind('<Double-Button-1>', lambda e: self.play_selected_video())
    
    def create_settings_tab(self):
        """Cria aba de configurações"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Settings")
        
        # Frame do servidor
        server_frame = ttk.LabelFrame(settings_frame, text="Server Configuration", padding=20)
        server_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(server_frame, text="Server URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.server_url_var = tk.StringVar(value=SERVER_URL)
        server_entry = ttk.Entry(server_frame, textvariable=self.server_url_var, width=40)
        server_entry.grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Button(
            server_frame,
            text="Test Connection",
            command=self.check_server_connection
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Frame de estatísticas
        stats_frame = ttk.LabelFrame(settings_frame, text="Statistics", padding=20)
        stats_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.stats_label = ttk.Label(stats_frame, text="Loading statistics...")
        self.stats_label.pack()
        
        # Frame de logs
        log_frame = ttk.LabelFrame(settings_frame, text="Application Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Text widget para logs
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar para logs
        log_scroll = ttk.Scrollbar(self.log_text, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botão para limpar logs
        ttk.Button(
            settings_frame,
            text="Clear Logs",
            command=lambda: self.log_text.delete(1.0, tk.END)
        ).pack(pady=10)

    def select_file(self):
        """Abre diálogo para selecionar arquivo de vídeo"""
        filetypes = (
            ('Video files', '*.mp4 *.avi *.mov *.mkv *.webm *.flv'),
            ('All files', '*.*')
        )
        
        filename = filedialog.askopenfilename(
            title='Select a video file',
            initialdir=os.path.expanduser('~'),
            filetypes=filetypes
        )
        
        if filename:
            self.selected_file = filename
            self.file_label.config(text=os.path.basename(filename))
            self.upload_button.config(state='normal')
            
            # Mostrar preview
            self.show_video_preview(filename)
            
            # Log
            self.log(f"Selected file: {filename}")
    
    def show_video_preview(self, video_path):
        """Mostra preview do vídeo selecionado"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            # Pegar frame do meio
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
            
            ret, frame = cap.read()
            if ret:
                # Converter BGR para RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Redimensionar
                height, width = frame_rgb.shape[:2]
                canvas_width = self.preview_canvas.winfo_width()
                if canvas_width < 100:
                    canvas_width = 600
                
                scale = canvas_width / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                
                # Converter para PIL e exibir
                image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(image)
                
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(
                    canvas_width//2, 150,
                    image=photo, anchor=tk.CENTER
                )
                self.preview_canvas.image = photo
                
                # Exibir informações
                fps = cap.get(cv2.CAP_PROP_FPS)
                duration = total_frames / fps if fps > 0 else 0
                info_text = f"Resolution: {width}x{height} | Duration: {duration:.1f}s | FPS: {fps:.0f}"
                self.preview_canvas.create_text(
                    canvas_width//2, 280,
                    text=info_text,
                    fill="white",
                    font=('Arial', 10)
                )
            
            cap.release()
            
        except Exception as e:
            self.log(f"Error showing preview: {e}", level='error')

    def update_filter_description(self, event=None):
        """Atualiza descrição do filtro selecionado"""
        descriptions = {
            'grayscale': 'Convert to black and white',
            'blur': 'Apply Gaussian blur effect',
            'edge': 'Detect edges using Canny algorithm',
            'pixelate': 'Create pixelated/mosaic effect',
            'sepia': 'Apply vintage sepia tone',
            'negative': 'Invert all colors'
        }
        
        filter_name = self.selected_filter.get()
        description = descriptions.get(filter_name, '')
        self.filter_description.config(text=description)
    
    def upload_video(self):
        """Faz upload e processamento do vídeo"""
        if not self.selected_file:
            messagebox.showwarning("Warning", "Please select a video file first")
            return
        
        # Desabilitar botão e mostrar progresso
        self.upload_button.config(state='disabled')
        self.upload_progress.start(10)
        self.upload_status.config(text="Uploading...", foreground='blue')
        
        # Thread para upload
        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()
    
    def _upload_worker(self):
        """Worker thread para upload"""
        try:
            # Preparar arquivo
            with open(self.selected_file, 'rb') as f:
                files = {'file': (os.path.basename(self.selected_file), f, 'video/mp4')}
                data = {'filter': self.selected_filter.get()}
                
                # Fazer upload
                self.log(f"Uploading {os.path.basename(self.selected_file)}...")
                
                response = requests.post(
                    f"{SERVER_URL}/api/upload",
                    files=files,
                    data=data,
                    timeout=300  # 5 minutos timeout
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # Atualizar UI no thread principal
                self.root.after(0, self._upload_success, result)
                
            else:
                error_msg = response.json().get('error', 'Unknown error')
                self.root.after(0, self._upload_error, error_msg)
                
        except requests.exceptions.ConnectionError:
            self.root.after(0, self._upload_error, "Cannot connect to server")
        except Exception as e:
            self.root.after(0, self._upload_error, str(e))
    
    def _upload_success(self, result):
        """Callback de sucesso do upload"""
        self.upload_progress.stop()
        self.upload_button.config(state='normal')
        
        # Extrair informações da resposta do servidor
        video_id = result['video_id']
        video_info = result.get('info', {})
        processing_time = video_info.get('processing_time_sec', 0)
        
        self.upload_status.config(
            text=f"✅ Success! Processing time: {processing_time:.1f}s",
            foreground='green'
        )
        
        self.log(f"Video uploaded successfully: {video_id}")
        
        # Mostrar mensagem
        messagebox.showinfo(
            "Success",
            f"Video processed successfully!\n\n"
            f"Video ID: {video_id}\n"
            f"Processing Time: {processing_time:.1f}s\n"
            f"Filter: {self.selected_filter.get()}"
        )
        
        # Atualizar histórico
        self.load_history()
        
        # Perguntar se quer visualizar
        if messagebox.askyesno("View Video", "Do you want to view the processed video?"):
            # Obter URLs dos vídeos
            original_url = video_info.get('path_original', '')
            processed_url = video_info.get('path_processed', '')
            
            # Baixar vídeos temporariamente
            self.download_and_play(video_id, original_url, processed_url)
    
    def _upload_error(self, error_msg):
        """Callback de erro do upload"""
        self.upload_progress.stop()
        self.upload_button.config(state='normal')
        self.upload_status.config(text=f"❌ Error: {error_msg}", foreground='red')
        
        self.log(f"Upload error: {error_msg}", level='error')
        messagebox.showerror("Upload Error", f"Failed to upload video:\n{error_msg}")

    def load_history(self):
        """Carrega histórico de vídeos do servidor"""
        try:
            response = requests.get(f"{SERVER_URL}/api/videos", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.video_history = data['videos']
                
                # Limpar treeview
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
                
                # Adicionar vídeos
                for video in self.video_history:
                    # Formatar dados
                    video_id = video['id'][:8] + '...'
                    name = video['original_name']
                    filter_name = video['filter'].upper()
                    date = video['created_at'][:19] if video['created_at'] else 'Unknown'
                    duration = f"{video.get('duration_sec', 0):.1f}s"
                    size_mb = video.get('size_bytes', 0) / (1024 * 1024)
                    size = f"{size_mb:.1f} MB"
                    
                    # Inserir na árvore
                    self.history_tree.insert('', 'end', values=(
                        video['id'], name, filter_name, date, duration, size
                    ))
                
                # Atualizar contagem
                self.history_count.config(text=f"{len(self.video_history)} videos")
                
                # Atualizar estatísticas
                self.update_statistics()
                
                self.log(f"Loaded {len(self.video_history)} videos from history")
                
        except Exception as e:
            self.log(f"Error loading history: {e}", level='error')
    
    def update_statistics(self):
        """Atualiza estatísticas na aba de configurações"""
        if not self.video_history:
            return
        
        total_videos = len(self.video_history)
        total_size = sum(v.get('size_bytes', 0) for v in self.video_history) / (1024**3)  # GB
        total_duration = sum(v.get('duration_sec', 0) for v in self.video_history) / 60  # minutos
        
        # Contar filtros
        filter_counts = {}
        for video in self.video_history:
            filter_name = video.get('filter', 'unknown')
            filter_counts[filter_name] = filter_counts.get(filter_name, 0) + 1
        
        stats_text = f"""📊 Video Processing Statistics:

Total Videos: {total_videos}
Total Size: {total_size:.2f} GB
Total Duration: {total_duration:.1f} minutes

Filters Used:"""
        
        for filter_name, count in filter_counts.items():
            stats_text += f"\n  • {filter_name}: {count} videos"
        
        self.stats_label.config(text=stats_text)
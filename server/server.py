"""
Servidor Flask para processamento de vídeos
Sistema Cliente/Servidor em Três Camadas
Versão final com todas as correções de paths e thumbnails
"""

import os
import uuid
import json
import hashlib
import shutil
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, url_for, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sqlite3
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
from PIL import Image
import logging
import base64

# --- Adapters para o SQLite ---
def adapt_datetime_iso(val):
    """Adapta objetos datetime para o formato ISO 8601 string."""
    return val.isoformat()

def convert_timestamp_iso(val):
    """Converte strings ISO 8601 de volta para objetos datetime."""
    return datetime.fromisoformat(val.decode())

sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("timestamp", convert_timestamp_iso)

# Configuração de logging
Path('logs').mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurações
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['MEDIA_ROOT'] = Path('media').resolve()
app.config['UPLOAD_FOLDER'] = app.config['MEDIA_ROOT'] / 'incoming'
app.config['DATABASE'] = Path('database/videos.db').resolve()
app.config['SECRET_KEY'] = 'your-secret-key-here'

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
AVAILABLE_FILTERS = ['grayscale', 'blur', 'edge', 'pixelate', 'sepia', 'negative']

# --- FUNÇÕES AUXILIARES ---
def _get_db_conn():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def setup_directories():
    """Cria estrutura de diretórios necessária"""
    dirs = [
        app.config['UPLOAD_FOLDER'],
        app.config['MEDIA_ROOT'] / 'videos',
        app.config['MEDIA_ROOT'] / 'trash',
        app.config['DATABASE'].parent,
        Path('static/css'),
        Path('static/js'),
        Path('templates')
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def init_database():
    """Inicializa o banco de dados"""
    conn = _get_db_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            original_name TEXT NOT NULL,
            original_ext TEXT NOT NULL,
            mime_type TEXT,
            size_bytes INTEGER,
            duration_sec REAL,
            fps REAL,
            width INTEGER,
            height INTEGER,
            filter TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            path_original TEXT,
            path_processed TEXT,
            checksum_md5 TEXT,
            processing_time_sec REAL,
            thumbnail_path TEXT,
            preview_gif_path TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_md5(filepath):
    """Calcula MD5 checksum de um arquivo"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_video_metadata(filepath):
    """Extrai metadados do vídeo"""
    try:
        clip = VideoFileClip(str(filepath))
        metadata = {
            'duration_sec': clip.duration,
            'fps': clip.fps,
            'width': clip.w,
            'height': clip.h,
            'size_bytes': os.path.getsize(str(filepath))
        }
        clip.close()
        return metadata
    except Exception as e:
        logger.warning(f"MoviePy failed, trying OpenCV: {e}")
        try:
            cap = cv2.VideoCapture(str(filepath))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            metadata = {
                'duration_sec': frame_count / fps if fps > 0 else 0,
                'fps': fps,
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'size_bytes': os.path.getsize(str(filepath))
            }
            cap.release()
            return metadata
        except Exception as e2:
            logger.error(f"Failed to get metadata: {e2}")
            return {
                'duration_sec': 0,
                'fps': 0,
                'width': 0,
                'height': 0,
                'size_bytes': os.path.getsize(str(filepath))
            }

def create_directory_structure(video_id):
    """Cria estrutura de diretórios para um vídeo"""
    now = datetime.now()
    base_path = app.config['MEDIA_ROOT'] / 'videos' / now.strftime('%Y/%m/%d') / video_id
    dirs = {
        'base': base_path,
        'original': base_path / 'original',
        'processed': base_path / 'processed',
        'thumbs': base_path / 'thumbs'
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs

def generate_thumbnails(video_path, output_dir, num_frames=5):
    """Gera thumbnails do vídeo"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            cap.release()
            return None, None
        
        thumbnails = []
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                # Redimensionar para thumbnail
                height, width = frame.shape[:2]
                new_width = 320
                new_height = int(height * (new_width / width))
                resized = cv2.resize(frame, (new_width, new_height))
                
                # Salvar thumbnail
                thumb_path = output_dir / f"frame_{i+1:04d}.jpg"
                cv2.imwrite(str(thumb_path), resized)
                thumbnails.append(str(thumb_path))
        
        cap.release()
        
        # Gerar preview GIF
        if thumbnails:
            try:
                preview_gif_path = output_dir / "preview.gif"
                images = [Image.open(thumb) for thumb in thumbnails[:3]]
                images[0].save(
                    str(preview_gif_path),
                    save_all=True,
                    append_images=images[1:],
                    duration=500,
                    loop=0
                )
                # Retornar caminhos relativos ao MEDIA_ROOT
                thumb_rel = Path(thumbnails[0]).relative_to(app.config['MEDIA_ROOT'])
                gif_rel = preview_gif_path.relative_to(app.config['MEDIA_ROOT'])
                return str(thumb_rel).replace('\\', '/'), str(gif_rel).replace('\\', '/')
            except Exception as e:
                logger.error(f"Error creating GIF: {e}")
                if thumbnails:
                    thumb_rel = Path(thumbnails[0]).relative_to(app.config['MEDIA_ROOT'])
                    return str(thumb_rel).replace('\\', '/'), None
        
    except Exception as e:
        logger.error(f"Error generating thumbnails: {e}")
    
    return None, None

class VideoProcessor:
    """Classe para processar vídeos com diferentes filtros"""
    
    @staticmethod
    def process_frame(frame, filter_name):
        """Aplica filtro em um frame"""
        if filter_name == 'grayscale':
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif filter_name == 'blur':
            return cv2.GaussianBlur(frame, (15, 15), 0)
        elif filter_name == 'edge':
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        elif filter_name == 'pixelate':
            h, w = frame.shape[:2]
            temp = cv2.resize(frame, (w//10, h//10), interpolation=cv2.INTER_LINEAR)
            return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        elif filter_name == 'sepia':
            kernel = np.array([[0.272, 0.534, 0.131],
                              [0.349, 0.686, 0.168],
                              [0.393, 0.769, 0.189]])
            return cv2.transform(frame, kernel)
        elif filter_name == 'negative':
            return cv2.bitwise_not(frame)
        return frame
    
    @staticmethod
    def process_video(input_path, output_path, filter_name):
        """Processa vídeo completo com filtro"""
        try:
            cap = cv2.VideoCapture(str(input_path))
            
            # Obter propriedades do vídeo
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Configurar codec
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Criar writer
            if filter_name == 'grayscale':
                out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height), False)
            else:
                out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height), True)
            
            if not out.isOpened():
                logger.error("Failed to open video writer")
                cap.release()
                return False
            
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                processed_frame = VideoProcessor.process_frame(frame, filter_name)
                out.write(processed_frame)
                frame_count += 1
                
                if frame_count % 100 == 0 and total_frames > 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"Processed {frame_count}/{total_frames} frames ({progress:.1f}%)")
            
            cap.release()
            out.release()
            
            logger.info(f"Video processed successfully: {frame_count} frames")
            return True
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return False

# --- ROTAS DA API ---
@app.route('/')
def index():
    """Página inicial"""
    return jsonify({
        'status': 'online',
        'service': 'Video Processing Server',
        'version': '1.0.2',
        'endpoints': {
            'upload': '/api/upload',
            'videos': '/api/videos',
            'video': '/api/video/<uuid>',
            'gallery': '/gallery',
            'health': '/api/health'
        }
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        conn = _get_db_conn()
        video_count = conn.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
        conn.close()
        
        total, used, free = shutil.disk_usage(app.config['MEDIA_ROOT'])
        free_gb = free / (1024**3)
        
        return jsonify({
            'status': 'healthy',
            'videos_in_db': video_count,
            'disk_free_gb': round(free_gb, 2),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Endpoint para upload e processamento de vídeo"""
    start_time = time.time()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    filter_name = request.form.get('filter', 'grayscale')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    if filter_name not in AVAILABLE_FILTERS:
        return jsonify({'error': f'Invalid filter. Available: {", ".join(AVAILABLE_FILTERS)}'}), 400
    
    video_id = str(uuid.uuid4())
    original_name = secure_filename(file.filename)
    extension = original_name.rsplit('.', 1)[1].lower()
    temp_path = app.config['UPLOAD_FOLDER'] / f"{video_id}_temp.{extension}"
    
    try:
        # Salvar arquivo temporário
        file.save(str(temp_path))
        
        # Calcular checksum
        checksum = calculate_md5(temp_path)
        
        # Verificar duplicatas
        conn = _get_db_conn()
        cursor = conn.cursor()
        duplicate = cursor.execute('SELECT id FROM videos WHERE checksum_md5 = ?', (checksum,)).fetchone()
        
        if duplicate:
            conn.close()
            os.remove(temp_path)
            return jsonify({'error': 'Duplicate video detected', 'existing_id': duplicate[0]}), 409
        
        # Obter metadados
        metadata = get_video_metadata(temp_path)
        
        # Criar estrutura de diretórios
        dirs = create_directory_structure(video_id)
        
        # Mover arquivo original
        original_path = dirs['original'] / f"video.{extension}"
        shutil.move(str(temp_path), str(original_path))
        
        # Processar vídeo
        filter_dir = dirs['processed'] / filter_name
        filter_dir.mkdir(exist_ok=True)
        processed_path = filter_dir / f"video.{extension}"
        
        if not VideoProcessor.process_video(original_path, processed_path, filter_name):
            shutil.rmtree(dirs['base'])
            conn.close()
            return jsonify({'error': 'Failed to process video'}), 500
        
        # Gerar thumbnails
        thumbnail_path, preview_gif_path = generate_thumbnails(original_path, dirs['thumbs'])
        
        # Calcular caminhos relativos
        original_rel = str(original_path.relative_to(app.config['MEDIA_ROOT'])).replace('\\', '/')
        processed_rel = str(processed_path.relative_to(app.config['MEDIA_ROOT'])).replace('\\', '/')
        
        processing_time = time.time() - start_time
        
        # Salvar no banco de dados
        cursor.execute('''
            INSERT INTO videos (
                id, original_name, original_ext, mime_type, size_bytes,
                duration_sec, fps, width, height, filter, created_at,
                path_original, path_processed, checksum_md5, processing_time_sec,
                thumbnail_path, preview_gif_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_id, original_name, extension, f'video/{extension}',
            metadata['size_bytes'], metadata['duration_sec'], metadata['fps'],
            metadata['width'], metadata['height'], filter_name, datetime.now(),
            original_rel, processed_rel, checksum, processing_time,
            thumbnail_path, preview_gif_path
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Video {video_id} processed successfully in {processing_time:.2f}s")
        
        # Preparar resposta com URLs absolutas
        base_url = request.host_url.rstrip('/')
        response_data = {
            'success': True,
            'video_id': video_id,
            'info': {
                'id': video_id,
                'original_name': original_name,
                'filter': filter_name,
                'processing_time_sec': processing_time,
                'duration_sec': metadata['duration_sec'],
                'size_bytes': metadata['size_bytes'],
                'path_original': f"{base_url}/media/{original_rel}",
                'path_processed': f"{base_url}/media/{processed_rel}",
                'thumbnail_path': f"{base_url}/media/{thumbnail_path}" if thumbnail_path else None,
                'preview_gif_path': f"{base_url}/media/{preview_gif_path}" if preview_gif_path else None
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        if 'temp_path' in locals() and temp_path.exists():
            os.remove(temp_path)
        return jsonify({'error': 'An internal error occurred during upload'}), 500

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """Lista todos os vídeos processados"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filter_type = request.args.get('filter')
        
        conn = _get_db_conn()
        
        # Query base
        query_base = 'FROM videos'
        params = []
        
        if filter_type:
            query_base += ' WHERE filter = ?'
            params.append(filter_type)
        
        # Total count
        total_count = conn.execute(f'SELECT COUNT(*) {query_base}', params).fetchone()[0]
        
        # Get videos
        query = f'SELECT * {query_base} ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([per_page, (page - 1) * per_page])
        
        videos = []
        base_url = request.host_url.rstrip('/')
        
        for row in conn.execute(query, params).fetchall():
            video = dict(row)
            # Adicionar URLs absolutas
            video['path_original'] = f"{base_url}/media/{video['path_original']}" if video['path_original'] else None
            video['path_processed'] = f"{base_url}/media/{video['path_processed']}" if video['path_processed'] else None
            video['thumbnail_path'] = f"{base_url}/media/{video['thumbnail_path']}" if video['thumbnail_path'] else None
            video['preview_gif_path'] = f"{base_url}/media/{video['preview_gif_path']}" if video['preview_gif_path'] else None
            videos.append(video)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(videos),
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page,
            'videos': videos
        })
        
    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>', methods=['GET'])
def get_video_info(video_id):
    """Obtém informações de um vídeo específico"""
    try:
        conn = _get_db_conn()
        video = conn.execute('SELECT * FROM videos WHERE id = ?', (video_id,)).fetchone()
        conn.close()
        
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        video_dict = dict(video)
        base_url = request.host_url.rstrip('/')
        
        # Adicionar URLs absolutas
        video_dict['path_original'] = f"{base_url}/media/{video_dict['path_original']}" if video_dict['path_original'] else None
        video_dict['path_processed'] = f"{base_url}/media/{video_dict['path_processed']}" if video_dict['path_processed'] else None
        video_dict['thumbnail_path'] = f"{base_url}/media/{video_dict['thumbnail_path']}" if video_dict['thumbnail_path'] else None
        video_dict['preview_gif_path'] = f"{base_url}/media/{video_dict['preview_gif_path']}" if video_dict['preview_gif_path'] else None
        
        return jsonify({
            'success': True,
            'video': video_dict
        })
        
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    """Move vídeo para lixeira"""
    try:
        conn = _get_db_conn()
        result = conn.execute('SELECT path_original FROM videos WHERE id = ?', (video_id,)).fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'Video not found'}), 404
        
        # Construir caminho completo
        original_path = app.config['MEDIA_ROOT'] / result['path_original']
        
        if original_path.exists():
            video_dir = original_path.parent.parent
            trash_dir = app.config['MEDIA_ROOT'] / 'trash' / video_id
            shutil.move(str(video_dir), str(trash_dir))
        
        conn.execute('DELETE FROM videos WHERE id = ?', (video_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"Video {video_id} moved to trash")
        return jsonify({'success': True, 'message': 'Video moved to trash'})
        
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/gallery')
def gallery():
    """Interface web para visualização de thumbnails"""
    try:
        conn = _get_db_conn()
        videos = [dict(row) for row in conn.execute(
            'SELECT * FROM videos ORDER BY created_at DESC LIMIT 50'
        ).fetchall()]
        total_size = conn.execute('SELECT SUM(size_bytes) FROM videos').fetchone()[0] or 0
        conn.close()
        
        # Criar template HTML inline se não existir
        template_dir = Path('templates')
        template_dir.mkdir(exist_ok=True)
        template_file = template_dir / 'gallery.html'
        
        if not template_file.exists():
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(GALLERY_TEMPLATE)
        
        return render_template('gallery.html',
                             videos=videos,
                             total_size_mb=total_size / (1024 * 1024))
        
    except Exception as e:
        logger.error(f"Error loading gallery: {e}")
        return f"Error: {e}", 500

@app.route('/media/<path:filepath>')
def serve_media(filepath):
    """Serve arquivos de mídia"""
    try:
        # Construir caminho completo
        full_path = app.config['MEDIA_ROOT'] / filepath
        
        logger.info(f"Serving media: {filepath}")
        logger.info(f"Full path: {full_path}")
        logger.info(f"Exists: {full_path.exists()}")
        
        if full_path.exists() and full_path.is_file():
            return send_from_directory(app.config['MEDIA_ROOT'], filepath)
        else:
            logger.error(f"File not found: {full_path}")
            return "File not found", 404
            
    except Exception as e:
        logger.error(f"Error serving media: {e}")
        return str(e), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': f'File too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] / 1024**2}MB'}), 413

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'An internal server error occurred'}), 500

# Template HTML para galeria
GALLERY_TEMPLATE = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Galeria de Vídeos</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .stats {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-around;
        }
        .stat-item { text-align: center; padding: 10px; }
        .stat-value { font-size: 2rem; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 5px; }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
        }
        .video-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .video-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }
        .video-thumbnail {
            width: 100%;
            height: 200px;
            object-fit: cover;
            background: #f0f0f0;
        }
        .video-info { padding: 15px; }
        .video-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }
        .filter-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            display: inline-block;
        }
        .video-meta {
            color: #666;
            font-size: 0.9rem;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Galeria de Vídeos Processados</h1>
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{{ videos|length }}</div>
                <div class="stat-label">Total de Vídeos</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ "%.1f"|format(total_size_mb) }} MB</div>
                <div class="stat-label">Espaço Utilizado</div>
            </div>
        </div>
        <div class="gallery">
            {% for video in videos %}
            <div class="video-card">
                {% if video.thumbnail_path %}
                <img src="/media/{{ video.thumbnail_path }}" alt="{{ video.original_name }}" class="video-thumbnail">
                {% else %}
                <div class="video-thumbnail" style="display: flex; align-items: center; justify-content: center; color: #999;">
                    📹 No Thumbnail
                </div>
                {% endif %}
                <div class="video-info">
                    <div class="video-title">{{ video.original_name }}</div>
                    <span class="filter-badge">{{ video.filter|upper }}</span>
                    <div class="video-meta">
                        Duration: {{ "%.1f"|format(video.duration_sec) }}s<br>
                        Created: {{ video.created_at[:19] }}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>'''

if __name__ == '__main__':
    setup_directories()
    init_database()
    
    logger.info("Starting Video Processing Server v1.0.2...")
    logger.info(f"Server running on http://localhost:5000")
    logger.info(f"Gallery available at http://localhost:5000/gallery")
    logger.info(f"Media root: {app.config['MEDIA_ROOT']}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
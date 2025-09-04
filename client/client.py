"""
Cliente Tkinter para Sistema de Processamento de Vídeos
Interface gráfica para upload e visualização de vídeos processados
Versão corrigida para corresponder ao servidor atual
"""

from pathlib import Path
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
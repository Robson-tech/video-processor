# 🎬 Sistema de Processamento de Vídeos

Sistema cliente-servidor para upload, processamento e visualização de vídeos com aplicação de filtros em tempo real.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-v2.0+-green.svg)
![OpenCV](https://img.shields.io/badge/opencv-v4.0+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 📋 Descrição

Sistema completo de processamento de vídeos que permite aos usuários fazer upload de vídeos, aplicar diversos filtros de processamento de imagem e visualizar/baixar os resultados. O projeto segue uma arquitetura cliente-servidor em três camadas.

### ✨ Funcionalidades

- **Upload de Vídeos**: Suporte para múltiplos formatos (MP4, AVI, MOV, MKV, WebM, FLV)
- **Processamento com Filtros**:
  - Grayscale (Preto e Branco)
  - Blur (Desfoque Gaussiano)
  - Edge Detection (Detecção de Bordas)
  - Pixelate (Efeito Pixelado)
  - Sepia (Tons Sépia)
  - Negative (Negativo)
- **Visualização**: Galeria web com thumbnails automáticos
- **Download**: Vídeos originais e processados
- **Interface Gráfica**: Cliente desktop em Tkinter
- **API REST**: Endpoints para integração

## 🏗️ Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Cliente GUI    │────▶│  Servidor Flask │────▶│  Banco SQLite   │
│  (Tkinter)      │◀────│  (API REST)     │◀────│  + Storage      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       ▲
        │                       │
        └───────────────────────┘
          Interface Web (Gallery)
```

## 📦 Requisitos

### Dependências Python

```txt
Flask==2.3.0
flask-cors==4.0.0
opencv-python==4.8.0
numpy==1.24.0
Pillow==10.0.0
moviepy==1.0.3
requests==2.31.0
tkinter (incluído no Python)
```

### Requisitos do Sistema

- Python 3.8 ou superior
- Windows 10/11, macOS 10.14+, ou Linux
- Mínimo 4GB RAM
- 2GB de espaço em disco
- Conexão de rede local

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Robson-tech/video-processor.git
cd video-processor
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Estrutura de diretórios esperada

```
projeto_videoSD/
├── server/
│   ├── server.py
│   ├── templates/
│   │   └── gallery.html
│   ├── database/
│   │   └── videos.db (criado automaticamente)
│   ├── media/
│   │   ├── incoming/
│   │   ├── videos/
│   │   └── trash/
│   └── logs/
│       └── server.log
├── client/
│   ├── client.py
│   └── temp_videos/
├── requirements.txt
└── README.md
```

## 💻 Como Usar

### 1. Iniciar o Servidor

```bash
cd server
python server.py
```

O servidor iniciará em `http://localhost:5000`


### 2. Iniciar o Cliente Desktop

Em outro terminal:

```bash
cd client
python client.py
```
Caso queira testar usando dois computadores deve trocar localhost pelo IP da máquina que estiver rodando o servidor.

### 3. Processar um Vídeo

1. Clique em **"📂 Choose File"** para selecionar um vídeo
2. Escolha um filtro no dropdown
3. Clique em **"🚀 UPLOAD & PROCESS VIDEO"**
4. Aguarde o processamento
5. Acesse a aba **"📜 History"** para baixar os resultados

### 4. Acessar a Galeria Web

Abra o navegador em: `http://localhost:5000/gallery`

## 🔌 API Endpoints

### Health Check
```http
GET /api/health
```

### Upload de Vídeo
```http
POST /api/upload
Content-Type: multipart/form-data

Parameters:
- file: arquivo de vídeo
- filter: nome do filtro (grayscale, blur, edge, pixelate, sepia, negative)
```

### Listar Vídeos
```http
GET /api/videos?page=1&per_page=20&filter=grayscale
```

### Obter Informações do Vídeo
```http
GET /api/video/{video_id}
```

### Deletar Vídeo
```http
DELETE /api/video/{video_id}
```

### Download de Arquivo
```http
GET /media/{path_to_file}
```

## 🎨 Filtros Disponíveis

| Filtro | Descrição | Processamento |
|--------|-----------|---------------|
| **Grayscale** | Converte para preto e branco | Rápido |
| **Blur** | Aplica desfoque Gaussiano (15x15) | Rápido |
| **Edge** | Detecta bordas usando Canny | Médio |
| **Pixelate** | Cria efeito de pixelização | Rápido |
| **Sepia** | Aplica tons sépia vintage | Rápido |
| **Negative** | Inverte todas as cores | Rápido |

## 🔧 Configurações

### Servidor (`server.py`)

```python
# Tamanho máximo de upload
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Extensões permitidas
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}

# Porta do servidor
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Cliente (`client.py`)

```python
# URL do servidor
SERVER_URL = "http://localhost:5000"

# Tamanho da janela
self.root.geometry("1200x800")
```

## 🐛 Resolução de Problemas

### Problema: Botão de upload não aparece

**Solução**: Ajuste a escala do Windows para 100% ou maximize a janela do cliente

### Problema: "Server Offline" no cliente

**Solução**: 
1. Verifique se o servidor está rodando
2. Confirme que está usando a porta 5000
3. Desative temporariamente o firewall

### Problema: Erro de codec no vídeo processado

**Solução**: O sistema usa o codec `mp4v` por padrão. Para melhor compatibilidade, converta seus vídeos para MP4 antes do upload.

### Problema: Memória insuficiente

**Solução**: Para vídeos grandes (>100MB), considere:
- Reduzir a resolução antes do upload
- Processar vídeos mais curtos
- Aumentar a memória disponível do sistema

## 📊 Estrutura do Banco de Dados

### Tabela: `videos`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | TEXT | UUID único do vídeo |
| original_name | TEXT | Nome original do arquivo |
| filter | TEXT | Filtro aplicado |
| duration_sec | REAL | Duração em segundos |
| size_bytes | INTEGER | Tamanho em bytes |
| created_at | TIMESTAMP | Data de criação |
| path_original | TEXT | Caminho do vídeo original |
| path_processed | TEXT | Caminho do vídeo processado |
| thumbnail_path | TEXT | Caminho da thumbnail |

## 🔒 Segurança

- Validação de tipos de arquivo
- Limite de tamanho de upload (500MB)
- Sanitização de nomes de arquivo
- Verificação de checksums MD5 para evitar duplicatas
- Isolamento de arquivos por UUID

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---
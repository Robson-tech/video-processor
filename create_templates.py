"""
Helper script to create HTML templates for the Flask video server
"""

from pathlib import Path

def create_gallery_template():
    """Cria o arquivo gallery.html dentro da pasta 'server/templates' com o novo design."""
    
    # Garante que o template seja criado no local correto para o Flask
    template_dir = Path("server") / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    output_file = template_dir / "gallery.html"
    
    template_content = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Galeria de Vídeos Processados</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: linear-gradient(135deg, #6e8efb 0%, #a777e3 100%); min-height: 100vh; padding: 25px; color: #333; }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 { color: white; text-align: center; margin-bottom: 40px; font-size: 2.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center; gap: 15px; }
        h1 i { font-size: 2.2rem; }

        /* Seção de Estatísticas */
        .stats { background: white; border-radius: 16px; padding: 20px 25px; margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; }
        .stat-item { text-align: center; padding: 10px; flex: 1; min-width: 150px; }
        .stat-value { font-size: 2.2rem; font-weight: bold; color: #5a67d8; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px; }

        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 25px; }
        
        /* Card de Vídeo */
        .video-card { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); transition: transform 0.3s, box-shadow 0.3s; display: flex; flex-direction: column; }
        .video-card:hover { transform: translateY(-8px); box-shadow: 0 15px 40px rgba(0,0,0,0.2); }
        
        .thumbnail-container { width: 100%; height: 190px; background-color: #f0f2f5; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #e2e8f0; position: relative; overflow: hidden; }
        .thumbnail { width: 100%; height: 100%; object-fit: cover; }
        .no-thumbnail { color: #a0aec0; font-size: 3rem; display: flex; flex-direction: column; align-items: center; gap: 10px; }
        .no-thumbnail span { font-size: 0.9rem; }

        .info { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; }
        .info h3 { font-size: 1.2rem; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #2d3748; }
        
        .metadata-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; font-size: 0.9rem; }
        .tag { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
        .tag i { font-size: 0.8em; }
        .filter-tag { background-color: #ebf4ff; color: #5a67d8; }
        .duration-tag { background-color: #f0f2f5; color: #4a5568; }
        .date-time { color: #718096; grid-column: span 2; display: flex; align-items: center; gap: 6px; font-size: 0.85rem; }

        .card-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: auto; padding-top: 15px; border-top: 1px solid #e2e8f0; }
        .action-btn { border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 600; transition: all 0.2s; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
        .action-btn i { font-size: 1em; }
        .action-btn.original { background-color: #48bb78; color: white; }
        .action-btn.original:hover { background-color: #38a169; }
        .action-btn.processed { background-color: #4299e1; color: white; }
        .action-btn.processed:hover { background-color: #3182ce; }

        .empty-gallery { color: white; text-align: center; font-size: 1.2rem; padding: 50px; background: rgba(255,255,255,0.1); border-radius: 15px; grid-column: 1 / -1; }
        
        @media (max-width: 768px) {
            .gallery { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
            h1 { font-size: 1.8rem; }
            .stats { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><i class="fas fa-film"></i> Galeria de Vídeos Processados</h1>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{{ videos | length }}</div>
                <div class="stat-label">Total de Vídeos</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">6</div>
                <div class="stat-label">Filtros Disponíveis</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ "%.1f"|format(total_size_mb) }} MB</div>
                <div class="stat-label">Espaço Utilizado</div>
            </div>
        </div>

        <div class="gallery">
            {% if videos %}
                {% for video in videos %}
                <div class="video-card">
                    <div class="thumbnail-container">
                        {% if video.thumbnail_path %}
                            {% if video.thumbnail_path.startswith('http') %}
                                <img class="thumbnail" 
                                     src="{{ video.thumbnail_path }}" 
                                     alt="Thumbnail para {{ video.original_name }}"
                                     onerror="this.style.display='none'; this.parentElement.querySelector('.no-thumbnail').style.display='flex';">
                            {% else %}
                                <img class="thumbnail" 
                                     src="/media/{{ video.thumbnail_path }}" 
                                     alt="Thumbnail para {{ video.original_name }}"
                                     onerror="this.style.display='none'; this.parentElement.querySelector('.no-thumbnail').style.display='flex';">
                            {% endif %}
                            <div class="no-thumbnail" style="display: none;">
                                <i class="fas fa-video"></i>
                                <span>Preview não disponível</span>
                            </div>
                        {% else %}
                            <div class="no-thumbnail">
                                <i class="fas fa-video"></i>
                                <span>Preview não disponível</span>
                            </div>
                        {% endif %}
                    </div>
                    <div class="info">
                        <h3 title="{{ video.original_name }}">{{ video.original_name }}</h3>
                        <div class="metadata-grid">
                            <span class="tag filter-tag">
                                <i class="fas fa-magic"></i> 
                                {{ video.filter.upper() if video.filter else 'UNKNOWN' }}
                            </span>
                            <span class="tag duration-tag">
                                <i class="far fa-clock"></i> 
                                {{ "%.1f"|format(video.duration_sec if video.duration_sec else 0) }}s
                            </span>
                            <div class="date-time">
                                <i class="far fa-calendar-alt"></i>
                                {% if video.created_at %}
                                    {% if video.created_at is string %}
                                        {{ video.created_at[:19] }}
                                    {% else %}
                                        {{ video.created_at.strftime('%d/%m/%Y %H:%M') if video.created_at else 'Data desconhecida' }}
                                    {% endif %}
                                {% else %}
                                    Data desconhecida
                                {% endif %}
                            </div>
                        </div>
                        <div class="card-actions">
                            {% if video.path_original %}
                                {% if video.path_original.startswith('http') %}
                                    <a href="{{ video.path_original }}" download class="action-btn original">
                                        <i class="fas fa-download"></i> Original
                                    </a>
                                {% else %}
                                    <a href="/media/{{ video.path_original }}" download class="action-btn original">
                                        <i class="fas fa-download"></i> Original
                                    </a>
                                {% endif %}
                            {% endif %}
                            
                            {% if video.path_processed %}
                                {% if video.path_processed.startswith('http') %}
                                    <a href="{{ video.path_processed }}" download class="action-btn processed">
                                        <i class="fas fa-download"></i> Processado
                                    </a>
                                {% else %}
                                    <a href="/media/{{ video.path_processed }}" download class="action-btn processed">
                                        <i class="fas fa-download"></i> Processado
                                    </a>
                                {% endif %}
                            {% endif %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-gallery">
                    <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 20px;"></i>
                    <p>Nenhum vídeo encontrado.</p>
                    <p style="font-size: 1rem; margin-top: 10px;">Faça o upload de um vídeo para começar!</p>
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        // Debug detalhado
        console.log('=== Gallery Debug ===');
        
        // Verificar todas as thumbnails
        document.querySelectorAll('.thumbnail').forEach((img, index) => {
            console.log(`Thumbnail ${index + 1}:`, {
                src: img.src,
                alt: img.alt,
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
                complete: img.complete
            });
            
            // Adicionar listener para quando a imagem carregar
            img.addEventListener('load', function() {
                console.log(`✅ Thumbnail ${index + 1} carregada com sucesso`);
            });
            
            // Adicionar listener para erros
            img.addEventListener('error', function(e) {
                console.error(`❌ Erro ao carregar thumbnail ${index + 1}:`, img.src);
            });
        });
        
        // Verificar links de download
        document.querySelectorAll('.action-btn').forEach((link, index) => {
            console.log(`Link ${index + 1}:`, link.href);
        });
        
        // Testar se conseguimos acessar uma thumbnail diretamente
        const testThumbnail = document.querySelector('.thumbnail');
        if (testThumbnail) {
            fetch(testThumbnail.src, { method: 'HEAD' })
                .then(response => {
                    if (response.ok) {
                        console.log('✅ Thumbnail acessível via fetch:', testThumbnail.src);
                    } else {
                        console.error('❌ Thumbnail não acessível:', response.status, testThumbnail.src);
                    }
                })
                .catch(error => {
                    console.error('❌ Erro ao verificar thumbnail:', error);
                });
        }
    </script>
</body>
</html>'''

    # Escreve o conteúdo no arquivo
    output_file.write_text(template_content, encoding='utf-8')
    print(f"✅ Arquivo '{output_file}' criado com sucesso com o novo template!")


# Este bloco faz com que o script seja executável
if __name__ == "__main__":
    create_gallery_template()
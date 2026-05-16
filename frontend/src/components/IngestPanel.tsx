import React, { useState, useEffect } from 'react';

interface Source {
  [key: string]: {
    name: string;
    docs_urls: string[];
  };
}

export const IngestPanel: React.FC = () => {
  const [sources, setSources] = useState<Source>({});
  const [newTech, setNewTech] = useState('');
  const [newTechName, setNewTechName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Cargar sources
  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const res = await fetch('/api/v1/sources');
      const data = await res.json();
      setSources(data.sources);
    } catch (err) {
      console.error('Error loading sources:', err);
      setMessage('❌ Error cargando fuentes');
    }
  };

  // Agregar URL
  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTech || !newUrl) {
      setMessage('⚠️ Completa todos los campos');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/v1/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technology: newTech.toLowerCase(),
          name: newTechName || newTech,
          url: newUrl,
          selector_content: 'article'
        })
      });

      const data = await res.json();
      if (data.success) {
        setSources(data.sources);
        setMessage(`✅ URL agregada a ${newTech}`);
        setNewTech('');
        setNewTechName('');
        setNewUrl('');
      } else {
        setMessage(`❌ Error: ${data.message}`);
      }
    } catch (err) {
      setMessage(`❌ Error: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  // Eliminar URL
  const handleRemoveUrl = async (tech: string, url: string) => {
    if (!window.confirm(`¿Eliminar esta URL de ${tech}?`)) return;
    
    setLoading(true);
    try {
      const encodedUrl = encodeURIComponent(url);
      const res = await fetch(`/api/v1/sources/${tech}/${encodedUrl}`, {
        method: 'DELETE'
      });

      const data = await res.json();
      if (data.success) {
        setSources(data.sources);
        setMessage('✅ URL eliminada');
      }
    } catch (err) {
      setMessage(`❌ Error: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  // Ingestar tecnología
  const handleIngest = async (tech: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technology: tech,
          ingest_now: true
        })
      });

      const data = await res.json();
      if (data.success) {
        setMessage(`✅ ${tech} ingested: ${data.chunks_ingested} chunks`);
      } else {
        setMessage(`❌ Error: ${data.message}`);
      }
    } catch (err) {
      setMessage(`❌ Error: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ingest-panel">
      <h2>📚 Gestor de Documentación</h2>

      {/* Formulario de agregar */}
      <form onSubmit={handleAddSource} className="add-source-form">
        <h3>Agregar Nueva URL</h3>
        
        <input
          type="text"
          placeholder="Tecnología (ej: fastapi, python)"
          value={newTech}
          onChange={(e) => setNewTech(e.target.value)}
          disabled={loading}
        />

        <input
          type="text"
          placeholder="Nombre (ej: FastAPI)"
          value={newTechName}
          onChange={(e) => setNewTechName(e.target.value)}
          disabled={loading}
        />

        <input
          type="url"
          placeholder="URL de documentación"
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          disabled={loading}
        />

        <button type="submit" disabled={loading}>
          {loading ? '⏳ Procesando...' : '➕ Agregar URL'}
        </button>
      </form>

      {/* Mensaje de estado */}
      {message && (
        <div className={`message ${message.includes('✅') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      {/* Lista de URLs por tecnología */}
      <div className="sources-list">
        <h3>URLs Configuradas</h3>
        {Object.entries(sources).length === 0 ? (
          <p className="empty-state">No hay fuentes configuradas</p>
        ) : (
          Object.entries(sources).map(([tech, config]) => (
            <div key={tech} className="tech-group">
              <h4>
                {config.name} 
                <span className="tech-slug">({tech})</span>
              </h4>
              
              <ul className="url-list">
                {config.docs_urls.map((url: string) => (
                  <li key={url} className="url-item">
                    <a 
                      href={url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      title={url}
                    >
                      {url.substring(0, 60)}
                      {url.length > 60 ? '...' : ''}
                    </a>
                    <button
                      onClick={() => handleRemoveUrl(tech, url)}
                      disabled={loading}
                      className="remove-btn"
                      title="Eliminar URL"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleIngest(tech)}
                disabled={loading}
                className="ingest-btn"
              >
                {loading ? '⏳ Ingesting...' : `🔄 Ingestar ${config.name}`}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

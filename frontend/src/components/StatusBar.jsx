import React from 'react';
import { FiCpu, FiHardDrive, FiDatabase } from 'react-icons/fi';

function StatusBar({ stats, health }) {
    const formatMemory = (mb) => {
        if (!mb) return 'N/A';
        if (mb > 1024) return `${(mb / 1024).toFixed(1)} GB`;
        return `${Math.round(mb)} MB`;
    };

    return (
        <div className="status-bar">
            <div className="status-left">
                <div className="status-stat">
                    <FiCpu />
                    <span>CPU: {stats?.system?.cpu_percent || 0}%</span>
                </div>
                <div className="status-stat">
                    <FiHardDrive />
                    <span>RAM: {formatMemory(stats?.system?.memory_available_mb)}</span>
                </div>
                <div className="status-stat">
                    <FiDatabase />
                    <span>Документов: {stats?.vector_db?.document_count || 0}</span>
                </div>
            </div>
            <div className="status-right">
                <span className={`status-badge ${health?.ollama_available ? 'online' : 'offline'}`}>
                    {health?.ollama_available ? 'Ollama Online' : 'Ollama Offline'}
                </span>
                <span className={`status-badge ${health?.chromadb_available ? 'online' : 'offline'}`}>
                    {health?.chromadb_available ? 'ChromaDB Online' : 'ChromaDB Offline'}
                </span>
            </div>
        </div>
    );
}

export default StatusBar;
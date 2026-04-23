import React, { useState, useEffect } from 'react';
import { FiPlus, FiFolder } from 'react-icons/fi';
import ChatItem from './ChatItem';
import { getStats, getHealth, scanDocuments } from '../services/api';
import toast from 'react-hot-toast';

function ChatSidebar({ chats, currentChatId, onSelectChat, onCreateChat, onUpdateChat, onDeleteChat }) {
    const [isCreating, setIsCreating] = useState(false);
    const [newChatName, setNewChatName] = useState('');
    const [stats, setStats] = useState(null);
    const [health, setHealth] = useState(null);
    const [isScanning, setIsScanning] = useState(false);
    const [ollamaModel, setOllamaModel] = useState('загрузка...');
    const [isLoading, setIsLoading] = useState(true);

    const pinnedChats = chats.filter(chat => chat.pinned);
    const otherChats = chats.filter(chat => !chat.pinned);

    const loadModelInfo = async () => {
        try {
            const response = await fetch('http://localhost:8080/');
            const data = await response.json();
            setOllamaModel(data.ollama_model || 'deepseek-r1:8b');
        } catch (error) {
            console.error('Ошибка загрузки модели:', error);
            setOllamaModel('deepseek-r1:8b');
        }
    };

    const loadStats = async () => {
        try {
            const data = await getStats();
            setStats(data);
        } catch (error) {
            console.error('Ошибка загрузки статистики:', error);
        }
    };

    const loadHealth = async () => {
        try {
            const data = await getHealth();
            setHealth(data);
        } catch (error) {
            console.error('Ошибка загрузки здоровья:', error);
        }
    };

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            await Promise.all([
                loadModelInfo(),
                loadStats(),
                loadHealth()
            ]);
            setIsLoading(false);
        };
        loadData();
        
        const interval = setInterval(() => {
            loadStats();
            loadHealth();
        }, 60000);
        
        return () => clearInterval(interval);
    }, []);

    const handleScanDocuments = async () => {
        setIsScanning(true);
        try {
            await scanDocuments();
            toast.success('Документы просканированы и проиндексированы');
            await loadStats();
        } catch (error) {
            toast.error('Ошибка сканирования документов');
        } finally {
            setIsScanning(false);
        }
    };

    const handleCreateChat = () => {
        if (newChatName.trim()) {
            onCreateChat(newChatName.trim());
            setNewChatName('');
            setIsCreating(false);
        }
    };

    const isOllamaConnected = health?.ollama_available;
    const isChromaConnected = health?.chromadb_available;

    if (isLoading) {
        return (
            <div className="chat-sidebar">
                <div className="sidebar-header">
                    <h2>💬 Чаты</h2>
                    <button className="new-chat-btn" onClick={() => setIsCreating(true)}>
                        <FiPlus size={18} />
                    </button>
                </div>
                <div className="loading-sidebar">Загрузка...</div>
            </div>
        );
    }

    return (
        <div className="chat-sidebar">
            <div className="sidebar-header">
                <h2>💬 Чаты</h2>
                <button className="new-chat-btn" onClick={() => setIsCreating(true)}>
                    <FiPlus size={18} />
                </button>
            </div>

            {isCreating && (
                <div className="new-chat-form">
                    <input
                        type="text"
                        placeholder="Название чата"
                        value={newChatName}
                        onChange={(e) => setNewChatName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleCreateChat()}
                        autoFocus
                    />
                    <button onClick={handleCreateChat}>Создать</button>
                    <button onClick={() => setIsCreating(false)}>Отмена</button>
                </div>
            )}

            <div className="status-indicators">
                <div className={`status-item ${isOllamaConnected ? 'online' : 'offline'}`}>
                    <span className="status-dot"></span>
                    <span>Ollama ({ollamaModel})</span>
                </div>
                <div className={`status-item ${isChromaConnected ? 'online' : 'offline'}`}>
                    <span className="status-dot"></span>
                    <span>ChromaDB ({stats?.vector_db?.document_count || 0})</span>
                </div>
            </div>

            <div className="documents-info">
                <div className="info-card">
                    <FiFolder size={16} />
                    <div className="info-text">
                        <strong>Документы:</strong>
                        <span>{stats?.documents_count || 0} файлов</span>
                    </div>
                    <button 
                        className="scan-btn" 
                        onClick={handleScanDocuments}
                        disabled={isScanning}
                        title="Сканировать папку с документами"
                    >
                        {isScanning ? '⏳' : '🔄'}
                    </button>
                </div>
                <div className="info-hint">
                    Документы автоматически загружаются из папки <code>backend/data/documents/</code>
                </div>
            </div>

            {pinnedChats.length > 0 && (
                <div className="chat-section">
                    <div className="section-title">📌 Закрепленные</div>
                    {pinnedChats.map(chat => (
                        <ChatItem
                            key={chat.id}
                            chat={chat}
                            isActive={currentChatId === chat.id}
                            onSelect={() => onSelectChat(chat.id)}
                            onUpdate={onUpdateChat}
                            onDelete={onDeleteChat}
                        />
                    ))}
                </div>
            )}

            <div className="chat-section">
                <div className="section-title">📋 Все чаты</div>
                {otherChats.map(chat => (
                    <ChatItem
                        key={chat.id}
                        chat={chat}
                        isActive={currentChatId === chat.id}
                        onSelect={() => onSelectChat(chat.id)}
                        onUpdate={onUpdateChat}
                        onDelete={onDeleteChat}
                        />
                    ))}
                </div>
            
        </div>
    );
}

export default ChatSidebar;
import React, { useState } from 'react';
import { FiMoreVertical, FiEdit2, FiTrash2, FiStar } from 'react-icons/fi';

function ChatItem({ chat, isActive, onSelect, onUpdate, onDelete }) {
    const [isEditing, setIsEditing] = useState(false);
    const [editName, setEditName] = useState(chat.name);
    const [showMenu, setShowMenu] = useState(false);

    const handleRename = () => {
        if (editName.trim() && editName !== chat.name) {
            onUpdate(chat.id, { name: editName.trim() });
        }
        setIsEditing(false);
        setShowMenu(false);
    };

    const handlePin = () => {
        onUpdate(chat.id, { pinned: !chat.pinned });
        setShowMenu(false);
    };

    const handleDelete = () => {
        if (window.confirm(`Удалить чат "${chat.name}"?`)) {
            onDelete(chat.id);
        }
        setShowMenu(false);
    };

    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (days === 0) return 'сегодня';
        if (days === 1) return 'вчера';
        if (days < 7) return `${days} дня назад`;
        return date.toLocaleDateString();
    };

    return (
        <div className={`chat-item ${isActive ? 'active' : ''}`} onClick={() => onSelect()}>
            <div className="chat-icon">
                {chat.pinned ? <FiStar size={14} color="#fbbf24" /> : '💬'}
            </div>
            
            <div className="chat-info">
                {isEditing ? (
                    <input
                        className="chat-edit-input"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onBlur={handleRename}
                        onKeyPress={(e) => e.key === 'Enter' && handleRename()}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                    />
                ) : (
                    <>
                        <div className="chat-name">{chat.name}</div>
                        <div className="chat-date">{formatDate(chat.updated_at)}</div>
                    </>
                )}
            </div>
            
            <button 
                className="chat-menu-btn"
                onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(!showMenu);
                }}
            >
                <FiMoreVertical size={16} />
            </button>
            
            {showMenu && (
                <div className="chat-menu">
                    <button onClick={handlePin}>
                        <FiStar size={14} />
                        {chat.pinned ? ' Открепить' : ' Закрепить'}
                    </button>
                    <button onClick={() => {
                        setIsEditing(true);
                        setShowMenu(false);
                    }}>
                        <FiEdit2 size={14} /> Переименовать
                    </button>
                    <button onClick={handleDelete} className="danger">
                        <FiTrash2 size={14} /> Удалить
                    </button>
                </div>
            )}
        </div>
    );
}

export default ChatItem;
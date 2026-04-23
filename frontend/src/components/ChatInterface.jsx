import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { FiSend, FiSun, FiMoon } from 'react-icons/fi';

function ChatInterface({ messages, onSendMessage, isLoading, chatName, isDarkTheme, onToggleTheme }) {
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (inputValue.trim() && !isLoading) {
            onSendMessage(inputValue.trim());
            setInputValue('');
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleInputChange = (e) => {
        setInputValue(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
    };

    return (
        <div className="chat-interface">
            <div className="chat-header">
                <div className="chat-header-info">
                    <h1>📚 Корпоративный Ассистент</h1>
                    {chatName && <span className="chat-badge">{chatName}</span>}
                </div>
                <button 
                    className="theme-toggle-btn-header" 
                    onClick={onToggleTheme} 
                    title={isDarkTheme ? 'Светлая тема' : 'Тёмная тема'}
                >
                    {isDarkTheme ? <FiSun size={18} /> : <FiMoon size={18} />}
                </button>
            </div>

            <div className="messages-container">
                {messages.length === 0 && (
                    <div className="welcome-message">
                        <div className="welcome-icon">🤖</div>
                        <h3>Добро пожаловать!</h3>
                        <p>Задайте вопрос по нормативным документам (ГОСТ, СНиП, СанПиН и др.)</p>
                        <div className="welcome-tips">
                            <div className="tip">📄 Поддерживаются: PDF, DOCX, TXT</div>
                            <div className="tip">🔍 Гибридный поиск: векторный + ключевые слова</div>
                            <div className="tip">💡 Используйте filter:ГОСТ для фильтрации</div>
                        </div>
                    </div>
                )}
                
                {messages.map((msg, idx) => (
                    <div key={msg.id || idx} className={`message ${msg.role}`}>
                        <div className="message-avatar">
                            {msg.role === 'user' ? '👤' : '🤖'}
                        </div>
                        <div className="message-content">
                            <div className="message-text">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="message-sources">
                                    <strong>📚 Источники:</strong>
                                    {msg.sources.map((src, i) => (
                                        <span key={i} className="source-tag">{src}</span>
                                    ))}
                                </div>
                            )}
                            <div className="message-time">
                                {new Date(msg.timestamp).toLocaleTimeString()}
                            </div>
                        </div>
                    </div>
                ))}
                
                {isLoading && (
                    <div className="message assistant">
                        <div className="message-avatar">🤖</div>
                        <div className="message-content">
                            <div className="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-form" onSubmit={handleSubmit}>
                <textarea
                    ref={textareaRef}
                    value={inputValue}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Введите вопрос по нормативным документам... (Enter - отправить, Shift+Enter - новая строка)"
                    disabled={isLoading}
                    rows={1}
                />
                <button type="submit" disabled={!inputValue.trim() || isLoading}>
                    {isLoading ? <div className="spinner-small" /> : <FiSend />}
                </button>
            </form>
        </div>
    );
}

export default ChatInterface;
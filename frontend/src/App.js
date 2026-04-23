import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import ChatInterface from './components/ChatInterface';
import ChatSidebar from './components/ChatSidebar';
import { getChats, createChat, updateChat, deleteChat, getChat, sendMessage } from './services/api';
import './styles/App.css';

function App() {
    const [chats, setChats] = useState([]);
    const [currentChatId, setCurrentChatId] = useState(null);
    const [currentChat, setCurrentChat] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isDarkTheme, setIsDarkTheme] = useState(() => {
        const saved = localStorage.getItem('theme');
        return saved !== null ? saved === 'dark' : true;
    });
    const [isLoadingChats, setIsLoadingChats] = useState(true);
    
    // Флаг для предотвращения двойной загрузки
    const hasLoaded = useRef(false);

    const loadChats = useCallback(async () => {
        setIsLoadingChats(true);
        try {
            const data = await getChats();
            setChats(data);
            
            if (data.length > 0 && !currentChatId) {
                setCurrentChatId(data[0].id);
            } else if (data.length === 0) {
                const newChat = await createChat('Новый чат');
                setChats([newChat]);
                setCurrentChatId(newChat.id);
            }
        } catch (error) {
            console.error('Ошибка загрузки чатов:', error);
            toast.error('Не удалось загрузить чаты');
        } finally {
            setIsLoadingChats(false);
        }
    }, [currentChatId]);

    const loadChat = useCallback(async (chatId) => {
        try {
            const chat = await getChat(chatId);
            setCurrentChat(chat);
        } catch (error) {
            console.error('Ошибка загрузки чата:', error);
        }
    }, []);

    useEffect(() => {
        if (!hasLoaded.current) {
            hasLoaded.current = true;
            loadChats();
        }
    }, [loadChats]);

    useEffect(() => {
        if (currentChatId) {
            loadChat(currentChatId);
        }
    }, [currentChatId, loadChat]);

    useEffect(() => {
        if (isDarkTheme) {
            document.body.setAttribute('data-theme', 'dark');
            document.body.classList.remove('light-theme');
            document.body.classList.add('dark-theme');
        } else {
            document.body.setAttribute('data-theme', 'light');
            document.body.classList.remove('dark-theme');
            document.body.classList.add('light-theme');
        }
        localStorage.setItem('theme', isDarkTheme ? 'dark' : 'light');
    }, [isDarkTheme]);

    const handleSendMessage = async (message) => {
        if (!currentChatId) {
            toast.error('Нет активного чата');
            return;
        }

        setIsLoading(true);
        
        try {
            const userMessage = {
                id: Date.now().toString(),
                role: 'user',
                content: message,
                timestamp: new Date().toISOString(),
                sources: []
            };
            
            setCurrentChat(prev => ({
                ...prev,
                messages: [...(prev?.messages || []), userMessage]
            }));

            const response = await sendMessage(message, currentChatId);
            
            const assistantMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.response,
                timestamp: new Date().toISOString(),
                sources: response.sources || []
            };
            
            setCurrentChat(prev => ({
                ...prev,
                messages: [...(prev?.messages || []), assistantMessage]
            }));
            
            await loadChats();
            
        } catch (error) {
            console.error('Ошибка отправки:', error);
            toast.error(error.response?.data?.detail || 'Ошибка отправки сообщения');
            
            setCurrentChat(prev => ({
                ...prev,
                messages: prev?.messages?.slice(0, -1) || []
            }));
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateChat = async (name) => {
        try {
            const newChat = await createChat(name);
            const updatedChats = [newChat, ...chats];
            setChats(updatedChats);
            setCurrentChatId(newChat.id);
            toast.success('Чат создан');
        } catch (error) {
            console.error('Ошибка создания чата:', error);
            toast.error('Не удалось создать чат');
        }
    };

    const handleUpdateChat = async (chatId, updates) => {
        try {
            const updated = await updateChat(chatId, updates);
            const updatedChats = chats.map(chat => chat.id === chatId ? updated : chat);
            setChats(updatedChats);
            if (currentChatId === chatId) {
                setCurrentChat(updated);
            }
            toast.success('Чат обновлен');
        } catch (error) {
            console.error('Ошибка обновления чата:', error);
            toast.error('Не удалось обновить чат');
        }
    };

    const handleDeleteChat = async (chatId) => {
        try {
            await deleteChat(chatId);
            const updatedChats = chats.filter(chat => chat.id !== chatId);
            setChats(updatedChats);
            
            if (currentChatId === chatId && updatedChats.length > 0) {
                setCurrentChatId(updatedChats[0].id);
            } else if (updatedChats.length === 0) {
                const newChat = await createChat('Новый чат');
                setChats([newChat]);
                setCurrentChatId(newChat.id);
            }
            toast.success('Чат удален');
        } catch (error) {
            console.error('Ошибка удаления чата:', error);
            toast.error('Не удалось удалить чат');
        }
    };

    const toggleTheme = useCallback(() => {
        setIsDarkTheme(prev => !prev);
    }, []);

    if (isLoadingChats) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Загрузка чатов...</p>
            </div>
        );
    }

    return (
        <div className="app">
            <Toaster 
                position="top-right"
                toastOptions={{
                    duration: 3000,
                    style: {
                        background: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border)'
                    }
                }}
            />
            
            <ChatSidebar
                chats={chats}
                currentChatId={currentChatId}
                onSelectChat={setCurrentChatId}
                onCreateChat={handleCreateChat}
                onUpdateChat={handleUpdateChat}
                onDeleteChat={handleDeleteChat}
            />
            
            <div className="main-content">
                <ChatInterface
                    messages={currentChat?.messages || []}
                    onSendMessage={handleSendMessage}
                    isLoading={isLoading}
                    chatName={currentChat?.name}
                    isDarkTheme={isDarkTheme}
                    onToggleTheme={toggleTheme}
                />
            </div>
        </div>
    );
}

export default App;
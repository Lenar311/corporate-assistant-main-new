import axios from 'axios';

// Конфигурация
const API_TIMEOUT = 180000;
const HEALTH_TIMEOUT = 3000;

let API_BASE_URL = 'http://localhost:8080';

// Создаем axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
    timeout: API_TIMEOUT,
});

// 🔥 КЭШ ДЛЯ ЧАСТЫХ ЗАПРОСОВ
const responseCache = new Map();
const CACHE_TTL = 10 * 60 * 1000; // 10 минут

const getCached = (key) => {
    const cached = responseCache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data;
    }
    return null;
};

const setCached = (key, data) => {
    responseCache.set(key, { data, timestamp: Date.now() });
};

// ============================================================================
// ЧАТ
// ============================================================================

export const sendMessage = async (message, chatId) => {
    const cacheKey = `msg:${message.toLowerCase().trim()}`;
    const cached = getCached(cacheKey);
    if (cached) {
        return cached;
    }
    
    try {
        const response = await api.post('/chat', { message, chat_id: chatId });
        setCached(cacheKey, response.data);
        return response.data;
    } catch (error) {
        console.error('Ошибка отправки:', error);
        throw error;
    }
};

// ============================================================================
// ЧАТЫ
// ============================================================================

export const getChats = async () => {
    try {
        const response = await api.get('/chats');
        return response.data;
    } catch (error) {
        console.error('Ошибка getChats:', error);
        return [];
    }
};

export const createChat = async (name) => {
    try {
        const response = await api.post('/chats', { name });
        return response.data;
    } catch (error) {
        console.error('Ошибка createChat:', error);
        throw error;
    }
};

export const updateChat = async (chatId, updates) => {
    try {
        const response = await api.put(`/chats/${chatId}`, updates);
        return response.data;
    } catch (error) {
        console.error('Ошибка updateChat:', error);
        throw error;
    }
};

export const deleteChat = async (chatId) => {
    try {
        const response = await api.delete(`/chats/${chatId}`);
        return response.data;
    } catch (error) {
        console.error('Ошибка deleteChat:', error);
        throw error;
    }
};

export const getChat = async (chatId) => {
    try {
        const response = await api.get(`/chats/${chatId}`);
        return response.data;
    } catch (error) {
        console.error('Ошибка getChat:', error);
        return null;
    }
};

// ============================================================================
// ДОКУМЕНТЫ
// ============================================================================

export const getDocuments = async () => {
    try {
        const response = await api.get('/documents/list');
        return response.data;
    } catch (error) {
        console.error('Ошибка getDocuments:', error);
        return [];
    }
};

export const scanDocuments = async () => {
    try {
        const response = await api.post('/documents/scan');
        return response.data;
    } catch (error) {
        console.error('Ошибка scanDocuments:', error);
        throw error;
    }
};

// ============================================================================
// СТАТИСТИКА
// ============================================================================

export const getStats = async () => {
    try {
        const response = await api.get('/stats', { timeout: 10000 });
        return response.data;
    } catch (error) {
        console.error('Ошибка getStats:', error);
        return { vector_db: { document_count: 0 }, documents_count: 0 };
    }
};

export const getHealth = async () => {
    try {
        const response = await api.get('/health', { timeout: 5000 });
        return response.data;
    } catch (error) {
        console.error('Ошибка getHealth:', error);
        return { status: 'unhealthy' };
    }
};
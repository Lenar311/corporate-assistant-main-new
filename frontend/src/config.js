const config = {
    API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8080',
    DEFAULT_TOP_K: 15,
    MAX_FILE_SIZE_MB: 30,
    SUPPORTED_FORMATS: ['.pdf', '.docx', '.doc'],
    OLLAMA_MODEL: process.env.REACT_APP_OLLAMA_MODEL || 'deepseek-r1:8b',
    EMBEDDING_MODEL: process.env.REACT_APP_EMBEDDING_MODEL || 'BAAI/bge-m3'
};

export default config;
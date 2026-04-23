import React, { useState, useEffect } from 'react';
import { FiUpload, FiX, FiFile } from 'react-icons/fi';
import { uploadDocument, getFormats } from '../services/api';
import toast from 'react-hot-toast';

function DocumentUploader({ onClose }) {
    const [isUploading, setIsUploading] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [supportedFormats, setSupportedFormats] = useState([]);

    useEffect(() => {
        getFormats().then(data => {
            setSupportedFormats(data.formats || ['.txt', '.pdf', '.docx', '.doc']);
        }).catch(console.error);
    }, []);

    const handleFileSelect = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        if (!supportedFormats.includes(fileExt)) {
            toast.error(`Неподдерживаемый формат. Разрешены: ${supportedFormats.join(', ')}`);
            return;
        }

        if (file.size > 30 * 1024 * 1024) {
            toast.error('Файл слишком большой (макс 30MB)');
            return;
        }

        setSelectedFile(file);
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setIsUploading(true);
        try {
            await uploadDocument(selectedFile);
            toast.success(`Файл "${selectedFile.name}" успешно загружен!`);
            onClose();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Ошибка загрузки');
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="uploader-modal">
            <div className="uploader-content">
                <div className="uploader-header">
                    <h3>Загрузка документа</h3>
                    <button className="close-btn" onClick={onClose}>
                        <FiX />
                    </button>
                </div>
                
                <div className="uploader-body">
                    <div className="drop-zone" onClick={() => document.getElementById('file-input').click()}>
                        <FiUpload size={32} />
                        <p>Нажмите для выбора файла</p>
                        <span className="formats-hint">Поддерживаются: {supportedFormats.join(', ')}</span>
                        <input
                            id="file-input"
                            type="file"
                            accept={supportedFormats.join(',')}
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                        />
                    </div>
                    
                    {selectedFile && (
                        <div className="selected-file">
                            <FiFile />
                            <span>{selectedFile.name}</span>
                            <span className="file-size">
                                ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                        </div>
                    )}
                </div>
                
                <div className="uploader-footer">
                    <button className="cancel-btn" onClick={onClose}>Отмена</button>
                    <button 
                        className="upload-btn" 
                        onClick={handleUpload}
                        disabled={!selectedFile || isUploading}
                    >
                        {isUploading ? 'Загрузка...' : 'Загрузить'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default DocumentUploader;
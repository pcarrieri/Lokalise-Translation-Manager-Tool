import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, ClientSideRowModelModule } from 'ag-grid-community';

// Importa i componenti esterni
import ConfigEditor from './ConfigEditor';
import ConfigForm from './ConfigForm';
import SummaryDashboard from './SummaryDashboard';
import CleanupModal from './CleanupModal';

// Stili
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import './App.css';

ModuleRegistry.registerModules([ClientSideRowModelModule]);

// --- Componenti UI Ausiliari ---

const LogPanel = ({ logs, logContainerRef }) => (
    <div className="w-full max-w-4xl mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-8">
        <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-800 dark:text-white">Execution Log</h2>
        </div>
        <div ref={logContainerRef} className="log-container">
            {logs.map((log, index) => (
                <p key={index} className={`whitespace-pre-wrap ${
                    log.status === 'error' ? 'text-red-500 font-semibold' :
                    log.isDetail ? 'text-gray-400 dark:text-gray-500' :
                    'text-gray-600 dark:text-gray-300'
                }`}>
                    <span className="font-bold">{new Date().toLocaleTimeString()}:</span> {log.message}
                </p>
            ))}
            {logs.length === 0 && <p className="text-gray-400">In attesa dell'avvio del processo...</p>}
        </div>
    </div>
);

const DarkModeSwitch = ({ darkMode, setDarkMode }) => (
    <div style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', zIndex: 9999 }}>
        <div className="flex flex-col items-center gap-1">
            <span className="text-xs text-gray-500 dark:text-gray-300 font-medium">Dark mode</span>
            <label className="switch">
                <input type="checkbox" checked={darkMode} onChange={() => setDarkMode(prev => !prev)} />
                <span className="slider" />
            </label>
        </div>
    </div>
);

const ReportViewer = ({ files, selectedFile, setSelectedFile, loading, rowData, colDefs, darkMode, hasChanges, onSaveChanges, onCellValueChanged }) => (
    <div className="w-full max-w-7xl mx-auto mt-8">
        <h2 className="text-2xl font-bold mb-4 text-center">Report Generati</h2>
        <div className="file-navbar mb-4">
            <div className="file-tabs">
                {files.map(file => (
                    <button key={file} className={`file-tab ${selectedFile === file ? 'active' : ''}`} onClick={() => setSelectedFile(file)}>
                        {file.replace(/_/g, ' ').replace('.csv', '')}
                    </button>
                ))}
            </div>
            {selectedFile && hasChanges && (
                <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition" onClick={onSaveChanges}>💾 Salva Modifiche</button>
            )}
        </div>
        {loading ? <div className="text-center text-gray-500 mt-8">⏳ Caricamento dati...</div> :
            <div className={"ag-theme-alpine ag-grid-custom" + (darkMode ? " ag-theme-alpine-dark" : "")} style={{ height: '600px', width: '100%' }}>
                <AgGridReact rowData={rowData} columnDefs={colDefs} onCellValueChanged={onCellValueChanged} />
            </div>
        }
    </div>
);

// --- NUOVO Componente per la Barra di Avanzamento ---
const ProgressBar = ({ percentage }) => (
  <div className="w-full max-w-4xl mx-auto bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 my-4">
    <div
      className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-linear"
      style={{ width: `${percentage}%` }}
    ></div>
  </div>
);


// --- Componente Principale App ---

const App = () => {
    const [appState, setAppState] = useState('initializing');
    const [configData, setConfigData] = useState(null);
    const [logs, setLogs] = useState([]);
    const [summaryData, setSummaryData] = useState([]);
    const [progress, setProgress] = useState(0); // <-- NUOVO STATO per la barra
    const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
    const [files, setFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState('');
    const [rowData, setRowData] = useState([]);
    const [originalData, setOriginalData] = useState([]);
    const [colDefs, setColDefs] = useState([]);
    const [hasChanges, setHasChanges] = useState(false);
    const [loading, setLoading] = useState(false);
     // --- NUOVI STATI per la modale di pulizia ---
    const [isCleanupModalOpen, setIsCleanupModalOpen] = useState(false);
    const [keysToCleanup, setKeysToCleanup] = useState([]);

    const logContainerRef = useRef(null);
    const backendURL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5050';

    // Carica la configurazione all'avvio
    useEffect(() => {
        axios.get(`${backendURL}/get-config`)
            .then(res => {
                const config = res.data;
                setConfigData(config);
                if (!config.lokalise?.api_key || !config.openai?.api_key) {
                    setAppState('needs_config');
                } else {
                    setAppState('idle');
                }
            })
            .catch(() => setAppState('error'));
    }, [backendURL]);

    // Gestisce WebSocket
    useEffect(() => {
        const socket = io(backendURL);
        socket.on('connect', () => console.log('Connesso al backend.'));
        socket.on('progress', (data) => setLogs(prev => [...prev, data]));
        socket.on('detailed_log', (data) => {
            const detailedMessage = { ...data, message: `  > ${data.message}`, isDetail: true };
            setLogs(prev => [...prev, detailedMessage]);
        });
        socket.on('summary_data', (data) => {
            setSummaryData(prev => {
                const existingTitles = new Set(prev.map(s => s.title));
                if (!existingTitles.has(data.title)) {
                    return [...prev, data];
                }
                return prev;
            });
        });

        // --- NUOVO LISTENER per la barra di avanzamento ---
        socket.on('progress_update', (data) => {
            setProgress(data.percentage);
        });
        
        socket.on('awaiting_review', (data) => {
            setProgress(100); // La prima parte è completa al 100%
            setAppState('reviewing');
            setFiles(prev => [...new Set([...prev, data.filename])].sort());
            setSelectedFile(data.filename);
        });

        // --- NUOVO LISTENER per la decisione sulla pulizia ---
        socket.on('awaiting_cleanup_decision', (data) => {
            if (data.keys && data.keys.length > 0) {
                setKeysToCleanup(data.keys);
                setIsCleanupModalOpen(true); // Apre la modale
            }
        });

        socket.on('completed', (data) => {
            setProgress(100);
            setLogs(prev => [...prev, data]);
            setAppState('completed');
            axios.get(`${backendURL}/files`).then(res => setFiles(res.data.sort()));
        });

        socket.on('error', (data) => {
            setLogs(prev => [...prev, { message: data.error, status: 'error' }]);
            setAppState('error');
        });

        return () => socket.disconnect();
    }, [backendURL]);

    // Carica dati del file CSV
    useEffect(() => {
        if (selectedFile) {
            setLoading(true);
            axios.get(`${backendURL}/files/${selectedFile}`).then(res => {
                const data = Array.isArray(res.data) ? res.data : [];
                setRowData(data);
                setOriginalData(JSON.stringify(data));
                setHasChanges(false);
                if (data.length > 0) {
                    const columns = Object.keys(data[0]).map(key => ({ field: key, editable: true, sortable: true, filter: true, resizable: true }));
                    setColDefs(columns);
                }
                setLoading(false);
            }).catch(() => setLoading(false));
        }
    }, [selectedFile, backendURL]);
    
    // Gestisce altri effetti
    useEffect(() => { document.documentElement.classList.toggle('dark', darkMode); localStorage.setItem('theme', darkMode ? 'dark' : 'light'); }, [darkMode]);
    useEffect(() => { if (logContainerRef.current) { logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight; } }, [logs]);


    // --- Funzioni di Gestione ---
    const handleStartProcess = () => {
        setLogs([]);
        setSummaryData([]);
        setProgress(0);
        setKeysToCleanup([]); // Azzera le chiavi da cancellare
        setAppState('running');
        axios.post(`${backendURL}/run-tool`);
    };

    const handleSaveConfig = (newConfig) => {
        axios.post(`${backendURL}/save-config`, newConfig)
            .then(() => {
                alert('✅ Configurazione salvata!');
                setConfigData(newConfig);
                if (appState === 'needs_config' && newConfig.lokalise?.api_key && newConfig.openai?.api_key) {
                    setAppState('idle');
                }
            })
            .catch(() => alert('❌ Errore salvataggio.'));
    };

    const onSaveChanges = () => {
        return new Promise((resolve) => {
            axios.post(`${backendURL}/files/${selectedFile}`, rowData).then(() => {
                alert('✅ Modifiche salvate.');
                setOriginalData(JSON.stringify(rowData));
                setHasChanges(false);
                resolve();
            });
        });
    };
    
    const onCellValueChanged = (params) => {
        const updatedData = params.api.getDataAsCsv().split("\n").map(line => line.split(","));
        const headers = updatedData.shift();
        const newRowData = updatedData.map(row => {
            let obj = {};
            headers.forEach((header, i) => obj[header] = row[i]);
            return obj;
        });

        setRowData(newRowData);
        if (!hasChanges) setHasChanges(true);
    };

        // --- NUOVE FUNZIONI per gestire la modale di pulizia ---
    const handleConfirmCleanup = () => {
        axios.post(`${backendURL}/execute-cleanup`, { keys: keysToCleanup })
            .then(() => {
                setLogs(prev => [...prev, { message: 'Richiesta di cancellazione inviata al backend.', isDetail: false }]);
            })
            .catch(() => {
                setLogs(prev => [...prev, { message: 'ERRORE: Impossibile inviare la richiesta di cancellazione.', status: 'error' }]);
            });
        setIsCleanupModalOpen(false); // Chiude la modale
    };

    const handleCancelCleanup = () => {
        setLogs(prev => [...prev, { message: 'Cancellazione delle chiavi saltata dall\'utente.', isDetail: false }]);
        setIsCleanupModalOpen(false); // Chiude la modale
    };

    const handleResumeUpload = async () => {
        if (hasChanges) {
            await onSaveChanges();
        }
        setProgress(0); // <-- Azzera la barra per la seconda parte
        setAppState('running');
        axios.post(`${backendURL}/resume-upload`);
    };

    // --- Render Condizionale ---
    const renderContent = () => {
        switch (appState) {
            case 'initializing': return <div className="text-center text-gray-500 mt-10">Caricamento...</div>;
            case 'needs_config': return <ConfigForm onSave={handleSaveConfig} />;
            case 'idle': return <ConfigEditor config={configData} setConfig={setConfigData} onStart={handleStartProcess} onSave={() => handleSaveConfig(configData)} />;
            
            case 'running':
            case 'error':
                return (
                    <>
                        {appState === 'running' && <ProgressBar percentage={progress} />}
                        <LogPanel logs={logs} logContainerRef={logContainerRef} />
                        <SummaryDashboard summaries={summaryData} darkMode={darkMode} />
                    </>
                );
            case 'reviewing':
            case 'completed':
                return (
                    <>
                        <LogPanel logs={logs} logContainerRef={logContainerRef} />
                        <SummaryDashboard summaries={summaryData} darkMode={darkMode} />
                        
                        {appState === 'reviewing' && (
                            <div className="w-full max-w-4xl mx-auto text-center p-4 bg-yellow-100 dark:bg-yellow-900 border border-yellow-300 dark:border-yellow-700 rounded-lg">
                                <h3 className="font-bold text-yellow-800 dark:text-yellow-200">Revisione Richiesta</h3>
                                <p className="text-sm text-yellow-700 dark:text-yellow-300">Controlla e modifica le traduzioni generate qui sotto. Quando hai finito, salva e procedi con l'upload.</p>
                                <button onClick={handleResumeUpload} className="primary mt-4">
                                    Approva e Carica su Lokalise
                                </button>
                            </div>
                        )}

                        <ReportViewer 
                            files={files} selectedFile={selectedFile} setSelectedFile={setSelectedFile}
                            loading={loading} rowData={rowData} colDefs={colDefs} darkMode={darkMode}
                            hasChanges={hasChanges} onSaveChanges={onSaveChanges} onCellValueChanged={onCellValueChanged}
                        />
                    </>
                );
            default: return null;
        }
    };

    return (
        <div className="page-container">
            <h1 className="toolbar-title mb-8">Lokalise Translation Manager</h1>
            
            {renderContent()}

            {/* --- NUOVO: Render della modale --- */}
            <CleanupModal
                isOpen={isCleanupModalOpen}
                keys={keysToCleanup}
                onConfirm={handleConfirmCleanup}
                onCancel={handleCancelCleanup}
            />
            
            <DarkModeSwitch darkMode={darkMode} setDarkMode={setDarkMode} />
        </div>
    );
};

export default App;
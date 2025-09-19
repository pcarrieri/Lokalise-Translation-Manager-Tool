import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import axios from 'axios';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, ClientSideRowModelModule, TextFilterModule, NumberFilterModule } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { Toaster, toast } from 'react-hot-toast';

import './App.css';

// Registrazione Moduli AG Grid
ModuleRegistry.registerModules([ClientSideRowModelModule, TextFilterModule, NumberFilterModule]);

// --- CONFIGURAZIONE E HOOKS ---
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5050';
const SPECIAL_FILES_CONFIG = {
  'final_report.csv': 'Final Report',
  'ready_to_be_deleted.csv': 'Keys to Delete',
  'translation_done.csv': 'Complete Translations',
  'missing_translations.csv': 'Missing Translations',
};

const useDarkMode = () => {
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
  useEffect(() => {
    const html = document.documentElement;
    darkMode ? html.classList.add('dark') : html.classList.remove('dark');
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);
  return [darkMode, setDarkMode];
};

// Hook per i dati, semplificato senza logica AI
const useGridData = (selectedFile) => {
  const [rowData, setRowData] = useState([]);
  const [originalData, setOriginalData] = useState([]);
  const [colDefs, setColDefs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modifiedRowIds, setModifiedRowIds] = useState(new Set());

  useEffect(() => {
    if (!selectedFile) {
      setRowData([]); setOriginalData([]); setColDefs([]); setModifiedRowIds(new Set());
      return;
    }
    const fetchData = async () => {
      setLoading(true);
      setModifiedRowIds(new Set());
      try {
        const { data } = await axios.get(`${BACKEND_URL}/files/${selectedFile}`);
        const validData = Array.isArray(data) ? data : [];
        setRowData(validData);
        setOriginalData(JSON.parse(JSON.stringify(validData)));

        if (validData.length > 0) {
          const dynamicColumns = Object.keys(validData[0]).map(key => ({
            field: key,
            headerName: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
            editable: true, sortable: true, filter: true, resizable: true,
          }));
          
          const staticFirstColumn = { width: 80, headerCheckboxSelection: true, checkboxSelection: true, showDisabledCheckboxes: true, editable: false, cellRenderer: params => ( modifiedRowIds.has(params.data.key_id) && <div className="dirty-indicator"></div> ), cellClass: 'dirty-indicator-cell' };
          setColDefs([staticFirstColumn, ...dynamicColumns]);
        } else {
          setColDefs([]);
        }
      } catch (error) { toast.error(`🔥 Failed to load file: ${error.message}`); } 
      finally { setLoading(false); }
    };
    fetchData();
  }, [selectedFile]);

  return { loading, rowData, setRowData, originalData, colDefs, modifiedRowIds, setModifiedRowIds };
};

// --- ICONE E COMPONENTI UI (invariati) ---
const SearchIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;
const UndoIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7v6h6"></path><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path></svg>;
const RedoIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 7v6h-6"></path><path d="M3 17a9 9 0 0 0 9 9 9 9 0 0 0 6-2.3L21 13"></path></svg>;
const ExportIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>;
const ResetIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3l-4.3 4.3a4 4 0 0 0-5.7 5.7l-4.3 4.3A10 10 0 0 1 2 11.5z"></path></svg>;
const AppHeader = React.memo(({ darkMode, setDarkMode }) => ( <header className="app-header"> <h1>Lokalise Translation Manager</h1> <label className="theme-switch"> <input type="checkbox" checked={darkMode} onChange={() => setDarkMode(prev => !prev)} /> <span className="slider" /> </label> </header> ));
const FileBrowser = React.memo(({ files, selectedFile, setSelectedFile }) => { const specialFiles = Object.keys(SPECIAL_FILES_CONFIG); const otherFiles = files.filter(f => !specialFiles.includes(f)); return ( <nav className="file-browser"> {specialFiles.map(file => files.includes(file) && ( <button key={file} className={`file-tab ${selectedFile === file ? 'active' : ''}`} onClick={() => setSelectedFile(file)}> {SPECIAL_FILES_CONFIG[file]} </button> ))} {otherFiles.length > 0 && ( <select className="file-tab" onChange={(e) => setSelectedFile(e.target.value)} value={specialFiles.includes(selectedFile) ? '' : selectedFile}> <option value="">Other files...</option> {otherFiles.map(file => <option key={file} value={file}>{file}</option>)} </select> )} </nav> ); });
const ActionBar = React.memo(({ onQuickFilterChanged, onExport, onReset, onSave, onUndo, onRedo, hasChanges, canUndo, canRedo }) => ( <div className="action-bar"> <div className="search-input"> <SearchIcon /> <input type="text" placeholder="Search across all columns..." onChange={onQuickFilterChanged} /> </div> <div className="action-buttons"> <button className="action-button" onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl+Z)"><UndoIcon /></button> <button className="action-button" onClick={onRedo} disabled={!canRedo} title="Redo (Ctrl+Y)"><RedoIcon /></button> <button className="action-button" onClick={onExport} title="Export as CSV"><ExportIcon /></button> <button className="action-button" onClick={onReset} disabled={!hasChanges} title="Reset all changes"><ResetIcon /></button> <button className="save-button" onClick={onSave} disabled={!hasChanges}> 💾 <span>Save {hasChanges ? `(${hasChanges})` : ''}</span> </button> </div> </div> ));
const DashboardInfo = React.memo(({ fileName, totalRows, modifiedCount, missingCount }) => ( <div className="dashboard-info"> <div>File: <span>{fileName}</span></div> <div>Total Keys: <span>{totalRows}</span></div> {modifiedCount > 0 && <div>Modified: <span style={{ color: 'var(--warning)' }}>{modifiedCount}</span></div>} {missingCount > 0 && <div>Missing: <span style={{ color: 'var(--danger)' }}>{missingCount}</span></div>} </div> ));
const TranslationGrid = React.memo(({ loading, rowData, colDefs, onGridReady, onCellValueChanged, darkMode, selectedFile }) => { if (loading) { return <div className="grid-wrapper status-message">⏳ Loading data...</div>; } if (!selectedFile) { return <div className="grid-wrapper status-message">👆 Please select a file to begin.</div>; } if (rowData.length === 0 && selectedFile) { return <div className="grid-wrapper status-message">⚠️ This file is empty or has no data.</div>; } return ( <div className="grid-wrapper"> <div className={darkMode ? 'ag-theme-alpine-dark ag-grid-custom' : 'ag-theme-alpine ag-grid-custom'}> <AgGridReact rowData={rowData} columnDefs={colDefs} onGridReady={onGridReady} onCellValueChanged={onCellValueChanged} getRowId={params => params.data.key_id} rowSelection="multiple" suppressRowClickSelection={true} /> </div> </div> ); });


// --- COMPONENTE PRINCIPALE ---
const App = () => {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [darkMode, setDarkMode] = useDarkMode();
  const gridApiRef = useRef(null);
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  
  // Hook dati semplificato, senza la funzione AI
  const { loading, rowData, setRowData, originalData, colDefs, modifiedRowIds, setModifiedRowIds } = useGridData(selectedFile);

  useEffect(() => { axios.get(`${BACKEND_URL}/files`).then(res => setFiles(res.data)); }, []);

  const missingCount = useMemo(() => rowData.filter(row => !row.new_translation || row.new_translation.trim() === '').length, [rowData]);
  
  const onGridReady = useCallback((params) => {
    gridApiRef.current = params.api;
    gridApiRef.current.sizeColumnsToFit();
  }, []);

  const onCellValueChanged = useCallback((params) => {
    const { data, colDef, oldValue, newValue } = params;
    const { key_id } = data;
    const field = colDef.field;
    setUndoStack(prev => [...prev, { key_id, field, oldValue, newValue }]);
    setRedoStack([]);
    
    const originalRow = originalData.find(row => row.key_id === key_id);
    const isSameAsOriginal = originalRow && Object.keys(data).every(key => data[key] === originalRow[key]);

    setModifiedRowIds(prev => {
        const newSet = new Set(prev);
        isSameAsOriginal ? newSet.delete(key_id) : newSet.add(key_id);
        return newSet;
    });
  }, [originalData]);

  const onQuickFilterChanged = useCallback((event) => {
    gridApiRef.current?.setQuickFilter(event.target.value);
  }, []);

  const exportCSV = useCallback(() => {
    gridApiRef.current?.exportDataAsCsv();
    toast.success('📤 CSV Exported!');
  }, []);
  
  const undo = useCallback(() => {
    if (undoStack.length === 0) return;
    const lastAction = undoStack.pop();
    const { key_id, field, oldValue } = lastAction;
    const rowNode = gridApiRef.current?.getRowNode(key_id);
    if (rowNode) { rowNode.setDataValue(field, oldValue); }
    setRedoStack(prev => [...prev, lastAction]);
  }, [undoStack]);

  const redo = useCallback(() => {
    if (redoStack.length === 0) return;
    const lastAction = redoStack.pop();
    const { key_id, field, newValue } = lastAction;
    const rowNode = gridApiRef.current?.getRowNode(key_id);
    if (rowNode) { rowNode.setDataValue(field, newValue); }
    setUndoStack(prev => [...prev, lastAction]);
  }, [redoStack]);

  const saveChanges = useCallback(async () => {
    toast.promise(
      axios.post(`${BACKEND_URL}/files/${selectedFile}`, rowData),
      {
        loading: 'Saving...',
        success: () => {
          setOriginalData(JSON.parse(JSON.stringify(rowData)));
          setModifiedRowIds(new Set());
          setUndoStack([]); setRedoStack([]);
          return '✅ File saved successfully!';
        },
        error: (err) => `❌ Failed to save: ${err.message}`,
      }
    );
  }, [selectedFile, rowData, setModifiedRowIds]);

  const resetFile = useCallback(() => {
    toast((t) => (
      <span>Undo all changes?
        <button className="toast-button" onClick={() => {
          setRowData(JSON.parse(JSON.stringify(originalData)));
          setModifiedRowIds(new Set());
          setUndoStack([]); setRedoStack([]);
          toast.dismiss(t.id);
        }}>Yes</button>
        <button className="toast-button" onClick={() => toast.dismiss(t.id)}>No</button>
      </span>
    ));
  }, [originalData, setRowData, setModifiedRowIds]);
  
  return (
    <>
      <Toaster position="bottom-right" toastOptions={{ style: { background: darkMode ? '#333' : '#fff', color: darkMode ? '#fff' : '#333' }}} />
      <div className="page-container">
        <AppHeader darkMode={darkMode} setDarkMode={setDarkMode} />
        <FileBrowser files={files} selectedFile={selectedFile} setSelectedFile={setSelectedFile} />
        
        {selectedFile && !loading && (
          <>
            <ActionBar 
                onQuickFilterChanged={onQuickFilterChanged}
                onExport={exportCSV}
                onReset={resetFile}
                onSave={saveChanges}
                onUndo={undo}
                onRedo={redo}
                hasChanges={modifiedRowIds.size}
                canUndo={undoStack.length > 0}
                canRedo={redoStack.length > 0}
            />
            {rowData.length > 0 && 
              <DashboardInfo 
                  fileName={selectedFile}
                  totalRows={rowData.length}
                  modifiedCount={modifiedRowIds.size}
                  missingCount={missingCount}
              />
            }
          </>
        )}

        <TranslationGrid
            loading={loading}
            rowData={rowData}
            colDefs={colDefs}
            onGridReady={onGridReady}
            onCellValueChanged={onCellValueChanged}
            darkMode={darkMode}
            selectedFile={selectedFile}
        />
      </div>
    </>
  );
};

export default App;
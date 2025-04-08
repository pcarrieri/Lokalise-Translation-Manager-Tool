import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { AgGridReact } from 'ag-grid-react';
import {
  ModuleRegistry,
  TextEditorModule,
  ClientSideRowModelModule,
  ValidationModule,
  TextFilterModule,
  NumberFilterModule,
  DateFilterModule,
  NumberEditorModule,
  provideGlobalGridOptions
} from 'ag-grid-community';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import './App.css';

provideGlobalGridOptions({ theme: "legacy" });

ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  ValidationModule,
  TextFilterModule,
  NumberFilterModule,
  DateFilterModule,
  TextEditorModule,
  NumberEditorModule 
]);

const App = () => {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [rowData, setRowData] = useState([]);
  const [originalData, setOriginalData] = useState([]);
  const [colDefs, setColDefs] = useState([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
  const [showOnlyChanges, setShowOnlyChanges] = useState(false);
  const [exporting, setExporting] = useState(false);

  const gridRef = useRef(null);

  const backendURL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5050';

  useEffect(() => {
    axios.get(`${backendURL}/files`).then(res => setFiles(res.data));
  }, []);

  useEffect(() => {
    if (selectedFile) {
      setLoading(true);
      axios.get(`${backendURL}/files/${selectedFile}`).then(res => {
        const data = Array.isArray(res.data) ? res.data : [];
        setRowData(data);
        setOriginalData(JSON.stringify(data));
        setHasChanges(false);
        if (data.length > 0) {
          const columns = Object.keys(data[0]).map(key => ({
            field: key,
            headerName: key.toUpperCase(),
            editable: true,
            sortable: true,
            filter: true,
            resizable: true,
          }));
          setColDefs(columns);
        }
        setLoading(false);
      });
    }
  }, [selectedFile]);

  useEffect(() => {
    const html = document.documentElement;
    if (darkMode) {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  useEffect(() => {
    const handleResize = () => {
      if (gridRef.current) {
        gridRef.current.sizeColumnsToFit();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const saveChanges = () => {
    axios.post(`${backendURL}/files/${selectedFile}`, rowData).then(() => {
      alert('✅ File salvato con successo');
      setOriginalData(JSON.stringify(rowData));
      setHasChanges(false);
    });
  };

  const exportCSV = () => {
    setExporting(true);
    // TODO: implementazione reale
    setTimeout(() => {
      alert('📤 CSV esportato!');
      setExporting(false);
    }, 800);
  };

  const resetFile = () => {
    if (confirm('Sei sicuro di voler annullare tutte le modifiche?')) {
      const data = JSON.parse(originalData);
      setRowData(data);
      setHasChanges(false);
    }
  };

  const handleChange = (params) => {
    const updated = [...rowData];
    updated[params.node.rowIndex] = params.data;
    setRowData(updated);
    if (JSON.stringify(updated) !== originalData) {
      setHasChanges(true);
    }
  };

  const getModifiedRows = () => {
    const original = JSON.parse(originalData);
    return rowData.filter((row, idx) => {
      const originalRow = original[idx];
      return Object.keys(row).some(key => row[key] !== originalRow[key]);
    });
  };

  return (
    <div className="page-container">
      <header className="toolbar">
        <h1 className="toolbar-title">Lokalise Translation Manager Tool Report</h1>
        <div className="toolbar-buttons">
          <div className="toolbar-button">
            <label className="label">Tema</label>
            <label className="switch">
              <input
                type="checkbox"
                checked={darkMode}
                onChange={() => setDarkMode(prev => !prev)}
              />
              <span className="slider" />
            </label>
          </div>
          <div className="toolbar-button">
            <label className="label">Esporta</label>
            <button className="action-button" onClick={exportCSV} disabled={exporting}>
              📤
            </button>
          </div>
          <div className="toolbar-button">
            <label className="label">Ripristina</label>
            <button className="action-button" onClick={resetFile} disabled={!hasChanges}>
              🔁
            </button>
          </div>
          <div className="toolbar-stats">
            <span>📄 {rowData.length} righe</span>
            {hasChanges && (
              <span className="text-yellow-500 ml-2">✏️ {getModifiedRows().length} modificate</span>
            )}
          </div>
        </div>
      </header>

      <div className="file-selector">
        <label>Scegli un file:</label>
        <select
          className="p-2 border rounded"
          onChange={(e) => setSelectedFile(e.target.value)}
          defaultValue=""
        >
          <option disabled value="">-- seleziona --</option>
          {files.map(file => (
            <option key={file} value={file}>{file}</option>
          ))}
        </select>

        {selectedFile && hasChanges && (
          <button
            className="ml-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
            onClick={saveChanges}
          >
            💾 Salva modifiche
          </button>
        )}
      </div>

      {selectedFile && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <label>
            <input
              type="checkbox"
              checked={showOnlyChanges}
              onChange={() => setShowOnlyChanges(prev => !prev)}
            />
            <span className="ml-1">Mostra solo righe modificate</span>
          </label>
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-500 mt-8">⏳ Caricamento dati in corso...</div>
      ) : (
        rowData.length > 0 ? (
          <div className="grid-wrapper">
            <div
              className="ag-theme-alpine ag-grid-custom"
              style={{
                height: '600px',
                width: '100%',
              }}
            >
              <AgGridReact
                ref={gridRef}
                rowData={showOnlyChanges ? getModifiedRows() : rowData}
                columnDefs={colDefs}
                defaultColDef={{
                  minWidth: 100,
                  editable: true,
                  sortable: true,
                  filter: true,
                  resizable: true,
                  cellClassRules: {
                    'cell-modified': (params) => {
                      const originalRow = JSON.parse(originalData)[params.node.rowIndex];
                      return originalRow?.[params.colDef.field] !== params.value;
                    }
                  }
                }}
                onCellValueChanged={handleChange}
                domLayout="normal"
                onGridReady={(params) => {
                  gridRef.current = params.api;
                  params.api.sizeColumnsToFit();
                }}
              />
            </div>
          </div>
        ) : (
          selectedFile && <div className="text-gray-500 mt-6">⚠️ Nessun dato da mostrare</div>
        )
      )}
    </div>
  );
};

export default App;

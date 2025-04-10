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
  const [showTools, setShowTools] = useState(false);

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
      alert('✅ File successfully saved');
      setOriginalData(JSON.stringify(rowData));
      setHasChanges(false);
    });
  };

  const exportCSV = () => {
    setExporting(true);
    setTimeout(() => {
      alert('📤 CSV exported!');
      setExporting(false);
    }, 800);
  };

  const resetFile = () => {
    if (confirm('Are you sure you want to undo all changes?')) {
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

  const specialFiles = [
    'final_report.csv',
    'ready_to_be_deleted.csv',
    'translation_done.csv',
    'missing_translations.csv'
  ];

  return (
    <>
      <div className="page-container">
        <h1 className="toolbar-title">Lokalise Translation Manager Tool Report</h1>

        <div className="file-navbar mb-0">
          <div className="file-tabs">
            {files.includes('final_report.csv') && (
              <button className={`file-tab ${selectedFile === 'final_report.csv' ? 'active' : ''}`} onClick={() => setSelectedFile('final_report.csv')}>Final Report</button>
            )}
            {files.includes('ready_to_be_deleted.csv') && (
              <button className={`file-tab ${selectedFile === 'ready_to_be_deleted.csv' ? 'active' : ''}`} onClick={() => setSelectedFile('ready_to_be_deleted.csv')}>Keys ready to be deleted</button>
            )}
            {files.includes('translation_done.csv') && (
              <button className={`file-tab ${selectedFile === 'translation_done.csv' ? 'active' : ''}`} onClick={() => setSelectedFile('translation_done.csv')}>Complete translation list</button>
            )}
            {files.includes('missing_translations.csv') && (
              <button className={`file-tab ${selectedFile === 'missing_translations.csv' ? 'active' : ''}`} onClick={() => setSelectedFile('missing_translations.csv')}>Missing translations</button>
            )}
            {files.filter(f => !specialFiles.includes(f)).length > 0 && (
              <select
                className="file-dropdown"
                onChange={(e) => setSelectedFile(e.target.value)}
                value={specialFiles.includes(selectedFile) ? '' : selectedFile}
              >
                <option value="">Other files</option>
                {files.filter(f => !specialFiles.includes(f)).map(file => (
                  <option key={file} value={file}>{file}</option>
                ))}
              </select>
            )}
          </div>

          <div className="tools-wrapper relative">
            <button className="tools-tab" onClick={() => setShowTools(prev => !prev)}>⚙️ Tools</button>
            {showTools && (
              <div className="tools-menu absolute right-0 mt-2 rounded-xl shadow-lg min-w-[250px] z-30 transition-all duration-200 ease-out transform scale-100 opacity-100 pointer-events-auto">
                <div className="p-4 flex flex-col gap-4">
                  <div className="flex justify-between items-center">
                    <span className="label">Export</span>
                    <button className="action-button" onClick={exportCSV} disabled={exporting}>📤</button>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="label">Reset</span>
                    <button className="action-button" onClick={resetFile} disabled={!hasChanges}>🔁</button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {selectedFile && hasChanges && (
            <button className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition" onClick={saveChanges}>💾 Save changes</button>
          )}
        </div>

        {selectedFile && (
          <div className="-mt-4 flex items-center justify-center gap-8 text-sm flex-wrap md:flex-nowrap">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={showOnlyChanges}
                onChange={() => setShowOnlyChanges(prev => !prev)}
              />
              <span>Show only modified rows</span>
            </label>

            <div className="flex items-center gap-2">
              <span>📄 {rowData.length} rows</span>
              {hasChanges && (
                <span className="text-yellow-500">✏️ {getModifiedRows().length} modified</span>
              )}
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center text-gray-500 mt-8">⏳ Loading data...</div>
        ) : (
          rowData.length > 0 ? (
            <div className="grid-wrapper">
              <div
                className="ag-theme-alpine ag-grid-custom"
                style={{ height: '600px', width: '100%' }}
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
            selectedFile && <div className="text-gray-500 mt-6">⚠️ No data to display</div>
          )
        )}
      </div>

      {/* ✅ Dark mode switch bottom-right with label */}
      <div style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', zIndex: 9999 }}>
        <div className="flex flex-col items-center gap-1">
          <span className="text-xs text-gray-500 dark:text-gray-300 font-medium">Dark mode  </span>
          <label className="switch">
            <input
              type="checkbox"
              checked={darkMode}
              onChange={() => setDarkMode(prev => !prev)}
            />
            <span className="slider" />
          </label>
        </div>
      </div>
    </>
  );
};

export default App;
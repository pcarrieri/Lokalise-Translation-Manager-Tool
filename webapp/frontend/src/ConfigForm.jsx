// src/ConfigForm.jsx
import React, { useState } from 'react';

const ConfigForm = ({ onSave }) => {
  const [config, setConfig] = useState({
    lokalise: { project_id: '', api_key: '' },
    openai: { api_key: '' },
    project_paths: { ios: '', android: '' },
  });

  const handleChange = (section, key, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: { ...prev[section], [key]: value },
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(config);
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
      <h2 className="text-2xl font-bold text-center mb-2 text-gray-800 dark:text-white">Setup Iniziale</h2>
      <p className="text-center text-gray-500 dark:text-gray-400 mb-6">
        Inserisci i dati di configurazione per continuare.
      </p>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold mb-2 border-b pb-1 border-gray-200 dark:border-gray-700">Lokalise</h3>
          <input type="text" placeholder="Lokalise Project ID" required className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" onChange={e => handleChange('lokalise', 'project_id', e.target.value)} />
          <input type="password" placeholder="Lokalise API Key" required className="w-full p-2 border rounded mt-2 dark:bg-gray-700 dark:border-gray-600" onChange={e => handleChange('lokalise', 'api_key', e.target.value)} />
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2 border-b pb-1 border-gray-200 dark:border-gray-700">OpenAI</h3>
          <input type="password" placeholder="OpenAI API Key" required className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" onChange={e => handleChange('openai', 'api_key', e.target.value)} />
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2 border-b pb-1 border-gray-200 dark:border-gray-700">Percorsi Progetti</h3>
          <input type="text" placeholder="Percorso completo cartella progetto iOS" required className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" onChange={e => handleChange('project_paths', 'ios', e.target.value)} />
          <input type="text" placeholder="Percorso completo cartella progetto Android" required className="w-full p-2 border rounded mt-2 dark:bg-gray-700 dark:border-gray-600" onChange={e => handleChange('project_paths', 'android', e.target.value)} />
        </div>
        <button type="submit" className="w-full px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 transition-transform transform hover:scale-105 active:scale-95">
          Salva e Avvia Processo
        </button>
      </form>
    </div>
  );
};

export default ConfigForm;
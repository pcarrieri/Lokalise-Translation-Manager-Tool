// src/ConfigEditor.jsx
import React from 'react';

const ConfigEditor = ({ config, setConfig, onStart, onSave }) => {
  // Funzione per verificare se la configurazione essenziale è completa
  const isConfigComplete = () => {
    return (
      config.lokalise?.project_id &&
      config.lokalise?.api_key &&
      config.openai?.api_key &&
      config.project_paths?.ios &&
      config.project_paths?.android
    );
  };

  const handlePathChange = (platform, value) => {
    setConfig(prevConfig => ({
      ...prevConfig,
      project_paths: {
        ...prevConfig.project_paths,
        [platform]: value,
      },
    }));
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 mb-8">
      <h2 className="text-2xl font-bold text-center mb-6 text-gray-800 dark:text-white">
        Configurazione
      </h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
            Percorso Progetto iOS
          </label>
          <input
            type="text"
            value={config.project_paths?.ios || ''}
            onChange={(e) => handlePathChange('ios', e.target.value)}
            placeholder="/Users/your_name/projects/my_ios_app"
            className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">
            Percorso Progetto Android
          </label>
          <input
            type="text"
            value={config.project_paths?.android || ''}
            onChange={(e) => handlePathChange('android', e.target.value)}
            placeholder="C:\Users\your_name\projects\my_android_app"
            className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
          />
        </div>
      </div>
      <div className="flex items-center justify-center space-x-4 mt-8">
        <button
          onClick={onSave}
          className="px-6 py-2 bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-100 font-semibold rounded-lg hover:bg-gray-300 transition"
        >
          Salva Percorsi
        </button>
        <button
          onClick={onStart}
          disabled={!isConfigComplete()}
          className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
        >
          Avvia Processo
        </button>
      </div>
       {!isConfigComplete() && (
          <p className="text-center text-xs text-red-500 mt-4">
            Il pulsante 'Avvia Processo' si abiliterà quando tutti i campi di configurazione saranno stati inseriti (anche quelli del primo setup).
          </p>
       )}
    </div>
  );
};

export default ConfigEditor;
// src/CleanupModal.jsx
import React from 'react';

const CleanupModal = ({ isOpen, keys, onConfirm, onCancel }) => {
  if (!isOpen) {
    return null;
  }

  const handleConfirm = () => {
    // Aggiungiamo una seconda conferma nativa del browser per la massima sicurezza
    if (window.confirm(`Sei assolutamente sicuro di voler cancellare permanentemente ${keys.length} chiavi da Lokalise? Questa azione non è reversibile.`)) {
      onConfirm();
    }
  };

  return (
    // Sfondo semi-trasparente
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">
      {/* Contenitore della modale */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8 max-w-lg w-full">
        <h2 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-4">
          ⚠️ Conferma Cancellazione Chiavi
        </h2>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Sono state trovate <strong className="font-bold">{keys.length}</strong> chiavi inutilizzate. Sei sicuro di volerle cancellare permanentemente da Lokalise?
        </p>
        
        {/* Elenco scrollabile delle chiavi */}
        <div className="h-48 overflow-y-auto border dark:border-gray-600 rounded-md p-3 bg-gray-50 dark:bg-gray-700 mb-6">
          <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-200">
            {keys.map(key => (
              <li key={key.key_id} className="truncate">
                {key.key_name}
              </li>
            ))}
          </ul>
        </div>

        {/* Pulsanti di azione */}
        <div className="flex justify-end space-x-4">
          <button 
            onClick={onCancel} 
            className="px-6 py-2 bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-100 font-semibold rounded-lg hover:bg-gray-300 transition"
          >
            Salta
          </button>
          <button 
            onClick={handleConfirm}
            className="px-6 py-2 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition"
          >
            Sì, Cancella le Chiavi
          </button>
        </div>
      </div>
    </div>
  );
};

export default CleanupModal;
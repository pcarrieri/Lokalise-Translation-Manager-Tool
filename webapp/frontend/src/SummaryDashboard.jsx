// src/SummaryDashboard.jsx
import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels'; // <-- IMPORTA IL PLUGIN

// Registra tutti i componenti necessari, incluso il nuovo plugin
ChartJS.register( CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ChartDataLabels );

const SummaryCard = ({ summary, darkMode }) => {
  const textColor = darkMode ? '#e9ecef' : '#212529';

  const data = {
    labels: summary.data.labels,
    datasets: [
      {
        label: 'Conteggio',
        data: summary.data.values,
        backgroundColor: [
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 99, 132, 0.7)',
          'rgba(75, 192, 192, 0.7)',
          'rgba(255, 206, 86, 0.7)',
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 99, 132, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(255, 206, 86, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  const options = {
    indexAxis: 'y', // <-- Rende il grafico orizzontale per una migliore leggibilità
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: summary.title,
        font: { size: 18, weight: 'bold' },
        color: textColor,
        padding: { bottom: 20 }
      },
      // --- NUOVA CONFIGURAZIONE PER LE ETICHETTE ---
      datalabels: {
        anchor: 'end',
        align: 'end',
        color: textColor,
        font: {
          weight: 'bold',
        },
        formatter: (value) => {
          // Non mostrare lo zero
          return value > 0 ? value : '';
        }
      }
    },
    scales: {
        x: {
            ticks: { color: textColor, stepSize: 1 }
        },
        y: {
            ticks: { color: textColor }
        }
    }
  };

  return (
    <div className="summary-card">
      <Bar data={data} options={options} />
    </div>
  );
};

const SummaryDashboard = ({ summaries, darkMode }) => {
  if (!summaries || summaries.length === 0) {
    return null;
  }

  return (
    <div className="summary-dashboard">
      <h2 className="text-2xl font-bold mb-4 text-center">Riepiloghi di Esecuzione</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {summaries.map((summary, index) => (
          <SummaryCard key={index} summary={summary} darkMode={darkMode} />
        ))}
      </div>
    </div>
  );
};

export default SummaryDashboard;
import React from "react";
/*
  We show a mocked Chart using react-chartjs-2 + chart.js.
  Install on frontend: npm install chart.js react-chartjs-2
*/
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

export default function Dashboard() {
  const data = {
    labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    datasets: [
      {
        label: "Mood",
        data: [5, 6, 6, 7, 6, 8, 7],
        fill: false,
        tension: 0.3,
      }
    ]
  };

  const options = {
    responsive: true,
    plugins: {
      title: {
        display: true,
        text: "Your Mood Over Time"
      },
      legend: {
        display: false
      }
    },
    scales: {
      y: {
        suggestedMin: 0,
        suggestedMax: 10
      }
    }
  };

  return (
    <div className="dashboard">
      <h2>Insights</h2>

      <div className="card">
        <Line data={data} options={options} />
      </div>

      <div className="card wellness-pathway">
        <h3>Personalized Wellness Pathway</h3>
        <p>Try one of these quick exercises:</p>
        <div className="pathway-buttons">
          <button className="path-btn">5-Minute Mindfulness</button>
          <button className="path-btn">Deep Breathing Exercise</button>
          <button className="path-btn">Reframing Your Thoughts</button>
        </div>
      </div>
    </div>
  );
}

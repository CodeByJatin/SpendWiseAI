import { useState, useRef } from 'react';
import { UploadCloud, Activity, LayoutDashboard, ShieldCheck } from 'lucide-react';
import SidebarChat from './components/SidebarChat';
import TransactionList from './components/TransactionList';
import SpendingChart from './components/SpendingChart';
import './App.css';

function App() {
  const [transactions, setTransactions] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      // 1. Upload file to ML Engine
      const uploadRes = await fetch('http://127.0.0.1:8000/api/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!uploadRes.ok) throw new Error('Upload failed');

      // 2. Fetch processed transactions
      const txRes = await fetch('http://127.0.0.1:8000/api/transactions');
      if (!txRes.ok) throw new Error('Failed to fetch transactions');
      
      const data = await txRes.json();
      setTransactions(data.transactions);
      setAnomalies(data.anomalies);
      
    } catch (err) {
      console.error(err);
      alert('Error connecting to backend API. Is FastAPI running?');
    } finally {
      setIsUploading(false);
      // Reset input so the same file can be uploaded again if needed
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const totalSpent = transactions
    .reduce((sum, t) => sum + Number(t.amount || 0), 0);

  return (
    <div className="app-container">
      <main className="main-content">
        
        {/* Header Area */}
        <header className="top-bar">
          <div className="brand animate-fade-in">
            <h1><Activity className="accent-icon" /> SpendWise AI</h1>
            <p>100% Local, Privacy-First Financial Intelligence</p>
          </div>

          <div className="upload-section animate-fade-in">
            {anomalies.length === 0 && transactions.length > 0 && (
              <div style={{ color: 'var(--success-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginRight: '1rem' }}>
                <ShieldCheck size={18} /> Clean Statement
              </div>
            )}
            <input 
              type="file" 
              accept=".csv" 
              className="upload-input" 
              id="csvUpload" 
              ref={fileInputRef}
              onChange={handleFileUpload}
            />
            <label htmlFor="csvUpload" className="btn">
              <UploadCloud size={18} />
              {isUploading ? 'Analyzing via ML...' : 'Upload Bank Statement (CSV)'}
            </label>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="dashboard-grid animate-fade-in">
          {/* Left Column: Metrics & Charts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Top Metric Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              <div className="glass-panel" style={{ padding: '1.5rem' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>Total Spent (This Period)</p>
                <h2 style={{ fontSize: '2rem' }}>${totalSpent.toFixed(2)}</h2>
              </div>
              <div className="glass-panel" style={{ padding: '1.5rem' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>Anomalies Detected</p>
                <h2 style={{ fontSize: '2rem', color: anomalies.length > 0 ? '#fca5a5' : 'var(--success-color)' }}>
                  {anomalies.length}
                </h2>
              </div>
            </div>

            {/* Spending Chart */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <SpendingChart transactions={transactions} />
            </div>

          </div>

          {/* Right Column: Transaction Feed */}
          <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <TransactionList transactions={transactions} />
          </div>
        </div>
      </main>

      {/* Persistent AI Chat Sidebar */}
      <aside style={{ width: '400px', flexShrink: 0 }}>
        <SidebarChat anomalies={anomalies} />
      </aside>
    </div>
  );
}

export default App;

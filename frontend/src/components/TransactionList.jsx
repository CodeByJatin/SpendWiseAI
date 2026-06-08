import { AlertTriangle, TrendingDown, TrendingUp, CreditCard } from 'lucide-react';
import './TransactionList.css';

export default function TransactionList({ transactions }) {
  if (!transactions || transactions.length === 0) {
    return (
      <div className="empty-state">
        <CreditCard size={48} className="empty-icon" />
        <p>No transactions loaded.</p>
        <p className="sub-text">Upload a bank statement to begin.</p>
      </div>
    );
  }

  return (
    <div className="transaction-list">
      <div className="list-header">
        <h3>Recent Transactions</h3>
        <span className="badge">{transactions.length} items</span>
      </div>
      
      <div className="transactions-container">
        {transactions.map((txn, idx) => (
          <div key={idx} className={`transaction-item ${txn.is_anomaly ? 'anomaly-row' : ''}`}>
            <div className="txn-icon">
              {txn.amount > 0 ? <TrendingDown size={20} className="expense" /> : <TrendingUp size={20} className="income" />}
            </div>
            
            <div className="txn-details">
              <h4>{txn.description}</h4>
              <span className="txn-meta">
                {txn.date} • <span className="category-tag">{txn.predicted_category || txn.category}</span>
              </span>
            </div>

            <div className="txn-amount">
              <h4>${Math.abs(txn.amount).toFixed(2)}</h4>
              {txn.is_anomaly && (
                <div className="anomaly-badge" title={`Anomaly Score: ${txn.anomaly_score?.toFixed(2)}`}>
                  <AlertTriangle size={14} /> Suspicious
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

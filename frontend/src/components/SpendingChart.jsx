import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

export default function SpendingChart({ transactions }) {
  if (!transactions || transactions.length === 0) {
    return null;
  }

  // Aggregate spending by category
  const categoryTotals = {};
  transactions.forEach(txn => {
    const category = txn.predicted_category || txn.category || 'Other';
    categoryTotals[category] = (categoryTotals[category] || 0) + Number(txn.amount || 0);
  });

  const data = Object.keys(categoryTotals).map(key => ({
    name: key,
    value: categoryTotals[key]
  })).sort((a, b) => b.value - a.value);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(25, 25, 35, 0.9)',
          border: '1px solid rgba(255,255,255,0.1)',
          padding: '10px 15px',
          borderRadius: '8px',
          color: '#fff',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}>
          <p style={{ margin: 0, fontWeight: 500 }}>{payload[0].name}</p>
          <p style={{ margin: '5px 0 0 0', color: payload[0].payload.fill }}>
            ${payload[0].value.toFixed(2)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container" style={{ width: '100%', height: '300px', display: 'flex', flexDirection: 'column' }}>
      <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Spending by Category</h3>
      <div style={{ flex: 1, width: '100%', minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle"
              wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

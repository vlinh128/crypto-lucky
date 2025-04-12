import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL = 'http://localhost:8888';

// Token definitions
const TOKENS = {
  BTC: { name: 'Bitcoin', symbol: 'BTC', decimals: 8 },
  ETH: { name: 'Ethereum', symbol: 'ETH', decimals: 18 },
  DOGE: { name: 'Dogecoin', symbol: 'DOGE', decimals: 8 }
};

function App() {
  // Stats state for each token type
  const [stats, setStats] = useState({
    BTC: { total_wallets: 0, total_balance: 0 },
    ETH: { total_wallets: 0, total_balance: 0 },
    DOGE: { total_wallets: 0, total_balance: 0 }
  });
  
  // State for wallet list (all token types)
  const [wallets, setWallets] = useState([]);
  
  const [error, setError] = useState(null);
  const initialDataLoaded = useRef(false);

  // Fetch data from API
  const fetchData = async () => {
    try {
      const [statsResponse, walletsResponse] = await Promise.all([
        fetch(`${API_URL}/api/stats`),
        fetch(`${API_URL}/api/wallets`)
      ]);

      const statsJson = await statsResponse.json();
      const walletsJson = await walletsResponse.json();

      if (statsJson.data) {
        // Update stats for each token type
        const newStats = { ...stats };
        Object.entries(statsJson.data).forEach(([coinType, data]) => {
          newStats[coinType] = {
            total_wallets: data.total_wallets || 0,
            total_balance: data.total_balance || 0
          };
        });
        setStats(newStats);
      }

      if (walletsJson.success && walletsJson.data && walletsJson.data.wallets) {
        // Save all wallets to array
        setWallets(walletsJson.data.wallets);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Failed to load data');
    }
  };

  // Initial data fetch
  useEffect(() => {
    if (!initialDataLoaded.current) {
      fetchData();
      initialDataLoaded.current = true;
    }
  }, []);

  // Polling every 5 seconds
  useEffect(() => {
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Component to display stats for a token type
  const TokenStats = ({ coinType }) => {
    const tokenInfo = TOKENS[coinType];
    const tokenStats = stats[coinType];
    
    return (
      <div className="col-md-4 mb-4">
        <div className="card stats-card">
          <div className="card-header">
            <h5 className="card-title mb-0">{tokenInfo.name} ({tokenInfo.symbol})</h5>
          </div>
          <div className="card-body">
            <div className="stats-row">
              <div className="stats-label">Total Wallets</div>
              <div className="stats-value">{tokenStats.total_wallets}</div>
            </div>
            <div className="stats-row">
              <div className="stats-label">Total Balance</div>
              <div className="stats-value">{Number(tokenStats.total_balance).toFixed(2)} {tokenInfo.symbol}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="container-fluid">
      <h1 className="mb-4">Crypto Finder Dashboard</h1>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}
      
      {/* Stats for all token types */}
      <div className="row g-4 mb-4">
        {Object.keys(TOKENS).map(coinType => (
          <TokenStats key={coinType} coinType={coinType} />
        ))}
      </div>

      {/* Combined table for all wallets */}
      <div className="card">
        <div className="card-header">
          <h5 className="card-title mb-0">Found Wallets</h5>
        </div>
        <div className="card-body">
          <div className="table-container">
            <table className="table table-striped table-hover">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Address</th>
                  <th>Balance</th>
                  <th>Strategy</th>
                  <th>API Source</th>
                  <th>Check Time</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map((wallet) => {
                  // Default to BTC if coin_type is not available
                  const tokenInfo = TOKENS[wallet.coin_type] || { symbol: wallet.coin_type, decimals: 8 };
                  return (
                    <tr key={wallet.address}>
                      <td>
                        <span className={`token-badge ${wallet.coin_type.toLowerCase()}`}>
                          {tokenInfo.symbol}
                        </span>
                      </td>
                      <td className="address-column text-monospace">{wallet.address}</td>
                      <td className="balance-column text-monospace">
                        {Number(wallet.balance).toFixed(2)} {tokenInfo.symbol}
                      </td>
                      <td className="strategy-column">{wallet.strategy}</td>
                      <td className="api-source-column">{wallet.api_source}</td>
                      <td className="timestamp-column">
                        {new Date(wallet.created_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
                {wallets.length === 0 && (
                  <tr>
                    <td colSpan="6" className="text-center">No wallets found yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 
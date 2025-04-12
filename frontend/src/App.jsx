import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL =  'http://localhost:8888';

function App() {
  const [stats, setStats] = useState({
    total_wallets: 0,
    total_balance: 0,
    max_balance: 0,
    min_balance: 0,
    is_searching: false
  });
  const [wallets, setWallets] = useState([]);
  const [error, setError] = useState(null);
  const initialDataLoaded = useRef(false);

  useEffect(() => {
    if (!initialDataLoaded.current) {
      fetchInitialData();
      initialDataLoaded.current = true;
    }
  }, []);

  const fetchInitialData = async () => {
    try {
      const [statsResponse, walletsResponse] = await Promise.all([
        fetch('http://localhost:8888/api/stats'),
        fetch('http://localhost:8888/api/wallets')
      ]);

      const statsJson = await statsResponse.json();
      const walletsJson = await walletsResponse.json();

      if (statsJson.data) {
        setStats(prev => ({
          ...prev,
          total_wallets: statsJson.data.total_wallets || 0,
          total_balance: statsJson.data.total_balance || 0,
          max_balance: statsJson.data.max_balance || 0,
          min_balance: statsJson.data.min_balance || 0,
          is_searching: statsJson.data.is_searching || false
        }));
      }

      if (walletsJson.wallets) {
        setWallets(walletsJson.wallets);
      }
    } catch (error) {
      console.error('Error fetching initial data:', error);
      setError('Failed to load initial data');
    }
  };

  // Setup SSE connection for real-time updates
  useEffect(() => {
    let eventSource = null;
    let reconnectTimeout = null;
    
    const setupSSE = () => {
      console.log('Setting up SSE connection...');
      
      if (eventSource) {
        eventSource.close();
      }
      
      eventSource = new EventSource(`${API_URL}/api/stream`);

      // Handle wallet updates
      eventSource.addEventListener('wallet_found', (event) => {
        console.log('Received wallet_found event:', event.data);
        try {
          const newWallet = JSON.parse(event.data);
          setWallets(prevWallets => {
            const filteredWallets = prevWallets.filter(w => w.address !== newWallet.address);
            return [newWallet, ...filteredWallets];
          });
        } catch (error) {
          console.error('Error parsing wallet update:', error);
        }
      });

      // Handle stats updates
      eventSource.addEventListener('stats_update', (event) => {
        console.log('Received stats_update event:', event.data);
        try {
          const statsData = JSON.parse(event.data);
          setStats(prev => ({
            ...prev,
            total_wallets: statsData.total_wallets || prev.total_wallets,
            total_balance: statsData.total_balance || prev.total_balance,
            max_balance: statsData.max_balance || prev.max_balance,
            min_balance: statsData.min_balance || prev.min_balance,
            is_searching: statsData.is_searching !== undefined ? statsData.is_searching : prev.is_searching
          }));
        } catch (error) {
          console.error('Error parsing stats update:', error);
        }
      });

      // Handle search status updates
      eventSource.addEventListener('search_status', (event) => {
        console.log('Received search_status event:', event.data);
        try {
          const statusData = JSON.parse(event.data);
          setStats(prev => ({
            ...prev,
            is_searching: statusData.is_searching
          }));
        } catch (error) {
          console.error('Error parsing search status:', error);
        }
      });

      // Handle connection open/error
      eventSource.onopen = () => {
        console.log('SSE connection opened');
        setError(null);
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource.close();
        
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
        }
        
        reconnectTimeout = setTimeout(() => {
          setError('Lost connection to server. Reconnecting...');
          setupSSE();
        }, 5000);
      };
    };
    
    setupSSE();
    
    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);

  return (
    <div className="container-fluid">
      <h1 className="mb-4">Crypto Finder Dashboard</h1>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}
      <div className="row g-4 mb-4">
        <div className="col-md-6">
          <div className="card stats-card">
            <div className="card-body">
              <div className="stats-label">Tổng số ví</div>
              <div className="stats-value">{stats.total_wallets}</div>
            </div>
          </div>
        </div>
        <div className="col-md-6">
          <div className="card stats-card">
            <div className="card-body">
              <div className="stats-label">Tổng số dư</div>
              <div className="stats-value">{stats.total_balance.toFixed(8)} BTC</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <h5 className="card-title">Danh sách ví đã tìm thấy</h5>
          <div className="table-container">
            <table className="table table-striped table-hover">
              <thead>
                <tr>
                  <th>Địa chỉ</th>
                  <th>Số dư (BTC)</th>
                  <th>Chiến lược</th>
                  <th>API Source</th>
                  <th>Thời gian kiểm tra</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map((wallet) => (
                  <tr key={wallet.address}>
                    <td className="address-column text-monospace">{wallet.address}</td>
                    <td className="balance-column text-monospace">{wallet.balance.toFixed(8)}</td>
                    <td className="strategy-column">{wallet.strategy}</td>
                    <td className="api-source-column">{wallet.api_source}</td>
                    <td className="timestamp-column">
                      {new Date(wallet.created_at).toLocaleString('vi-VN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 
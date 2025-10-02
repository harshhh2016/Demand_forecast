import React, { useEffect, useState } from 'react';

export default function ReorderAlerts({ projectId }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError('');
        const resp = await fetch(`http://localhost:5002/api/inventory/alerts/${projectId}`);
        if (!resp.ok) throw new Error('Failed to fetch alerts');
        const data = await resp.json();
        if (!cancelled) setAlerts(data);
      } catch (e) {
        if (!cancelled) setError(String(e.message || e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [projectId]);

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-br from-red-50 to-white border border-red-200/60">
      <h4 className="text-lg font-bold text-red-700 mb-3">Critical Reorder Alerts</h4>
      {loading && <p className="text-sm text-gray-600">Loading...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && alerts.length === 0 && <p className="text-sm text-gray-600">No alerts currently.</p>}
      {alerts.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-red-800">
                <th className="py-2 pr-4">Material</th>
                <th className="py-2 pr-4">Current Qty (MT)</th>
                <th className="py-2 pr-4">Reorder Point (MT)</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a, idx) => (
                <tr key={idx} className="bg-red-100/60">
                  <td className="py-2 pr-4 font-semibold">{a.material_name}</td>
                  <td className="py-2 pr-4">{Math.ceil(a.current_quantity_mt)}</td>
                  <td className="py-2 pr-4 font-semibold text-red-700">{Math.ceil(a.reorder_point)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

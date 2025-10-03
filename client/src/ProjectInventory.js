import React, { useState, useEffect, useCallback } from 'react';
import ReorderAlerts from './ReorderAlerts';

const ProjectInventory = ({ project, userData, goBack }) => {
  // Removed unused inventoryData to resolve lint warning
  const [materials, setMaterials] = useState([]);
  const [projectUsage, setProjectUsage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [showAlerts, setShowAlerts] = useState(false);
  const [showUsageModal, setShowUsageModal] = useState(false);
  const [showDeliveryModal, setShowDeliveryModal] = useState(false);

  const loadProjectInventoryData = useCallback(async () => {
    try {
      const [materialsResponse, usageResponse] = await Promise.all([
        fetch(`http://127.0.0.1:5002/inventory/materials?project_id=${encodeURIComponent(project.id)}`),
        fetch(`http://127.0.0.1:5002/inventory/project-usage/${project.id}`)
      ]);

      if (materialsResponse.ok) {
        const materialsData = await materialsResponse.json();
        const normalized = Array.isArray(materialsData)
          ? materialsData.map(m => {
              const deliveryCount = Number(m?.delivery_count) || 0;
              const delivered = Number(m?.project_delivered) || 0;
              const used = Number(m?.project_used) || 0;
              const projectStock = delivered - used;
              return {
                ...m,
                current_stock: Number(m?.current_stock) || 0,
                delivery_count: deliveryCount,
                project_stock: projectStock
              };
            })
          : [];
        setMaterials(normalized);
      } else {
        setMaterials([]);
      }

      if (usageResponse.ok) {
        const usageData = await usageResponse.json();
        setProjectUsage(Array.isArray(usageData) ? usageData : []);
      } else {
        setProjectUsage([]);
      }
    } catch (error) {
      console.error('Error loading project inventory data:', error);
      setMaterials([]);
      setProjectUsage([]);
    } finally {
      setLoading(false);
    }
  }, [project.id]);

  useEffect(() => {
    loadProjectInventoryData();
  }, [loadProjectInventoryData]);

  const formatQuantity = (value) => {
    const num = Math.ceil(Number(value) || 0);
    return num.toLocaleString();
  };

  // First Stocking helpers
  const LEAD_DAYS = {
    Steel: 75,
    Conductor: 90,
    Transformers: 120,
    Earthwire: 60,
    Foundation: 45,
    Reactors: 120,
    Tower: 60
  };

  const MATERIAL_UNITS = {
    Steel: 'tons',
    Conductor: 'km',
    Transformers: 'units',
    Earthwire: 'km',
    Foundation: 'units',
    Reactors: 'units',
    Tower: 'units'
  };

  const getForecastByName = (name) => {
    switch (name) {
      case 'Steel': return project.steel_forecast;
      case 'Conductor': return project.conductor_forecast;
      case 'Transformers': return project.transformers_forecast;
      case 'Earthwire': return project.earthwire_forecast;
      case 'Foundation': return project.foundation_forecast;
      case 'Reactors': return project.reactors_forecast;
      case 'Tower': return project.tower_forecast;
      default: return 0;
    }
  };

  // planned duration state for first stocking (default 3 years = 1095 days)
  const [plannedDays, setPlannedDays] = useState(1095);

  const computeFirstStocking = (name) => {
    const totalForecast = Number(getForecastByName(name) || 0);
    if (!totalForecast || !plannedDays) return 0;
    const avgDaily = totalForecast / Number(plannedDays);
    const lead = LEAD_DAYS[name] || 0;
    const leadDemand = avgDaily * lead;
    const withBuffer = leadDemand * 1.10; // 10% safety buffer
    return Math.ceil(withBuffer);
  };

  // Removed currency formatting and any cost displays per requirement

  // Removed total cost calculations

  const getProjectMaterialUsage = (materialId) => {
    const material = materials.find(m => m.id === materialId);
    if (!material) return 0;
    return projectUsage
      .filter(usage => (usage.material_name === material.name) || (usage.material_id === materialId))
      .reduce((total, usage) => total + (usage.quantity_used ?? usage.quantity ?? 0), 0);
  };

  if (loading) {
    return (
      <main className="flex-1 p-8">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">Loading project inventory...</div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            onClick={goBack}
            className="mb-4 flex items-center gap-2 text-blue-600 hover:text-blue-800 transition-colors"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Projects
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            Inventory Management - {project.location}
          </h1>
          <p className="text-gray-600 mt-2">
            Project ID: {project.id} | Status: {project.status}
          </p>
        </div>
        {/* Alerts banner action */}
        <div className="ml-4">
          <button
            onClick={() => setShowAlerts(true)}
            className="px-4 py-2 rounded-xl bg-red-500 text-white font-semibold hover:bg-red-600 transition-colors flex items-center gap-2"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 18.5a6.5 6.5 0 110-13 6.5 6.5 0 010 13z" />
            </svg>
            View Alerts
          </button>
        </div>
      </div>

      {/* Inline Alerts panel (modal-style) */}
      {showAlerts && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="w-full max-w-3xl bg-white rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-900">Reorder Alerts</h3>
              <button
                onClick={() => setShowAlerts(false)}
                className="px-3 py-1.5 rounded-lg bg-gray-200 text-gray-800 hover:bg-gray-300"
              >
                Close
              </button>
            </div>
            <ReorderAlerts projectId={project.id} />
          </div>
        </div>
      )}

      {/* Project Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Removed project total cost card */}

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Materials Used</h3>
          <p className="text-3xl font-bold text-green-600">
            {new Set(projectUsage.map(u => u.material_id)).size}
          </p>
          <p className="text-sm text-gray-500 mt-1">Different material types</p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Usage Records</h3>
          <p className="text-3xl font-bold text-purple-600">{projectUsage.length}</p>
          <p className="text-sm text-gray-500 mt-1">Total usage entries</p>
        </div>
      </div>

      {/* Action Buttons + First Stocking beside */}
      <div className="flex flex-col lg:flex-row gap-4 mb-8">
        <div className="flex gap-4">
          <button
            onClick={() => setShowUsageModal(true)}
            className="px-6 py-3 bg-blue-500 text-white rounded-xl font-semibold hover:bg-blue-600 transition-colors flex items-center gap-2"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Log Material Usage
          </button>

          <button
            onClick={() => setShowDeliveryModal(true)}
            className="px-6 py-3 bg-green-500 text-white rounded-xl font-semibold hover:bg-green-600 transition-colors flex items-center gap-2"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2 2v-5m16 0h-3.5m-9 0h-3.5" />
            </svg>
            Log Material Delivery
          </button>
        </div>

        {/* First Stocking Suggestions (beside buttons) */}
        <div className="flex-1 bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">First Stocking Suggestions</h3>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-600">Planned Duration (days)</label>
              <input
                type="number"
                min="1"
                value={plannedDays}
                onChange={(e) => setPlannedDays(Number(e.target.value || 0))}
                className="w-28 p-2 border rounded-lg"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {['Steel','Conductor','Transformers','Earthwire','Foundation','Reactors','Tower'].map((name) => {
              const suggestion = computeFirstStocking(name);
              const unit = MATERIAL_UNITS[name] || '';
              return (
                <div key={name} className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-xs text-gray-600">{name} ({unit})</div>
                  <div className="text-base font-semibold text-gray-900">
                    {formatQuantity(suggestion)} {unit}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-gray-500 mt-2">
            Suggestion = ceil(average daily usage × lead days × 1.10 buffer).
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-6 py-3 font-medium transition-colors ${
            activeTab === 'overview'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Project Overview
        </button>
        <button
          onClick={() => setActiveTab('materials')}
          className={`px-6 py-3 font-medium transition-colors ${
            activeTab === 'materials'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Material Usage
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-6 py-3 font-medium transition-colors ${
            activeTab === 'history'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Usage History
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Project Forecasts */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">AI Demand Forecasts</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { name: 'Steel', value: project.steel_forecast, unit: 'tons' },
                { name: 'Conductor', value: project.conductor_forecast, unit: 'km' },
                { name: 'Transformers', value: project.transformers_forecast, unit: 'units' },
                { name: 'Earthwire', value: project.earthwire_forecast, unit: 'km' },
                { name: 'Foundation', value: project.foundation_forecast, unit: 'units' },
                { name: 'Reactors', value: project.reactors_forecast, unit: 'units' },
                { name: 'Tower', value: project.tower_forecast, unit: 'units' }
              ].map((forecast) => (
                <div key={forecast.name} className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600">{forecast.name}</div>
                  <div className="text-lg font-semibold text-gray-900">
                    {formatQuantity(forecast.value)} {forecast.unit}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Usage for this Project */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Recent Material Usage</h3>
            {projectUsage.length > 0 ? (
              <div className="space-y-3">
                {projectUsage.slice(0, 5).map((usage, index) => {
                  const material = materials.find(m => m.name === usage.material_name || m.id === usage.material_id);
                  return (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium text-gray-900">{usage.material_name || material?.name || 'Unknown Material'}</div>
                        <div className="text-sm text-gray-500">
                          {new Date(usage.usage_date).toLocaleDateString()} by {usage.logged_by}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-900">{formatQuantity(usage.quantity_used ?? usage.quantity)} {material?.unit || ''}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No material usage recorded for this project yet.</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'materials' && (
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Material Usage by Type</h3>
          <div className="space-y-4">
            {materials.map((material) => {
              const usedQuantity = getProjectMaterialUsage(material.id);
              const showStock = (material.delivery_count > 0);
              const projectStockDisplay = showStock ? `${formatQuantity(material.project_stock)} ${material.unit}` : '—';
              return (
                <div key={material.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium text-gray-900">{material.name}</div>
                    <div className="text-sm text-gray-500">
                      Current Stock: {projectStockDisplay}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-gray-900">
                      Used: {formatQuantity(usedQuantity)} {material.unit}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Complete Usage History</h3>
          {projectUsage.length > 0 ? (
            <div className="space-y-3">
              {projectUsage.map((usage, index) => {
                const material = materials.find(m => m.name === usage.material_name || m.id === usage.material_id);
                return (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900">{usage.material_name || material?.name || 'Unknown Material'}</div>
                      <div className="text-sm text-gray-500">
                        {new Date(usage.usage_date).toLocaleString()} by {usage.logged_by}
                      </div>
                      {usage.notes && (
                        <div className="text-sm text-gray-600 mt-1">Notes: {usage.notes}</div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-gray-900">{formatQuantity(usage.quantity_used ?? usage.quantity)} {material?.unit || ''}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No usage history available for this project.</p>
          )}
        </div>
      )}

      {/* Modals */}
      <MaterialUsageModal
        show={showUsageModal}
        onClose={() => setShowUsageModal(false)}
        materials={materials}
        userData={userData}
        project={project}
        onSuccess={() => {
          loadProjectInventoryData();
        }}
      />

      <MaterialDeliveryModal
        show={showDeliveryModal}
        onClose={() => setShowDeliveryModal(false)}
        materials={materials}
        userData={userData}
        project={project}
        onSuccess={() => {
          loadProjectInventoryData();
        }}
      />
    </main>
  );
};

// Material Usage Modal Component
const MaterialUsageModal = ({ show, onClose, materials, userData, project, onSuccess }) => {
  const [formData, setFormData] = useState({
    material_id: '',
    quantity: '',
    notes: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Debug logging
      console.log('Project ID:', project.id);
      console.log('User ID:', userData.id);
      console.log('Form data:', formData);
      console.log('Materials available:', materials.length);

      // Validate form data
      if (!formData.material_id || !formData.quantity) {
        alert('Please fill in all required fields. Make sure to select a material and enter a quantity.');
        return;
      }

      const requestBody = {
        material_id: parseInt(formData.material_id),
        quantity_used: parseFloat(formData.quantity),
        project_id: project.id,
        logged_by: userData.id,
        notes: formData.notes
      };
      
      console.log('Request body:', requestBody);

      const response = await fetch('http://127.0.0.1:5002/inventory/usage', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (response.ok) {
        const result = await response.json();
        console.log('Success response:', result);
        alert('Material usage logged successfully!');
        setFormData({ material_id: '', quantity: '', notes: '' });
        onClose();
        onSuccess();
      } else {
        const errorData = await response.json();
        console.log('Error response:', errorData);
        alert(`Error: ${errorData.error || 'Failed to log usage'}`);
      }
    } catch (error) {
      console.error('Error logging usage:', error);
      console.error('Error details:', error.message);
      alert(`Error logging usage: ${error.message}. Please try again.`);
    } finally {
      setLoading(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl p-8">
        <h3 className="text-2xl font-bold mb-6">Log Material Usage</h3>
        <p className="text-gray-600 mb-4">Project: {project.location}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Material</label>
            <select
              value={formData.material_id}
              onChange={(e) => setFormData({ ...formData, material_id: e.target.value })}
              className="w-full p-3 border rounded-xl"
              required
            >
              <option value="">Select Material</option>
              {materials.map((material) => (
                <option key={material.id} value={material.id}>
                  {material.name} (Current: {material.delivery_count > 0 ? material.project_stock : '—'} {material.unit})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quantity Used</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
              className="w-full p-3 border rounded-xl"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Notes (Optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full p-3 border rounded-xl"
              rows="3"
              placeholder="Additional notes about usage..."
            />
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-500 text-white py-3 rounded-xl font-semibold hover:bg-blue-600 transition-colors disabled:opacity-50"
            >
              {loading ? 'Logging...' : 'Log Usage'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-xl font-semibold hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Material Delivery Modal Component
const MaterialDeliveryModal = ({ show, onClose, materials, userData, project, onSuccess }) => {
  const [formData, setFormData] = useState({
    material_id: '',
    quantity: '',
    notes: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (!formData.material_id || !formData.quantity) {
        alert('Please fill in all required fields');
        return;
      }

      const response = await fetch('http://127.0.0.1:5002/inventory/delivery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          material_id: parseInt(formData.material_id),
          quantity_delivered: parseFloat(formData.quantity),
          received_by: userData.id,
          project_id: project.id,
          purchase_order_number: '',
          invoice_number: '',
          notes: formData.notes
        }),
      });

      if (response.ok) {
        alert('Material delivery logged successfully!');
        setFormData({ material_id: '', quantity: '', notes: '' });
        onClose();
        onSuccess();
      } else {
        const errorData = await response.json();
        alert(`Error: ${errorData.error || 'Failed to log delivery'}`);
      }
    } catch (error) {
      console.error('Error logging delivery:', error);
      alert('Error logging delivery. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl p-8">
        <h3 className="text-2xl font-bold mb-6">Log Material Delivery</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Material</label>
            <select
              value={formData.material_id}
              onChange={(e) => setFormData({ ...formData, material_id: e.target.value })}
              className="w-full p-3 border rounded-xl"
              required
            >
              <option value="">Select Material</option>
              {materials.map((material) => (
                <option key={material.id} value={material.id}>
                  {material.name} (Current: {material.delivery_count > 0 ? material.project_stock : '—'} {material.unit})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quantity Delivered</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
              className="w-full p-3 border rounded-xl"
              required
            />
          </div>

          {/* Removed supplier field */}

          {/* Removed cost per unit field */}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Notes (Optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full p-3 border rounded-xl"
              rows="3"
              placeholder="Additional notes about delivery..."
            />
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-green-500 text-white py-3 rounded-xl font-semibold hover:bg-green-600 transition-colors disabled:opacity-50"
            >
              {loading ? 'Logging...' : 'Log Delivery'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-xl font-semibold hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectInventory;

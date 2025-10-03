import React, { useState, useEffect, useCallback } from 'react';

const AdminDashboard = ({ userData }) => {
  const [pendingProjects, setPendingProjects] = useState([]);
  const [allProjects, setAllProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [approvalNotes, setApprovalNotes] = useState({});
  const [currentView, setCurrentView] = useState('all'); // 'pending', 'approved', 'rejected', or 'all'

  const loadPendingProjects = useCallback(async () => {
    if (!userData?.state) return;
    
    try {
      setLoading(true);
      const response = await fetch(`http://127.0.0.1:5002/projects/pending/${userData.state}`);
      const data = await response.json();
      
      if (response.ok) {
        setPendingProjects(data.projects || []);
      } else {
        console.error('Failed to load pending projects:', data.error);
      }
    } catch (error) {
      console.error('Error loading pending projects:', error);
    } finally {
      setLoading(false);
    }
  }, [userData?.state]);

  const loadAllProjects = useCallback(async () => {
    if (!userData?.state) return;
    
    try {
      setLoading(true);
      const response = await fetch(`http://127.0.0.1:5002/projects/all/${userData.state}`);
      const data = await response.json();
      
      if (response.ok) {
        setAllProjects(data.projects || []);
      } else {
        console.error('Failed to load all projects:', data.error);
      }
    } catch (error) {
      console.error('Error loading all projects:', error);
    } finally {
      setLoading(false);
    }
  }, [userData?.state]);

  // Load all projects for this admin's state on initial load
  useEffect(() => {
    if (userData && userData.state) {
      loadAllProjects();
    }
  }, [userData, loadAllProjects]);

  // Helper functions to get filtered projects
  const getApprovedProjects = () => allProjects.filter(p => p.status === 'approved');
  const getRejectedProjects = () => allProjects.filter(p => p.status === 'rejected');
  const getCurrentProjects = () => {
    switch (currentView) {
      case 'pending': return pendingProjects;
      case 'approved': return getApprovedProjects();
      case 'rejected': return getRejectedProjects();
      case 'all': return allProjects;
      default: return [];
    }
  };

  const handleApproval = async (projectId, action) => {
    try {
      const notes = approvalNotes[projectId] || '';
      const endpoint = action === 'approve' ? 'approve' : 'reject';
      
      const response = await fetch(`http://127.0.0.1:5002/projects/${projectId}/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          admin_user_id: userData.id,
          [action === 'approve' ? 'approval_notes' : 'rejection_notes']: notes
        })
      });

      const result = await response.json();
      
      if (response.ok) {
        // Remove the project from pending list
        setPendingProjects(prev => prev.filter(p => p.id !== projectId));
        // Clear the notes for this project
        setApprovalNotes(prev => {
          const newNotes = { ...prev };
          delete newNotes[projectId];
          return newNotes;
        });
        
        alert(`Project ${action}d successfully!`);
      } else {
        alert(`Failed to ${action} project: ${result.error}`);
      }
    } catch (error) {
      console.error(`Error ${action}ing project:`, error);
      alert(`Error ${action}ing project. Please try again.`);
    }
  };

  const updateNotes = (projectId, notes) => {
    setApprovalNotes(prev => ({
      ...prev,
      [projectId]: notes
    }));
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusStyles = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      finished: 'bg-blue-100 text-blue-800'
    };
    
    const statusLabels = {
      pending: 'Pending',
      approved: 'Approved',
      rejected: 'Rejected',
      finished: 'Finished'
    };

    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusStyles[status] || 'bg-gray-100 text-gray-800'}`}>
        {statusLabels[status] || status}
      </span>
    );
  };

  return (
    <main className="flex-1">
      <section className="relative rounded-3xl p-8 shadow-2xl bg-white/80 backdrop-blur-xl ring-1 ring-gray-200/50 h-full">
        <div className="absolute inset-0 -z-10 rounded-3xl bg-gradient-to-br from-purple-500/5 via-pink-500/5 to-red-400/5" />
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl blur-sm opacity-75"></div>
              <div className="relative h-12 w-12 rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-bold text-gray-900">Admin Dashboard - {userData?.state}</h3>
              <p className="text-gray-600">Project approval and management</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* View Toggle Buttons */}
            <div className="flex rounded-lg bg-gray-100 p-1">
              <button
                onClick={() => {
                  setCurrentView('all');
                  loadAllProjects();
                }}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'all'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                All Projects
              </button>
              <button
                onClick={() => {
                  setCurrentView('pending');
                  loadPendingProjects();
                }}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'pending'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Pending
              </button>
              <button
                onClick={() => {
                  setCurrentView('approved');
                  loadAllProjects();
                }}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'approved'
                    ? 'bg-white text-green-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Approved
              </button>
              <button
                onClick={() => {
                  setCurrentView('rejected');
                  loadAllProjects();
                }}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'rejected'
                    ? 'bg-white text-red-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Rejected
              </button>
            </div>

            {/* Refresh Button */}
            <button 
              onClick={currentView === 'pending' ? loadPendingProjects : loadAllProjects}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="p-6 rounded-2xl bg-gradient-to-br from-yellow-50 to-orange-50 border border-yellow-200/50">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-yellow-500 flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h4 className="text-lg font-semibold text-gray-900">Pending</h4>
                <p className="text-2xl font-bold text-yellow-600">
                  {currentView === 'pending' ? pendingProjects.length : allProjects.filter(p => p.status === 'pending').length}
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200/50">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-green-500 flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h4 className="text-lg font-semibold text-gray-900">Approved</h4>
                <p className="text-2xl font-bold text-green-600">
                  {currentView === 'all' ? allProjects.filter(p => p.status === 'approved').length : 0}
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gradient-to-br from-red-50 to-rose-50 border border-red-200/50">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-red-500 flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div>
                <h4 className="text-lg font-semibold text-gray-900">Rejected</h4>
                <p className="text-2xl font-bold text-red-600">
                  {currentView === 'all' ? allProjects.filter(p => p.status === 'rejected').length : 0}
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200/50">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-purple-500 flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div>
                <h4 className="text-lg font-semibold text-gray-900">State Coverage</h4>
                <p className="text-2xl font-bold text-purple-600">{userData?.state}</p>
              </div>
            </div>
          </div>

        </div>

        {/* Projects Section */}
        <div className="bg-white/80 backdrop-blur-xl rounded-2xl p-6 shadow-lg ring-1 ring-gray-200/50 border border-white/20">
          <h4 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
            {currentView === 'pending' && (
              <>
                <svg className="h-5 w-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Projects Pending Approval ({pendingProjects.length})
              </>
            )}
            {currentView === 'approved' && (
              <>
                <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Approved Projects from {userData?.state} ({getApprovedProjects().length})
              </>
            )}
            {currentView === 'rejected' && (
              <>
                <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Rejected Projects from {userData?.state} ({getRejectedProjects().length})
              </>
            )}
            {currentView === 'all' && (
              <>
                <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                All Projects from {userData?.state} ({allProjects.length})
              </>
            )}
          </h4>

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-600 mt-4">Loading {currentView} projects...</p>
            </div>
          ) : getCurrentProjects().length === 0 ? (
            <div className="text-center py-12">
              <svg className="h-16 w-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h5 className="text-lg font-semibold text-gray-900 mb-2">
                {currentView === 'pending' && 'All Caught Up!'}
                {currentView === 'approved' && 'No Approved Projects'}
                {currentView === 'rejected' && 'No Rejected Projects'}
                {currentView === 'all' && 'No Projects Found'}
              </h5>
              <p className="text-gray-600">
                {currentView === 'pending' && `No projects pending approval from ${userData?.state}`}
                {currentView === 'approved' && `No approved projects from ${userData?.state}`}
                {currentView === 'rejected' && `No rejected projects from ${userData?.state}`}
                {currentView === 'all' && `No projects found from ${userData?.state}`}
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {getCurrentProjects().map((project) => (
                <div key={project.id} className="border border-gray-200 rounded-xl p-6 bg-white/50 hover:bg-white/70 transition-all duration-200">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h5 className="text-lg font-semibold text-gray-900 mb-1">
                        Project #{project.id} - {project.location}
                      </h5>
                      <p className="text-sm text-gray-600">
                        Created by: <span className="font-medium">{project.creator_fullname}</span> ({project.created_by_username})
                      </p>
                      <p className="text-sm text-gray-500">
                        Submitted: {formatDate(project.created_at)}
                      </p>
                    </div>
                    {getStatusBadge(project.status)}
                  </div>

                  {/* Project Details Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm text-gray-600">Budget</p>
                      <p className="font-semibold">{project.budget}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Tower Type</p>
                      <p className="font-semibold">{project.tower_type}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Substation</p>
                      <p className="font-semibold">{project.substation_type}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Geography</p>
                      <p className="font-semibold">{project.geo}</p>
                    </div>
                  </div>

                  {/* Forecasts */}
                  {(project.steel_forecast || project.conductor_forecast) && (
                    <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm font-semibold text-gray-700 mb-2">Demand Forecasts:</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        {project.steel_forecast && (
                          <div>
                            <span className="text-gray-600">Steel:</span>
                            <span className="ml-1 font-medium">{project.steel_forecast.toFixed(2)}</span>
                          </div>
                        )}
                        {project.conductor_forecast && (
                          <div>
                            <span className="text-gray-600">Conductor:</span>
                            <span className="ml-1 font-medium">{project.conductor_forecast.toFixed(2)}</span>
                          </div>
                        )}
                        {project.transformers_forecast && (
                          <div>
                            <span className="text-gray-600">Transformers:</span>
                            <span className="ml-1 font-medium">{project.transformers_forecast.toFixed(2)}</span>
                          </div>
                        )}
                        {project.tower_forecast && (
                          <div>
                            <span className="text-gray-600">Tower:</span>
                            <span className="ml-1 font-medium">{project.tower_forecast.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Approval Notes and Actions - Only for Pending Projects in Pending View */}
                  {currentView === 'pending' && project.status === 'pending' && (
                    <>
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Approval Notes (Optional)
                        </label>
                        <textarea
                          value={approvalNotes[project.id] || ''}
                          onChange={(e) => updateNotes(project.id, e.target.value)}
                          placeholder="Add any notes about this approval/rejection..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                          rows="2"
                        />
                      </div>

                      {/* Action Buttons */}
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleApproval(project.id, 'approve')}
                          className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center gap-2 font-medium"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Approve Project
                        </button>
                        <button
                          onClick={() => handleApproval(project.id, 'reject')}
                          className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center gap-2 font-medium"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          Reject Project
                        </button>
                      </div>
                    </>
                  )}

                  {/* Additional Info for Non-Pending Projects */}
                  {currentView !== 'pending' && project.status !== 'pending' && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        {project.approved_at && (
                          <div>
                            <span className="text-gray-600">Approved:</span>
                            <span className="ml-1 font-medium">{formatDate(project.approved_at)}</span>
                          </div>
                        )}
                        {project.rejected_at && (
                          <div>
                            <span className="text-gray-600">Rejected:</span>
                            <span className="ml-1 font-medium">{formatDate(project.rejected_at)}</span>
                          </div>
                        )}
                        {project.approval_notes && (
                          <div className="md:col-span-2">
                            <span className="text-gray-600">Admin Notes:</span>
                            <span className="ml-1 font-medium">{project.approval_notes}</span>
                          </div>
                        )}
                        {project.rejection_notes && (
                          <div className="md:col-span-2">
                            <span className="text-gray-600">Rejection Notes:</span>
                            <span className="ml-1 font-medium">{project.rejection_notes}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
};

export default AdminDashboard;
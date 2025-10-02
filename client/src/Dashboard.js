import React, { useState } from 'react';

const Dashboard = ({ projects, goBack, showAllProjects = false, onProjectUpdate }) => {
  const [selectedProject, setSelectedProject] = useState(null);
  const [showProjectModal, setShowProjectModal] = useState(false);

  const openProjectDetails = (project) => {
    setSelectedProject(project);
    setShowProjectModal(true);
  };

  const closeProjectDetails = () => {
    setSelectedProject(null);
    setShowProjectModal(false);
  };

  const handleProjectAction = async (projectId, action) => {
    try {
      const endpoint = action === 'finished' ? 'finish' : 'delete';
      const method = action === 'delete' ? 'DELETE' : 'PUT';
      
      const response = await fetch(`http://localhost:5002/projects/${projectId}/${endpoint}`, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        alert(`Project ${action} successfully!`);
        closeProjectDetails();
        if (onProjectUpdate) {
          onProjectUpdate(); // Refresh projects list
        }
      } else {
        const result = await response.json();
        alert(`Failed to ${action} project: ${result.error}`);
      }
    } catch (error) {
      console.error(`Error ${action}ing project:`, error);
      alert(`Error ${action}ing project. Please try again.`);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  return (
    <main className="flex-1">
      <section className="relative rounded-3xl p-8 shadow-2xl bg-white/80 backdrop-blur-xl ring-1 ring-gray-200/50 h-full">
        <div className="absolute inset-0 -z-10 rounded-3xl bg-gradient-to-br from-emerald-500/5 via-blue-500/5 to-purple-400/5" />
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl blur-sm opacity-75"></div>
              <div className="relative h-12 w-12 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            <div>
              <h3 className="text-3xl font-bold text-gray-900">Dashboard</h3>
              <p className="text-gray-600">Overview of your projects and analytics</p>
            </div>
          </div>
          <button
            onClick={goBack}
            className="px-6 py-3 rounded-2xl bg-gradient-to-r from-gray-500 to-gray-600 text-white font-semibold shadow-lg hover:shadow-xl hover:from-gray-600 hover:to-gray-700 transition-all duration-200 transform hover:-translate-y-1 flex items-center gap-2"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back
          </button>
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="p-6 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200/50 hover:border-emerald-300 transition-all duration-200 hover:shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-500 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-emerald-600 uppercase tracking-wide">Total Projects</p>
                <p className="text-3xl font-bold text-gray-900">{projects.length}</p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200/50 hover:border-blue-300 transition-all duration-200 hover:shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">Approved</p>
                <p className="text-3xl font-bold text-gray-900">{projects.filter(p => p.status === 'approved').length}</p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gradient-to-br from-yellow-50 to-orange-50 border border-yellow-200/50 hover:border-yellow-300 transition-all duration-200 hover:shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-xl bg-yellow-500 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-yellow-600 uppercase tracking-wide">Pending</p>
                <p className="text-3xl font-bold text-gray-900">{projects.filter(p => p.status === 'pending').length}</p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200/50 hover:border-purple-300 transition-all duration-200 hover:shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-xl bg-purple-500 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-purple-600 uppercase tracking-wide">Finished</p>
                <p className="text-3xl font-bold text-gray-900">{projects.filter(p => p.status === 'finished').length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Projects */}
        <div className="bg-white/80 backdrop-blur-xl rounded-2xl p-6 shadow-lg ring-1 ring-gray-200/50 border border-white/20">
          <div className="flex items-center justify-between mb-6">
            <h4 className="text-xl font-bold text-gray-900 flex items-center gap-3">
              <svg className="h-5 w-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              {showAllProjects ? 'All My Projects' : 'Recent Projects'}
            </h4>
            {showAllProjects && (
              <button
                onClick={goBack}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors flex items-center gap-2"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Dashboard
              </button>
            )}
          </div>
          
          {projects.length === 0 ? (
            <div className="text-center py-12">
              <div className="h-16 w-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
                <svg className="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-gray-500 text-lg font-medium">No projects yet</p>
              <p className="text-gray-400 text-sm">Create your first project to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {(showAllProjects ? projects : projects.slice(0, 5)).map((project, index) => (
                <div 
                  key={index} 
                  className="flex items-center justify-between p-4 rounded-xl bg-gray-50/50 hover:bg-gray-100/50 transition-all duration-200 cursor-pointer hover:shadow-md"
                  onClick={() => openProjectDetails(project)}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </div>
                    <div>
                      <h5 className="font-semibold text-gray-900">{project.location}</h5>
                      <p className="text-sm text-gray-500">Budget: {project.budget}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      project.status === 'approved' ? 'bg-green-100 text-green-800' :
                      project.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                      project.status === 'rejected' ? 'bg-red-100 text-red-800' :
                      project.status === 'declined' ? 'bg-red-100 text-red-800' :
                      project.status === 'finished' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {project.status}
                    </span>
                    <p className="text-xs text-gray-400">{project.createdAt}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Project Details Modal */}
      {showProjectModal && selectedProject && (
        <div className="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-white rounded-3xl p-8 max-h-[90vh] overflow-y-auto hide-scrollbar">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center">
                  <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-2xl font-bold">Project Details</h3>
                  <p className="text-gray-500 text-sm">Review project information and status</p>
                </div>
              </div>
              <button
                onClick={closeProjectDetails}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <svg className="h-6 w-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Scrollable Content Container */}
            <div className="space-y-4 mb-6">
              {/* Row 1: Budget & Location */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Budget (INR)</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {selectedProject.budget}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Project Location</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {selectedProject.location}
                  </div>
                </div>
              </div>

              {/* Row 2: Tower Type & Substation Type */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Tower Type</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {selectedProject.towerType}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Substation Type</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {selectedProject.substationType}
                  </div>
                </div>
              </div>

              {/* Row 3: Geographic Location & Taxes */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Geographic Location</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {selectedProject.geo}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Taxes</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {selectedProject.taxes}
                  </div>
                </div>
              </div>

              {/* Row 4: Status & Created Date */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                      selectedProject.status === 'approved' ? 'bg-green-100 text-green-800' :
                      selectedProject.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                      selectedProject.status === 'rejected' ? 'bg-red-100 text-red-800' :
                      selectedProject.status === 'finished' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {selectedProject.status}
                    </span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Created Date</label>
                  <div className="w-full p-3 border rounded-xl bg-gray-50 text-gray-900 font-medium">
                    {formatDate(selectedProject.created_at)}
                  </div>
                </div>
              </div>
            </div>

            {/* Demand Forecasts */}
            {(selectedProject.steel_forecast !== undefined || selectedProject.conductor_forecast !== undefined || selectedProject.transformers_forecast !== undefined || selectedProject.earthwire_forecast !== undefined || selectedProject.foundation_forecast !== undefined || selectedProject.reactors_forecast !== undefined || selectedProject.tower_forecast !== undefined) && (
              <div className="bg-blue-50 rounded-2xl p-6 mb-6">
                <h5 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  AI Demand Forecasts
                </h5>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {selectedProject.steel_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Steel</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.steel_forecast)} MT</p>
                    </div>
                  )}
                  {selectedProject.conductor_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Conductor</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.conductor_forecast)} MT</p>
                    </div>
                  )}
                  {selectedProject.transformers_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Transformers</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.transformers_forecast)} MT</p>
                    </div>
                  )}
                  {selectedProject.tower_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Tower</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.tower_forecast)} MT</p>
                    </div>
                  )}
                  {selectedProject.earthwire_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Earthwire</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.earthwire_forecast)} MT</p>
                    </div>
                  )}
                  {selectedProject.foundation_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Foundation</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.foundation_forecast)} MT</p>
                    </div>
                  )}
                  {selectedProject.reactors_forecast !== undefined && (
                    <div className="text-center p-4 bg-white rounded-xl">
                      <p className="text-sm text-gray-600 mb-1">Reactors</p>
                      <p className="text-xl font-bold text-gray-900">{Math.ceil(selectedProject.reactors_forecast)} MT</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4 justify-end">
              <button
                onClick={closeProjectDetails}
                className="px-6 py-3 bg-gray-300 text-gray-700 rounded-xl font-semibold hover:bg-gray-400 transition-colors"
              >
                Close
              </button>
              
              {selectedProject.status !== 'finished' && selectedProject.status !== 'rejected' && (
                <button
                  onClick={() => handleProjectAction(selectedProject.id, 'finished')}
                  className="px-6 py-3 bg-blue-500 text-white rounded-xl font-semibold hover:bg-blue-600 transition-colors flex items-center gap-2"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Mark as Finished
                </button>
              )}
              
              <button
                onClick={() => {
                  if (window.confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
                    handleProjectAction(selectedProject.id, 'delete');
                  }
                }}
                className="px-6 py-3 bg-red-500 text-white rounded-xl font-semibold hover:bg-red-600 transition-colors flex items-center gap-2"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete Project
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
};

export default Dashboard;


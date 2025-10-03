import React, { useState, useEffect, useCallback } from "react";
import Map from './Map'; // This line is still needed
import Dashboard from './Dashboard';
import AdminDashboard from './AdminDashboard';

function App() {
  // States
  const [userData, setUserData] = useState({});
  const [projects, setProjects] = useState([]);
  // Removed unused currentProjectIndex state
  const [showProfile, setShowProfile] = useState(false);
  const [activityLog, setActivityLog] = useState([]);
  const [modals, setModals] = useState({
    project: false,
    signup: false,
    login: false,
    projectDetails: false,
    verify2FA: false,
  });
  const [message, setMessage] = useState("");
  const [showMessage, setShowMessage] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showProjects, setShowProjects] = useState(false);
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);
  const [showForecastResults, setShowForecastResults] = useState(false);
  const [currentForecastData, setCurrentForecastData] = useState(null);
  const [loginError, setLoginError] = useState("");
  const [signupError, setSignupError] = useState("");
  const [signupRole, setSignupRole] = useState("");
  const [signupAdminLevel, setSignupAdminLevel] = useState("");

  // Load user session from localStorage on app startup
  useEffect(() => {
    const savedUser = localStorage.getItem('userData');
    if (savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser);
        setUserData(parsedUser);
      } catch (error) {
        console.error('Error parsing saved user data:', error);
        localStorage.removeItem('userData');
      }
    }
  }, []);

  // Moved useEffect to after loadUserProjects definition

  // State mapping for admin oversight
  const stateMapping = {
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Meerut", "Agra", "Varanasi"],
    Maharashtra: ["Mumbai", "Pune", "Nagpur"],
    Karnataka: ["Bengaluru", "Mysore"],
    "Tamil Nadu": ["Chennai", "Coimbatore"],
    "West Bengal": ["Kolkata", "Siliguri"],
    Rajasthan: ["Jaipur", "Jodhpur"],
    Gujarat: ["Ahmedabad", "Surat"],
    Telangana: ["Hyderabad", "Warangal"],
    Delhi: ["Delhi"],
  };

  // Custom message box function
  const showCustomMessage = (msg) => {
    setMessage(msg);
    setShowMessage(true);
    setTimeout(() => {
      setShowMessage(false);
      setMessage("");
    }, 3000);
  };

  // Add activity log
  const logActivity = (msg) => {
    setActivityLog((prev) => [msg, ...prev]);
  };

  // Get user's state based on role and location
  const getUserState = (location) => {
    for (const [state, cities] of Object.entries(stateMapping)) {
      if (cities.includes(location)) {
        return state;
      }
    }
    return "Unknown";
  };

  // Removed unused getAdminProjects function

  // Load projects from database
  const loadUserProjects = useCallback(async () => {
    if (!userData.id) {
      console.log("No user ID available, skipping project load");
      return;
    }
    
    try {
      console.log(`Loading projects for user ID: ${userData.id}`);
      const response = await fetch(`http://127.0.0.1:5002/projects/${userData.id}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Projects loaded:", result.projects);
        setProjects(result.projects || []);
        return result.projects || [];
      } else {
        const errorData = await response.json();
        console.error("Failed to load projects:", errorData);
        return [];
      }
    } catch (error) {
      console.error("Error loading projects:", error);
      // Don't clear projects on error, keep existing ones
      return [];
    }
  }, [userData.id]);

  // Load projects when user logs in
  useEffect(() => {
    if (userData.id) {
      loadUserProjects();
    }
  }, [userData.id]);

  // Project handlers
  const handleCreateProject = async (e) => {
    e.preventDefault();
    const form = e.target;
    const projectData = {
      budget: form.budget.value,
      location: form.location.value,
      towerType: form.towerType.value,
      substationType: form.substationType.value,
      geo: form.geo.value,
      taxes: form.taxes.value,
      created_by_user_id: userData.id,
      created_by_username: userData.name,
      created_by_role: userData.role,
    };

    try {
      // Create project via API (which includes prediction)
      const response = await fetch("http://127.0.0.1:5002/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Project creation failed.");
      }

      const result = await response.json();
      console.log("Project creation result:", result);
      
      logActivity(`Created project for: ${projectData.location} (Status: ${result.status})`);
      form.reset();
      setModals({ ...modals, project: false });

      // Reload projects from database and then show forecast results
      const updatedProjects = await loadUserProjects();
      console.log("Updated projects after creation:", updatedProjects);
      
      // Get the newly created project (should be the first one after reload)
      const newProject = updatedProjects && updatedProjects.length > 0 ? updatedProjects[0] : null;
      
      if (newProject && newProject.allForecasts) {
        // Show forecast results immediately after project creation
        // Include both forecast data AND project input parameters
        setCurrentForecastData({
          forecasts: newProject.allForecasts,
          projectDetails: {
            budget: newProject.budget,
            location: newProject.location,
            towerType: newProject.towerType,
            substationType: newProject.substationType,
            geo: newProject.geo,
            taxes: newProject.taxes,
            status: newProject.status,
            createdAt: newProject.createdAt
          }
        });
        setShowForecastResults(true);
      } else {
        // Fallback to dashboard if no forecast data
        setShowDashboard(true);
      }
      
      showCustomMessage(
        userData.role === "admin" ? "Demand forecasted and approved!" : "Demand forecasted! Awaiting admin approval."
      );
      
    } catch (error) {
      showCustomMessage(`Error: ${error.message}`);
      console.error("Error creating project:", error);
    }
  };

  // Removed unused handleOpenProjectDetails function

  // Removed unused handleDeleteProject function

  // Admin project management
  // eslint-disable-next-line no-unused-vars
  const handleProjectAction = async (projectId, action) => {
    try {
      const response = await fetch(`http://127.0.0.1:5002/projects/${projectId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          status: action,
          user_id: userData.id 
        }),
      });

      if (response.ok) {
        // Reload projects from database
        await loadUserProjects();
        logActivity(`${action.charAt(0).toUpperCase() + action.slice(1)} project ID: ${projectId}`);
        showCustomMessage(`Project ${action} successfully!`);
      } else {
        const errorData = await response.json();
        showCustomMessage(`Error: ${errorData.error || "Failed to update project status"}`);
      }
    } catch (error) {
      showCustomMessage(`Error: ${error.message}`);
      console.error("Error updating project status:", error);
    }
  };

  // User handlers
  const handleSignup = async (e) => {
    e.preventDefault();
    setSignupError(""); // Clear previous errors
    const form = e.target;
    const signupData = {
      fullname: form.fullname.value,
      username: form.email.value, // Using email as username
      password: form.password.value,
      role: form.role.value,
      admin_level: signupAdminLevel || undefined,
      state: form.state?.value || "",
    };

    try {
      const response = await fetch("http://127.0.0.1:5002/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signupData),
      });

      const result = await response.json();

      if (response.ok) {
        // Signup successful
        logActivity("Account created successfully");
        setSignupError(""); // Clear any errors
        setModals({ 
          project: false,
          signup: false,
          login: true, // Open login modal
          projectDetails: false,
          verify2FA: false 
        });
        // Show success message on top of login modal
        showCustomMessage("Account created successfully! Please login.");
      } else {
        // Signup failed - show error inline
        setSignupError(result.error || "Signup failed. Please try again.");
      }
    } catch (error) {
      console.error("Signup error:", error);
      // Check if it's a network error (server not running) vs other errors
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        setSignupError("Unable to connect to server. Please check your connection and try again.");
      } else {
        setSignupError("An unexpected error occurred. Please try again.");
      }
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError(""); // Clear previous errors
    const form = e.target;
    const loginData = {
      username: form.email.value, // Using email as username
      password: form.password.value,
    };

    try {
      const response = await fetch("http://127.0.0.1:5002/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginData),
      });

      const result = await response.json();

      if (response.ok) {
        // Login successful
        const user = result.user;
        const newUserData = {
          id: user.id,
          name: user.fullname || user.username, // Use fullname if available, fallback to username
          fullname: user.fullname, // Store the actual fullname from backend
          username: user.username, // Store the username separately
          email: user.username, // Using username as email for compatibility
          role: user.role,
          state: user.state || getUserState("Mumbai"), // Use state from backend, fallback to default
          created_at: user.created_at,
          last_login: user.last_login
        };
        
        setUserData(newUserData);
        // Save user data to localStorage for session persistence
        localStorage.setItem('userData', JSON.stringify(newUserData));
        logActivity("Logged in successfully");
        setLoginError(""); // Clear any errors
        setModals({ ...modals, login: false });
        // Show success message after closing modal
        showCustomMessage("Login successful!");
      } else {
        // Login failed - show error inline
        setLoginError(result.error || "Username and password not found.");
      }
    } catch (error) {
      console.error("Login error:", error);
      // Check if it's a network error (server not running) vs other errors
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        setLoginError("Unable to connect to server. Please check your connection and try again.");
      } else {
        setLoginError("An unexpected error occurred. Please try again.");
      }
    }
  };

  // Render functions
  const renderForecasts = (forecasts) => {
    if (!forecasts) return <p className="text-gray-500">N/A</p>;
    const modelNames = Object.keys(forecasts).sort();

    return (
      <div className="pt-5 space-y-3">
        <h4 className="text-xl font-extrabold bg-gradient-to-r from-emerald-600 via-teal-600 to-lime-600 bg-clip-text text-transparent tracking-tight">
          Material Forecasts (MT)
        </h4>
        <div className="grid grid-cols-2 gap-4 text-gray-800">
          {modelNames.map((modelName) => (
            <p
              key={modelName}
              className="relative p-[1px] rounded-xl bg-gradient-to-tr from-emerald-400/70 via-teal-500/70 to-lime-500/70 transition-transform hover:scale-[1.01]"
            >
              <span className="block bg-white/80 backdrop-blur-sm rounded-[11px] p-3 shadow-sm">
                <strong className="text-gray-900">{modelName.charAt(0).toUpperCase() + modelName.slice(1)}:</strong>
                {Number.isFinite(forecasts[modelName]) ? ` ${Math.ceil(forecasts[modelName])}` : " N/A"}
              </span>
            </p>
          ))}
        </div>
      </div>
    );
  };

  // eslint-disable-next-line no-unused-vars
  const getStatusBadge = (status) => {
    const colors = {
      pending: "bg-yellow-100 text-yellow-800 ring-yellow-300/50",
      approved: "bg-green-100 text-green-800 ring-green-300/50",
      declined: "bg-red-100 text-red-800 ring-red-300/50",
      deleted: "bg-gray-100 text-gray-800 ring-gray-300/50",
      finished: "bg-blue-100 text-blue-800 ring-blue-300/50",
    };
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-semibold ring-1 shadow-sm ${colors[status]} uppercase tracking-wide`}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="min-h-screen flex flex-col font-sans selection:bg-emerald-300/40 bg-gradient-to-br from-slate-50 via-white to-emerald-50/30">
      {/* Modern animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -inset-10 opacity-30">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-300/20 rounded-full mix-blend-multiply filter blur-xl animate-blob"></div>
          <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-teal-300/20 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-1/3 w-96 h-96 bg-lime-300/20 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-4000"></div>
        </div>
      </div>
      
      <nav className="relative z-10 mx-4 mt-4 rounded-3xl bg-white/80 backdrop-blur-xl text-gray-900 px-8 py-5 flex justify-between items-center shadow-2xl ring-1 ring-gray-200/50 border border-white/20">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl blur-sm opacity-75"></div>
            <span className="relative inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 shadow-lg">
              <svg version="1.0" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 300.000000 300.000000" preserveAspectRatio="xMidYMid meet">
                <g transform="translate(0.000000,300.000000) scale(0.050000,-0.050000)" fill="#ffffff" stroke="none">
                  <path d="M2870 4775 c-5 -14 -17 -61 -26 -105 l-16 -80 -345 -5 -346 -6 -103 -69 -103 -70 159 1 c109 0 172 10 199 30 30 22 105 29 335 29 l296 0 -2 -55 c0 -30 -6 -44 -11 -30 -18 44 -162 31 -177 -15 -12 -38 -30 -40 -452 -40 l-440 0 -49 -53 c-27 -29 -45 -58 -39 -64 18 -17 198 -2 219 19 31 30 956 23 946 -7 -5 -15 -53 -27 -123 -31 -78 -4 -118 -15 -125 -36 -10 -25 -88 -29 -513 -27 l-502 2 -35 -47 c-58 -75 -47 -96 52 -96 59 0 95 10 106 30 20 37 1101 37 1110 0 3 -12 -56 -22 -138 -26 -95 -4 -152 -15 -168 -35 -20 -24 -113 -29 -544 -29 -542 0 -571 -5 -574 -88 -1 -11 286 -13 709 -6 618 11 710 9 710 -17 0 -23 -34 -29 -178 -29 -132 0 -183 -8 -202 -30 -20 -24 -116 -30 -565 -35 l-540 -5 -17 -46 -17 -45 759 5 c673 5 760 2 760 -25 0 -26 -30 -29 -196 -23 -162 7 -200 3 -222 -24 -24 -28 -96 -32 -582 -32 -580 0 -580 0 -580 -82 0 -10 324 -18 790 -18 706 0 790 -3 790 -32 0 -27 -30 -30 -209 -26 -174 4 -216 -1 -247 -28 -33 -30 -101 -34 -601 -34 l-563 0 0 -45 0 -45 800 0 c517 0 802 -7 805 -20 3 -12 -62 -22 -158 -26 -113 -4 -171 -15 -188 -35 -20 -24 -125 -29 -651 -29 l-628 0 0 -50 0 -51 755 1 c509 1 757 -5 761 -19 4 -12 -26 -21 -74 -21 -60 0 -88 -11 -107 -40 -24 -39 -46 -40 -680 -40 l-655 0 0 -45 0 -45 770 7 c693 6 770 3 770 -25 0 -26 -23 -32 -118 -32 -80 0 -125 -10 -142 -30 -21 -25 -119 -30 -650 -30 l-624 0 10 -53 10 -52 757 9 c618 7 757 4 757 -18 0 -19 -37 -26 -138 -26 -97 0 -144 -9 -162 -30 -21 -25 -114 -30 -604 -30 l-579 0 7 -45 6 -45 750 -3 c586 -2 750 -8 750 -28 0 -18 -45 -24 -172 -21 -134 3 -177 -2 -197 -27 -22 -27 -100 -31 -553 -31 -291 0 -528 -7 -528 -16 0 -87 16 -89 756 -81 554 5 704 2 704 -18 0 -18 -55 -25 -211 -25 -168 0 -213 -6 -222 -30 -10 -25 -81 -30 -469 -30 -252 0 -458 -7 -457 -15 3 -90 21 -92 719 -79 575 12 660 9 660 -16 0 -25 -41 -30 -238 -30 -185 0 -243 -7 -262 -30 -19 -23 -97 -30 -390 -35 -358 -5 -366 -6 -339 -44 27 -36 56 -38 639 -33 544 5 610 2 610 -26 0 -28 -38 -32 -279 -32 -261 0 -281 -3 -308 -42 -28 -40 -44 -42 -261 -35 -243 8 -255 4 -194 -51 35 -32 82 -33 550 -20 468 13 512 11 512 -19 0 -29 -36 -33 -318 -33 -264 0 -320 -5 -329 -30 -8 -21 -41 -30 -112 -30 -56 0 -101 -9 -101 -19 0 -53 97 -65 483 -62 347 3 397 -1 397 -28 0 -27 -45 -31 -325 -32 -368 0 -381 -15 -97 -107 382 -125 701 -121 1082 12 254 89 245 96 -136 96 -297 0 -344 4 -344 31 0 27 51 31 407 28 311 -3 417 3 450 24 67 41 52 57 -55 57 -62 0 -106 11 -122 30 -20 24 -85 30 -342 30 -282 0 -318 4 -318 33 0 30 44 32 515 20 488 -12 517 -11 560 25 71 61 59 64 -190 50 -223 -12 -237 -11 -273 29 -36 40 -58 43 -325 43 -245 0 -287 5 -287 31 0 27 74 30 621 28 613 -2 679 4 679 63 0 10 -161 18 -358 18 -293 0 -362 5 -382 30 -20 24 -78 30 -282 30 -216 0 -258 5 -258 30 0 26 82 28 677 17 l676 -13 34 48 34 48 -465 5 c-386 5 -468 11 -481 35 -14 24 -66 30 -256 30 -194 0 -239 5 -239 29 0 24 106 27 742 16 625 -10 745 -7 760 17 48 76 35 78 -510 78 -459 0 -529 4 -540 31 -10 26 -48 31 -227 28 -177 -4 -216 1 -221 26 -5 26 89 28 777 19 656 -8 786 -5 801 18 48 76 37 78 -570 78 -497 0 -591 5 -612 30 -18 21 -65 30 -164 30 -103 0 -137 7 -131 25 7 20 173 23 769 18 l760 -8 10 53 10 52 -634 0 c-540 0 -639 4 -660 30 -17 20 -62 30 -142 30 -94 0 -118 6 -118 31 0 28 83 31 780 25 732 -6 780 -4 780 29 0 19 0 40 0 46 0 6 -297 10 -659 10 -642 -2 -660 -1 -681 39 -18 33 -41 40 -142 40 -80 0 -119 8 -114 22 5 16 235 21 802 19 l794 -3 0 51 0 51 -628 0 c-533 0 -631 4 -652 30 -18 22 -66 30 -172 30 -121 0 -148 6 -148 31 0 28 84 31 790 25 l790 -6 0 45 0 45 -573 0 c-514 0 -578 4 -612 34 -30 28 -77 35 -230 35 -135 1 -194 8 -200 26 -7 20 159 25 785 25 716 0 793 3 782 32 -7 17 -12 40 -12 50 0 10 -236 18 -568 18 -497 0 -570 4 -594 32 -22 27 -59 31 -212 24 -158 -7 -186 -3 -186 23 0 28 84 30 750 25 483 -4 750 0 750 13 0 83 0 83 -570 83 -467 0 -547 4 -557 30 -9 24 -51 30 -202 30 -158 0 -191 5 -191 30 0 27 84 30 710 21 391 -6 710 -5 710 1 0 85 -19 88 -558 88 -435 0 -521 5 -542 30 -18 22 -67 30 -182 30 -127 0 -158 6 -158 30 0 26 73 30 538 30 460 0 539 -4 549 -30 19 -49 233 -42 233 7 0 99 -42 107 -566 104 -424 -2 -491 1 -501 28 -9 24 -43 31 -142 31 -103 0 -131 6 -131 30 0 37 876 46 913 9 12 -12 77 -18 146 -15 l125 6 -44 55 -43 55 -434 0 c-430 0 -434 0 -453 45 -23 50 -184 57 -214 9 -9 -14 -16 -2 -16 31 l0 55 275 -1 c210 0 284 -7 314 -30 42 -32 391 -43 391 -13 0 75 -170 114 -539 124 l-369 10 -21 98 c-21 100 -75 160 -56 63 9 -46 3 -51 -53 -51 -53 0 -62 7 -62 50 0 52 -34 69 -50 25z m158 -695 c7 -115 21 -300 31 -410 36 -390 61 -643 80 -830 28 -262 31 -246 -39 -210 l-60 31 0 -710 c0 -698 -1 -711 -40 -711 -22 0 -40 7 -40 15 -1 8 -9 119 -20 245 -11 127 -33 401 -50 610 -16 209 -34 412 -40 450 -5 39 -15 160 -21 270 -6 110 -15 215 -21 233 -5 19 0 39 11 46 12 8 21 -4 21 -27 0 -33 51 -82 84 -82 4 0 10 218 12 485 2 267 10 625 18 795 l13 310 24 -150 c13 -82 29 -244 37 -360z"/>
                </g>
              </svg>
            </span>
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
              PrecisionGrid Analytics
            </h1>
            <p className="text-xs text-gray-500 font-medium">Material Demand Forecasting</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {!userData.email && (
            <>
              <button
                className="group relative px-6 py-2.5 rounded-2xl bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 shadow-sm hover:shadow-md"
                onClick={() => {
                  setSignupError(""); // Clear signup errors
                  setModals({ ...modals, signup: true });
                }}
              >
                <span className="relative font-semibold">Sign Up</span>
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 opacity-0 group-hover:opacity-10 transition-opacity duration-200"></div>
              </button>
              <button
                className="px-6 py-2.5 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg hover:shadow-xl hover:from-emerald-600 hover:to-teal-600 transition-all duration-200 transform hover:-translate-y-0.5"
                onClick={() => {
                  setLoginError(""); // Clear login errors
                  setModals({ ...modals, login: true });
                }}
              >
                Login
              </button>
            </>
          )}
          {userData.email && (
            <>
              <button
                className="group relative px-5 py-2.5 rounded-2xl bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2"
                onClick={() => {
                  setShowProfile(false);
                  setShowDashboard(false);
                  setShowProjects(false);
                  setShowAdminDashboard(false);
                  setModals({
                    project: false,
                    signup: false,
                    login: false,
                    projectDetails: false,
                    verify2FA: false,
                  });
                }}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0h6" />
                </svg>
                <span className="font-semibold">Home</span>
              </button>
              <button
                className="group relative px-5 py-2.5 rounded-2xl bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2"
                onClick={() => {
                  // Reset all other views when showing profile
                  setShowDashboard(false);
                  setShowProjects(false);
                  setShowAdminDashboard(false);
                  setModals({
                    project: false,
                    signup: false,
                    login: false,
                    projectDetails: false,
                    verify2FA: false,
                  });
                  // Toggle profile view
                  setShowProfile(!showProfile);
                }}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="font-semibold">Profile</span>
              </button>
              {userData.role === "admin" && (
                <button
                  className="px-6 py-2.5 rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold shadow-lg hover:shadow-xl hover:from-purple-600 hover:to-pink-600 transition-all duration-200 transform hover:-translate-y-0.5 flex items-center gap-2"
                  onClick={() => {
                    setShowAdminDashboard(true);
                    setShowDashboard(false);
                    setShowProjects(false);
                    setShowProfile(false);
                    setShowForecastResults(false);
                    setCurrentForecastData(null);
                  }}
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Admin Panel
                </button>
              )}
              <button
                className="group relative px-5 py-2.5 rounded-2xl bg-white border border-red-200 text-red-600 hover:bg-red-50 hover:border-red-300 transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2"
                onClick={() => {
                  const userWasLoggedIn = !!userData.email;
                  
                  // Clear user data and projects
                  setUserData({});
                  setProjects([]);
                  setShowProfile(false);
                  setShowDashboard(false);
                  setShowProjects(false);
                  setShowAdminDashboard(false);
                  setActivityLog([]);
                  
                  // Clear localStorage
                  localStorage.removeItem('userData');
                  
                  if (userWasLoggedIn) {
                    showCustomMessage("Logged out successfully!");
                  }
                }}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="font-semibold">Logout</span>
              </button>
            </>
          )}
        </div>
      </nav>

      <div className="flex flex-grow relative z-10 gap-4 mx-4 my-4">
        {userData.email && (
          <aside className="w-80 rounded-3xl bg-white/80 backdrop-blur-xl p-6 ring-1 ring-gray-200/50 border border-white/20 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl blur-sm opacity-50"></div>
                <div className="relative h-8 w-8 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center">
                  <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Activity Feed</h3>
                <p className="text-xs text-gray-500">Recent actions</p>
              </div>
            </div>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {activityLog.length === 0 ? (
                <div className="text-center py-8">
                  <div className="h-12 w-12 mx-auto mb-3 rounded-2xl bg-gray-100 flex items-center justify-center">
                    <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-sm">No activity yet</p>
                  <p className="text-gray-400 text-xs">Your actions will appear here</p>
                </div>
              ) : (
                activityLog.map((msg, i) => (
                  <div key={i} className="group relative p-4 rounded-2xl bg-gradient-to-r from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200">
                    <div className="flex items-start gap-3">
                      <div className="h-2 w-2 rounded-full bg-emerald-500 mt-2 flex-shrink-0"></div>
                      <div className="flex-1">
                        <p className="text-sm text-gray-700 leading-relaxed">{msg}</p>
                        <p className="text-xs text-gray-400 mt-1">{new Date().toLocaleTimeString()}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </aside>
        )}

      {showAdminDashboard ? (
        <AdminDashboard userData={userData} />
      ) : showForecastResults ? (
          <main className="flex-1">
            <section className="mt-8 py-12 max-w-7xl mx-auto rounded-3xl shadow-2xl p-8 bg-white/80 backdrop-blur-xl ring-1 ring-gray-200/50 border border-white/20">
              {/* Header */}
              <div className="text-center mb-12">
                <div className="relative inline-block mb-6">
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full blur-lg opacity-75"></div>
                  <div className="relative w-16 h-16 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl">
                    <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                </div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-600 via-teal-600 to-lime-600 bg-clip-text text-transparent mb-4">
                  Project Created Successfully!
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                  Your AI-powered demand forecast has been generated. Review the material requirements below.
                </p>
              </div>

              {/* Project Input Details */}
              {currentForecastData && currentForecastData.projectDetails && (
                <div className="mb-12">
                  <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent mb-6 text-center">
                    Project Details
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Budget</h3>
                        <p className="text-lg font-bold text-gray-900">₹{currentForecastData.projectDetails.budget?.toLocaleString()}</p>
                      </div>
                    </div>
                    
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Location</h3>
                        <p className="text-lg font-bold text-gray-900">{currentForecastData.projectDetails.location}</p>
                      </div>
                    </div>
                    
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Tower Type</h3>
                        <p className="text-lg font-bold text-gray-900">{currentForecastData.projectDetails.towerType}</p>
                      </div>
                    </div>
                    
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Substation Type</h3>
                        <p className="text-lg font-bold text-gray-900">{currentForecastData.projectDetails.substationType}</p>
                      </div>
                    </div>
                    
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Geographic Conditions</h3>
                        <p className="text-lg font-bold text-gray-900">{currentForecastData.projectDetails.geo}</p>
                      </div>
                    </div>
                    
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Tax Structure</h3>
                        <p className="text-lg font-bold text-gray-900">{currentForecastData.projectDetails.taxes}</p>
                      </div>
                    </div>
                    
                    <div className="relative p-[1px] rounded-xl bg-gradient-to-tr from-blue-400/70 via-purple-500/70 to-indigo-500/70 transition-transform hover:scale-[1.02]">
                      <div className="bg-white/80 backdrop-blur-sm rounded-[11px] p-4 shadow-sm">
                        <h3 className="text-sm font-semibold text-gray-600 mb-1">Project Status</h3>
                        <p className="text-lg font-bold text-gray-900 capitalize">{currentForecastData.projectDetails.status}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Divider */}
              {currentForecastData && currentForecastData.projectDetails && currentForecastData.forecasts && (
                <div className="flex items-center justify-center mb-12">
                  <div className="flex-grow h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                  <div className="mx-6 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-semibold rounded-full shadow-lg">
                    AI Predictions
                  </div>
                  <div className="flex-grow h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                </div>
              )}

              {/* AI Forecast Results */}
              {currentForecastData && currentForecastData.forecasts && renderForecasts(currentForecastData.forecasts)}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center mt-12">
                {( !(userData.role === 'admin' && (userData.admin_level || '').toLowerCase() === 'central') ) && (
                <button
                  onClick={() => {
                    setShowForecastResults(false);
                    setShowDashboard(true);
                    setCurrentForecastData(null);
                  }}
                  className="px-8 py-4 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold shadow-lg hover:shadow-xl hover:from-emerald-700 hover:to-teal-700 transition-all duration-200 transform hover:-translate-y-1 flex items-center gap-3 justify-center"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  View All Projects
                </button>
                )}
                <button
                  onClick={() => {
                    if (userData.role === 'admin' && (userData.admin_level || '').toLowerCase() === 'central') {
                      showCustomMessage('Central admins cannot create projects.');
                      return;
                    }
                    setShowForecastResults(false);
                    setCurrentForecastData(null);
                  }}
                  className="px-8 py-4 rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold shadow-lg hover:shadow-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-200 transform hover:-translate-y-1 flex items-center gap-3 justify-center"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Create Another Project
                </button>
              </div>
            </section>
          </main>
      ) : showDashboard ? (
        <Dashboard projects={projects} goBack={() => setShowDashboard(false)} userData={userData} />
      ) : showProjects ? (
        <Dashboard projects={projects} goBack={() => setShowProjects(false)} showAllProjects={true} onProjectUpdate={loadUserProjects} userData={userData} />
        ) : showProfile ? (
          <main className="flex-1">
            <section className="mt-8 py-12 max-w-7xl mx-auto rounded-3xl shadow-2xl p-8 bg-white/80 backdrop-blur-xl ring-1 ring-gray-200/50 border border-white/20">
              {/* Profile Header */}
              <div className="text-center mb-12">
                <div className="relative inline-block mb-6">
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full blur-lg opacity-75"></div>
                  <div className="relative w-24 h-24 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl">
                    <svg className="h-12 w-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-green-500 rounded-full border-4 border-white flex items-center justify-center">
                    <svg className="h-4 w-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
                <h3 className="text-4xl font-bold mb-3 text-gray-900">{userData.name}</h3>
                <div className="flex items-center justify-center gap-2 mb-4">
                  <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                    userData.role === 'admin' 
                      ? 'bg-purple-100 text-purple-800 ring-1 ring-purple-300' 
                      : 'bg-blue-100 text-blue-800 ring-1 ring-blue-300'
                  }`}>
                    {userData.role === 'admin' ? '👑 Administrator' : '👤 Employee'}
                  </span>
                </div>
              </div>

              {/* Profile Details Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                {/* Full Name */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200 hover:shadow-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Full Name</span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900">{userData.fullname || userData.name}</p>
                </div>

                {/* Username */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200 hover:shadow-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Username</span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900">{userData.username || userData.email}</p>
                </div>

                {/* State */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200 hover:shadow-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">State</span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900">{userData.state || 'Not specified'}</p>
                </div>

                {/* Role */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200 hover:shadow-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-yellow-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Role</span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900 capitalize">{userData.role}</p>
                </div>

                {/* Member Since */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200 hover:shadow-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Member Since</span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900">
                    {userData.created_at ? new Date(userData.created_at).toLocaleDateString('en-US', { 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    }) : 'N/A'}
                  </p>
                </div>

                {/* User ID */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200/50 hover:border-emerald-200 transition-all duration-200 hover:shadow-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
                      <svg className="h-5 w-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                      </svg>
                    </div>
                    <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">User ID</span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900">#{userData.id}</p>
                </div>
              </div>

              {/* Statistics Section */}
              <div className="mb-8">
                <h4 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                  <svg className="h-6 w-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Account Statistics
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Total Projects */}
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200/50 hover:border-emerald-300 transition-all duration-200 hover:shadow-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
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
                  </div>

                  {/* Recent Activity */}
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200/50 hover:border-purple-300 transition-all duration-200 hover:shadow-lg">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 rounded-xl bg-purple-500 flex items-center justify-center">
                        <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-purple-600 uppercase tracking-wide">Recent Activity</p>
                        <p className="text-2xl font-bold text-gray-900">{activityLog.length}</p>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">Total logged activities</p>
                  </div>

                  {/* Last Login */}
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200/50 hover:border-blue-300 transition-all duration-200 hover:shadow-lg">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center">
                        <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">Last Login</p>
                        <p className="text-lg font-bold text-gray-900">
                          {userData.last_login ? new Date(userData.last_login).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          }) : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Back Button */}
              <div className="text-center">
                <button
                  onClick={() => setShowProfile(false)}
                  className="px-8 py-4 rounded-2xl bg-gradient-to-r from-gray-500 to-gray-600 text-white font-semibold shadow-lg hover:shadow-xl hover:from-gray-600 hover:to-gray-700 transition-all duration-200 transform hover:-translate-y-1 flex items-center gap-3 mx-auto"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                  Back to Dashboard
                </button>
              </div>
            </section>
          </main>
        ) : (
          <main className="flex-1">
            <section className="relative text-center py-20 rounded-3xl mb-8 overflow-hidden">
              <div className="absolute inset-0 -z-10 bg-gradient-to-br from-white via-emerald-50/50 to-teal-50/50 backdrop-blur-sm" />
              <div className="relative mx-auto max-w-4xl px-6">
                <h2 className="text-6xl font-black mb-6 bg-gradient-to-r from-gray-900 via-emerald-800 to-teal-800 bg-clip-text text-transparent leading-tight">
                  Material Demand Forecasting
                </h2>
                <p className="mt-4 text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed">
                  Leverage advanced AI to predict material requirements with unprecedented accuracy. 
                  Plan smarter, build faster, and optimize your supply chain.
                </p>
                {userData.email && (
                  <div className="flex justify-center flex-wrap gap-6">
                    {( !(userData.role === 'admin' && (userData.admin_level || '').toLowerCase() === 'central') ) && (
                    <button
                      className="group relative px-8 py-4 rounded-2xl bg-white border-2 border-gray-200 text-gray-900 font-bold shadow-lg hover:shadow-xl hover:border-emerald-300 transition-all duration-200 transform hover:-translate-y-1"
                      onClick={() => {
                        setShowForecastResults(false);
                        setCurrentForecastData(null);
                        // allow only non-central users
                        if (userData.role === 'admin' && (userData.admin_level || '').toLowerCase() === 'central') {
                          showCustomMessage('Central admins cannot create projects.');
                          return;
                        }
                        setModals({ ...modals, project: true });
                      }}
                    >
                      <span className="relative flex items-center gap-3">
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        Create New Project
                      </span>
                    </button>
                    )}
                    <button
                      className="px-8 py-4 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold shadow-lg hover:shadow-xl hover:from-emerald-700 hover:to-teal-700 transition-all duration-200 transform hover:-translate-y-1 flex items-center gap-3"
                      onClick={() => {
                        setShowProjects(true);
                        setShowDashboard(false);
                        setShowAdminDashboard(false);
                        setShowProfile(false);
                        setShowForecastResults(false);
                        setCurrentForecastData(null);
                        setModals({ ...modals, project: false, signup: false, login: false, projectDetails: false, verify2FA: false });
                      }}
                    >
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      My Projects
                    </button>
                  </div>
                )}
              </div>
            </section>

            {!userData.email && (
              <section className="mx-auto max-w-7xl px-6 -mt-8 relative z-10">
                <div className="w-full md:w-2/3 ml-auto p-6 rounded-3xl bg-white/80 backdrop-blur-xl ring-1 ring-gray-200/50 border border-white/20 shadow-2xl">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center">
                      <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900">Project Locations</h3>
                  </div>
                  <Map />
                </div>
              </section>
            )}
          </main>
        )}
      </div>

      {/* Custom Message Box */}
      {showMessage && (
        <div className="fixed bottom-6 right-6 z-[60] bg-white/95 backdrop-blur-xl text-gray-900 px-6 py-4 rounded-2xl shadow-2xl ring-1 ring-gray-200/50 border border-white/20 animate-fadeInUp max-w-sm">
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <p className="font-medium">{message}</p>
          </div>
        </div>
      )}

      {/* Modals would go here - simplified for now */}
      {modals.project && (
        <div className="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-white rounded-3xl p-8">
            <h3 className="text-2xl font-bold mb-6">Create New Project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <input name="budget" placeholder="Budget" className="w-full p-3 border rounded-xl" required />
              <select name="location" className="w-full p-3 border rounded-xl" required>
                <option value="">Select Location</option>
                {Object.values(stateMapping).flat().map((city) => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </select>
              <select name="towerType" className="w-full p-3 border rounded-xl" required>
                <option value="">Tower Type</option>
                <option value="230 kV">230 kV</option>
                <option value="400 kV">400 kV</option>
                <option value="765 kV">765 kV</option>
                <option value="1200 kV">1200 kV</option>
              </select>
              <select name="substationType" className="w-full p-3 border rounded-xl" required>
                <option value="">Substation Type</option>
                <option value="AIS (Air Insulated Substation)">AIS (Air Insulated Substation)</option>
                <option value="GIS (Gas Insulated Substation)">GIS (Gas Insulated Substation)</option>
                <option value="HVDC (High Voltage Direct Current)">HVDC (High Voltage Direct Current)</option>
                <option value="Hybrid Substation">Hybrid Substation</option>
                <option value="Mobile Substation">Mobile Substation</option>
                <option value="Switching Substation">Switching Substation</option>
                <option value="Transformer Substation">Transformer Substation</option>
                <option value="Converter Substation">Converter Substation</option>
              </select>
              <select name="geo" className="w-full p-3 border rounded-xl" required>
                <option value="">Geography</option>
                <option value="Urban">Urban</option>
                <option value="Semi-urban">Semi-urban</option>
                <option value="Industrial">Industrial</option>
                <option value="Hill">Hill</option>
                <option value="Forest">Forest</option>
                <option value="Desert">Desert</option>
                <option value="Coastal">Coastal</option>
              </select>
              <select name="taxes" className="w-full p-3 border rounded-xl" required>
                <option value="">Tax Structure</option>
                <option value="Standard">Standard</option>
                <option value="Reduced">Reduced</option>
                <option value="Exempt">Exempt</option>
              </select>
              <div className="flex gap-4">
                <button type="submit" className="flex-1 bg-emerald-500 text-white py-3 rounded-xl font-semibold">
                  Create Project
                </button>
                <button type="button" onClick={() => setModals({ ...modals, project: false })} className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-xl font-semibold">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modals.signup && (
        <div className="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-3xl p-8">
            <h3 className="text-2xl font-bold mb-6">Sign Up</h3>
            <form onSubmit={handleSignup} className="space-y-4">
              <input name="fullname" placeholder="Full Name" className="w-full p-3 border rounded-xl" required />
              <input name="email" placeholder="Username" className="w-full p-3 border rounded-xl" required />
              <input name="password" type="password" placeholder="Password" className="w-full p-3 border rounded-xl" required />
              <select name="role" className="w-full p-3 border rounded-xl" required onChange={(e)=>{ setSignupRole(e.target.value); setSignupAdminLevel(""); }}>
                <option value="">Select Role</option>
                <option value="admin">Admin</option>
                <option value="employee">Employee</option>
              </select>
              {signupRole === 'admin' && (
                <select name="admin_level" className="w-full p-3 border rounded-xl" required onChange={(e)=> setSignupAdminLevel(e.target.value)}>
                  <option value="">Admin Type</option>
                  <option value="state">State Admin</option>
                  <option value="central">Central Admin</option>
                </select>
              )}
              {(signupRole === 'employee' || (signupRole === 'admin' && signupAdminLevel === 'state')) && (
                <select name="state" className="w-full p-3 border rounded-xl" required>
                <option value="">Select State</option>
                {Object.keys(stateMapping).map((state) => (
                  <option key={state} value={state}>{state}</option>
                ))}
              </select>
              )}
              {signupError && (
                <div className="text-red-600 text-sm">{signupError}</div>
              )}
              <div className="flex gap-4">
                <button type="submit" className="flex-1 bg-emerald-500 text-white py-3 rounded-xl font-semibold">
                  Sign Up
                </button>
                <button type="button" onClick={() => setModals({ ...modals, signup: false })} className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-xl font-semibold">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modals.login && (
        <div className="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-3xl p-8">
            <h3 className="text-2xl font-bold mb-6">Login</h3>
            <form onSubmit={handleLogin} className="space-y-4">
              <input name="email" placeholder="Username" className="w-full p-3 border rounded-xl" required />
              <input name="password" type="password" placeholder="Password" className="w-full p-3 border rounded-xl" required />
              {loginError && (
                <div className="text-red-600 text-sm">{loginError}</div>
              )}
              <div className="flex gap-4">
                <button type="submit" className="flex-1 bg-emerald-500 text-white py-3 rounded-xl font-semibold">
                  Login
                </button>
                <button type="button" onClick={() => setModals({ ...modals, login: false })} className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-xl font-semibold">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

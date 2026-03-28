import { Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import { Briefcase, Users, Calendar, FileText, LayoutDashboard, MessageSquare } from "lucide-react";
import Jobs from "./pages/Jobs";
import Recruiters from "./pages/Recruiters";
import Applications from "./pages/Applications";
import CalendarPage from "./pages/Calendar";
import CV from "./pages/CV";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Recover from "./pages/Recover";
import Profile from "./pages/Profile";

const nav = [
  { to: "/", label: "Jobs", icon: Briefcase },
  { to: "/applications", label: "Track", icon: LayoutDashboard },
  { to: "/recruiters", label: "Recruiters", icon: Users },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/cv", label: "CV", icon: FileText },
  { to: "/profile", label: "Chat", icon: MessageSquare },
];

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("scout_token");
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/recover" element={<Recover />} />

      <Route
        path="/*"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      />
    </Routes>
  );
}

function AppShell() {
  return (
    <div className="flex flex-col md:flex-row h-screen bg-gray-950 text-gray-100">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-56 shrink-0 border-r border-gray-800 flex-col py-8 px-4 gap-1">
        <div className="mb-8 px-2">
          <h1 className="text-xl font-bold tracking-tight text-white">Scout</h1>
          <p className="text-xs text-gray-500 mt-0.5">Job search platform</p>
        </div>
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </aside>

      {/* Mobile top bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0">
        <h1 className="text-lg font-bold tracking-tight text-white">Scout</h1>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-auto pb-20 md:pb-0">
        <Routes>
          <Route path="/" element={<Jobs />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/recruiters" element={<Recruiters />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/cv" element={<CV />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </main>

      {/* Bottom nav — mobile only */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 flex justify-around py-2 z-50">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors ${
                isActive ? "text-indigo-400" : "text-gray-500"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

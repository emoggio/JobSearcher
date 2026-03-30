import { Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Briefcase, Users, Calendar, FileText, LayoutDashboard, MessageSquare, Zap, LogOut, Settings2 } from "lucide-react";
import { getHealth } from "./api";
import Jobs from "./pages/Jobs";
import Recruiters from "./pages/Recruiters";
import Applications from "./pages/Applications";
import CalendarPage from "./pages/Calendar";
import CV from "./pages/CV";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Recover from "./pages/Recover";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import FloatingChat from "./components/FloatingChat";

const nav = [
  { to: "/", label: "Jobs", icon: Briefcase },
  { to: "/applications", label: "Track", icon: LayoutDashboard },
  { to: "/recruiters", label: "Recruiters", icon: Users },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/cv", label: "CV", icon: FileText },
  { to: "/profile", label: "Profile", icon: MessageSquare },
  { to: "/settings", label: "Settings", icon: Settings2 },
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
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => getHealth().then((r) => r.data),
    staleTime: 30_000,
    retry: false,
  });
  const aiConnected = health?.ai_connected === true;

  return (
    <div className="flex flex-col md:flex-row h-screen bg-gray-950 text-gray-100">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-56 shrink-0 border-r border-gray-800 flex-col py-8 px-4 gap-1">
        <div className="mb-8 px-2">
          <h1 className="text-xl font-bold tracking-tight text-white">Scout</h1>
          <div className="flex items-center gap-1.5 mt-1">
            {aiConnected ? (
              <>
                <Zap size={10} className="text-emerald-400" />
                <p className="text-[10px] text-emerald-400 font-medium">AI-powered</p>
              </>
            ) : (
              <>
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-600" />
                <p className="text-[10px] text-yellow-600">No API key — basic mode</p>
              </>
            )}
          </div>
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
        <div className="mt-auto pt-4 border-t border-gray-800">
          <button
            onClick={() => { localStorage.removeItem("scout_token"); window.location.href = "/login"; }}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 w-full transition-colors"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold tracking-tight text-white">Scout</h1>
          {aiConnected && <Zap size={12} className="text-emerald-400" aria-label="AI connected" />}
        </div>
        <button
          onClick={() => { localStorage.removeItem("scout_token"); window.location.href = "/login"; }}
          className="text-gray-400 hover:text-white p-1"
          aria-label="Log out"
        >
          <LogOut size={18} />
        </button>
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
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>

      {/* Floating chat assistant — visible on all pages */}
      <FloatingChat />

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

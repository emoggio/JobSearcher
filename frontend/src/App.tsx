import { Routes, Route, NavLink } from "react-router-dom";
import { Briefcase, Users, Calendar, FileText, LayoutDashboard } from "lucide-react";
import Jobs from "./pages/Jobs";
import Recruiters from "./pages/Recruiters";
import Applications from "./pages/Applications";
import CalendarPage from "./pages/Calendar";
import CV from "./pages/CV";

const nav = [
  { to: "/", label: "Jobs", icon: Briefcase },
  { to: "/applications", label: "Applications", icon: LayoutDashboard },
  { to: "/recruiters", label: "Recruiters", icon: Users },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/cv", label: "CV", icon: FileText },
];

export default function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-56 border-r border-gray-800 flex flex-col py-8 px-4 gap-1">
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
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Jobs />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/recruiters" element={<Recruiters />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/cv" element={<CV />} />
        </Routes>
      </main>
    </div>
  );
}

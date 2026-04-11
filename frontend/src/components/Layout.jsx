import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Layout({ children }) {
  const { isAuthenticated, logout, userEmail } = useAuth();
  const nav = useNavigate();

  const linkCls = ({ isActive }) =>
    `px-3 py-2 rounded-lg text-sm font-medium ${isActive ? "bg-accent text-white" : "text-ink-700 hover:bg-slate-200"}`;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 py-3">
          <Link to="/" className="font-bold text-ink-950 tracking-tight">
            Handwritten Assessment
          </Link>
          <nav className="flex items-center gap-1">
            {isAuthenticated ? (
              <>
                <NavLink to="/upload" className={linkCls}>
                  Upload
                </NavLink>
                <NavLink to="/results" className={linkCls}>
                  Results
                </NavLink>
                <NavLink to="/feedback" className={linkCls}>
                  Feedback
                </NavLink>
                <NavLink to="/teacher" className={linkCls}>
                  Teacher
                </NavLink>
                <span className="text-xs text-slate-500 ml-2 max-w-[140px] truncate">{userEmail}</span>
                <button
                  type="button"
                  className="ml-2 text-sm text-red-600 hover:underline"
                  onClick={() => {
                    logout();
                    nav("/login");
                  }}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={linkCls}>
                  Login
                </NavLink>
                <NavLink to="/register" className={linkCls}>
                  Register
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">{children}</main>
    </div>
  );
}

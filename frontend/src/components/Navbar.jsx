import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link to="/" className="text-lg font-semibold text-slate-900">
          CaseArena
        </Link>
        {user && (
          <div className="flex items-center gap-4 text-sm">
            <Link to="/dashboard" className="text-slate-600 hover:text-slate-900">
              Dashboard
            </Link>
            <Link to="/repository" className="text-slate-600 hover:text-slate-900">
              Repository
            </Link>
            <Link to="/upload" className="text-slate-600 hover:text-slate-900">
              Upload
            </Link>
            <Link to="/profile" className="text-slate-600 hover:text-slate-900">
              Profile
            </Link>
            <button
              onClick={handleLogout}
              className="rounded-md border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

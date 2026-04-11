import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Home() {
  const { isAuthenticated } = useAuth();
  return (
    <div className="text-center py-12">
      <h1 className="text-4xl font-bold text-ink-950 mb-4 tracking-tight">Automated handwritten grading</h1>
      <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-8">
        Upload scans or PDFs, run OCR with preprocessing, and score answers with transformer embeddings plus keyword
        alignment—complete with feedback and teacher overrides.
      </p>
      <div className="flex justify-center gap-4">
        {isAuthenticated ? (
          <Link
            to="/upload"
            className="px-6 py-3 bg-accent text-white rounded-xl font-semibold hover:bg-accent-dim shadow-lg shadow-blue-500/20"
          >
            Upload assignment
          </Link>
        ) : (
          <>
            <Link
              to="/register"
              className="px-6 py-3 bg-accent text-white rounded-xl font-semibold hover:bg-accent-dim shadow-lg shadow-blue-500/20"
            >
              Get started
            </Link>
            <Link to="/login" className="px-6 py-3 border border-slate-300 rounded-xl font-semibold text-ink-700 hover:bg-slate-100">
              Sign in
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

export default function Sidebar({ title, items, active, onSelect }) {
  return (
    <aside className="w-64 bg-slate-900 text-white min-h-screen p-4">
      <h2 className="text-xl font-semibold mb-6">{title}</h2>
      <nav className="space-y-2">
        {items.map((item) => (
          <button
            key={item}
            className={`w-full text-left px-3 py-2 rounded ${
              active === item ? "bg-blue-600" : "bg-slate-800 hover:bg-slate-700"
            }`}
            onClick={() => onSelect(item)}
          >
            {item}
          </button>
        ))}
      </nav>
    </aside>
  );
}

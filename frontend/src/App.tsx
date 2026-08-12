import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import Overview from './pages/Overview';
import Users from './pages/Users';
import Mmm from './pages/Mmm';
import Growth from './pages/Growth';
import Report from './pages/Report';

const NAV = [
  { to: '/', label: '总览', icon: '📈', end: true },
  { to: '/users', label: '用户分层', icon: '👥' },
  { to: '/mmm', label: '营销组合 MMM', icon: '🎯' },
  { to: '/growth', label: '裂变增长', icon: '🌱' },
  { to: '/report', label: 'AI 报告', icon: '🤖' },
];

export default function App() {
  return (
    <div className="flex h-full min-h-screen">
      {/* 侧边栏 */}
      <aside className="fixed inset-y-0 left-0 z-20 flex w-60 flex-col border-r border-slate-800 bg-slate-900">
        <div className="flex items-center gap-3 px-5 py-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500 text-lg font-bold text-white">
            G
          </div>
          <div>
            <div className="text-sm font-semibold text-white">增长智能分析平台</div>
            <div className="text-[11px] text-slate-400">Growth Intelligence</div>
          </div>
        </div>
        <nav className="mt-2 flex-1 space-y-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? 'bg-indigo-500/15 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-5 text-[11px] leading-relaxed text-slate-500">
          <div>模拟数据 · 全模拟</div>
          <div>ODS → DWD → DWS → ADS</div>
          <div>React + FastAPI</div>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="ml-60 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/users" element={<Users />} />
            <Route path="/mmm" element={<Mmm />} />
            <Route path="/growth" element={<Growth />} />
            <Route path="/report" element={<Report />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

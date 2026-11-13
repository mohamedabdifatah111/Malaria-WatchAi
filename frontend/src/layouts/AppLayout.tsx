import {
  Activity, Bot, CloudSun, FileText, FlaskConical, LayoutDashboard, LogOut, Map, Menu, Microscope, Pill, Users, X,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Loading } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/map", label: "Surveillance map", icon: Map },
  { to: "/prevalence", label: "Prevalence", icon: Activity },
  { to: "/species", label: "Species", icon: Microscope },
  { to: "/environment", label: "Environment", icon: CloudSun },
  { to: "/population-risk", label: "Population at risk", icon: Users },
  { to: "/drug-efficacy", label: "Drug efficacy", icon: Pill },
  { to: "/resistance", label: "Resistance markers", icon: FlaskConical },
  { to: "/assistant", label: "AI assistant", icon: Bot },
  { to: "/briefs", label: "Surveillance briefs", icon: FileText },
];

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="space-y-0.5">
      {NAV.map(({ to, label, icon: Icon }) => (
        <li key={to}>
          <NavLink to={to} onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm ${isActive
                ? "bg-white/10 font-medium text-white"
                : "text-white/70 hover:bg-white/5 hover:text-white"}`}>
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function Brand() {
  return (
    <div className="px-3">
      <p className="text-base font-semibold tracking-tight text-white">MalariaWatchAI</p>
      <p className="text-[11px] text-white/55">Kenya · Tanzania · Ethiopia</p>
    </div>
  );
}

export function AppLayout() {
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="flex min-h-full">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col bg-navy-900 py-5 lg:flex" aria-label="Main navigation">
        <Brand />
        <nav className="mt-6 flex-1 px-2"><NavItems /></nav>
        <div className="px-2">
          <button type="button" onClick={logout}
            className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white">
            <LogOut className="h-4 w-4" aria-hidden /> Sign out
          </button>
          <p className="mt-3 px-3 text-[11px] leading-snug text-white/45">
            Surveillance decision support. Not for diagnosis or treatment.
          </p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-30 flex items-center justify-between bg-navy-900 px-4 py-3 lg:hidden">
          <p className="font-semibold text-white">MalariaWatchAI</p>
          <button type="button" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}
            onClick={() => setOpen((v) => !v)} className="rounded-md p-1.5 text-white hover:bg-white/10">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </header>
        {open && (
          <div className="fixed inset-0 z-20 bg-navy-950/40 lg:hidden" onClick={() => setOpen(false)}>
            <nav className="absolute left-0 top-[52px] h-[calc(100%-52px)] w-72 max-w-[85vw] overflow-y-auto bg-navy-900 p-2"
              aria-label="Main navigation" onClick={(e) => e.stopPropagation()}>
              <NavItems onNavigate={() => setOpen(false)} />
              <button type="button" onClick={logout}
                className="mt-2 flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-white/70 hover:bg-white/5">
                <LogOut className="h-4 w-4" aria-hidden /> Sign out
              </button>
            </nav>
          </div>
        )}

        <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Suspense fallback={<Loading label="Loading page..." />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}

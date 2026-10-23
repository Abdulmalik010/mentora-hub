import React from 'react';

interface SidebarProps {
  currentScreen: string;
  onNavigate: (screen: string) => void;
  upcomingCount?: number;
  streakDays?: number;
  onToggleViewMode: () => void;
  viewMode: 'phone' | 'desktop';
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  upcomingCount = 1,
  streakDays = 12,
  onToggleViewMode,
  viewMode
}) => {
  const navItems = [
    { id: 'home', label: 'Home Overview', icon: 'home', badge: null },
    { id: 'matched-experts', label: 'Faculty Directory', icon: 'school', badge: '8 Top Mentors' },
    { id: 'ai-chat', label: 'AI Academic Advisor', icon: 'auto_awesome', badge: 'Fast Stream' },
    { id: 'sessions', label: 'My Sessions', icon: 'calendar_month', badge: upcomingCount > 0 ? `${upcomingCount} upcoming` : null },
    { id: 'profile', label: 'Learner Profile', icon: 'person', badge: null }
  ];

  return (
    <aside className="w-64 bg-[#ffffff] border-r border-[#e2e8f0] flex flex-col justify-between h-screen sticky top-0 shrink-0 select-none z-30">
      {/* Top Branding */}
      <div className="flex flex-col">
        <div className="p-5 border-b border-[#f1f5f9] flex items-center justify-between">
          <div
            onClick={() => onNavigate('home')}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-9 h-9 rounded-xl bg-[#001428] flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined text-[20px]">school</span>
            </div>
            <div>
              <span className="text-[20px] font-extrabold text-[#001428] tracking-tight block leading-none">
                Mentora
              </span>
              <span className="text-[10px] text-[#a73a00] font-bold uppercase tracking-wider block mt-0.5">
                Academic Hub
              </span>
            </div>
          </div>

          <span className="px-2 py-0.5 rounded-full bg-[#e5eeff] text-[#0f2942] text-[10px] font-bold">
            ₦ NGN
          </span>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1.5">
          {navItems.map((item) => {
            const isActive =
              currentScreen === item.id ||
              (item.id === 'matched-experts' && currentScreen === 'expert-profile') ||
              (item.id === 'sessions' && ['booking', 'payment', 'confirmation'].includes(currentScreen));

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-[13px] font-bold transition-all ${
                  isActive
                    ? 'bg-[#001428] text-white shadow-sm'
                    : 'text-[#43474d] hover:bg-[#eff4ff] hover:text-[#001428]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`material-symbols-outlined text-[20px] ${
                      isActive ? 'text-[#ffdbce]' : 'text-[#74777e]'
                    }`}
                  >
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      isActive
                        ? 'bg-[#ffffff]/20 text-white'
                        : item.badge.includes('upcoming')
                        ? 'bg-[#fd651e] text-white animate-pulse'
                        : 'bg-[#ffdbce] text-[#370e00]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* View Mode Switch Pill */}
        <div className="px-4 py-2">
          <div className="bg-[#f8f9ff] border border-[#d1e4ff]/70 rounded-xl p-2.5 flex flex-col gap-2">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#001428]">
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] text-[#a73a00]">devices</span>
                <span>Layout Mode</span>
              </span>
              <span className="text-[#a73a00] uppercase font-bold text-[10px]">
                {viewMode === 'desktop' ? 'Desktop Full' : 'Phone Frame'}
              </span>
            </div>
            <button
              type="button"
              onClick={onToggleViewMode}
              className="w-full py-1.5 px-2.5 rounded-lg bg-[#ffffff] hover:bg-[#e5eeff] text-[#001428] text-[11px] font-bold shadow-2xs border border-[#e2e8f0] flex items-center justify-center gap-1.5 active:scale-95 transition-all"
            >
              <span className="material-symbols-outlined text-[14px]">
                {viewMode === 'desktop' ? 'smartphone' : 'desktop_windows'}
              </span>
              <span>{viewMode === 'desktop' ? 'Switch to Phone View' : 'Switch to Desktop View'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Profile & Streak Section */}
      <div className="p-3 border-t border-[#f1f5f9] flex flex-col gap-2 bg-[#f8f9ff]/50">
        <div className="flex items-center justify-between px-2 py-1 bg-[#ffdbce]/40 rounded-xl">
          <div className="flex items-center gap-1.5 text-[#370e00] text-[11px] font-bold">
            <span
              className="material-symbols-outlined text-[16px] text-[#a73a00]"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              local_fire_department
            </span>
            <span>{streakDays} Day Learning Streak</span>
          </div>
          <span className="text-[10px] text-[#a73a00] font-bold">Top 5%</span>
        </div>

        <div
          onClick={() => onNavigate('profile')}
          className="flex items-center gap-3 p-2 rounded-xl hover:bg-[#e5eeff] cursor-pointer transition-colors"
        >
          <img
            alt="Elena Rostova"
            className="w-10 h-10 rounded-xl object-cover ring-2 ring-[#d1e4ff]"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuA2VTTxi1zoK5YzJ7C2Hl0DTEQPPfygc806vetOKMVnW6jxM4hDr2fX3Q8vWqEh2fYXQyhimiJjMW7Vvs5HO7p9coq6pCqKV2Ba6yzywodQE0hEze0F2lRWzDOum2eLQVV-by-mWO4tdRlLdpkWCwOXD_oC4Dc3W1rX1ra9cJTmN9sLNBocY5MOAvqIKf64EPeMQBGG0jewKa0oFJ90uafmn0vLhJJPvnEX4hJfh5kUPF6b2h_Ukcbv"
          />
          <div className="flex flex-col min-w-0">
            <span className="text-[13px] font-bold text-[#001428] truncate">Elena Rostova</span>
            <span className="text-[11px] text-[#74777e] truncate">PhD Track • Cambridge</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

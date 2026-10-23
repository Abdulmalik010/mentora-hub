import React from 'react';

interface BottomNavProps {
  currentScreen: string;
  onNavigate: (screen: string) => void;
  upcomingCount?: number;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  currentScreen,
  onNavigate,
  upcomingCount = 1
}) => {
  const tabs = [
    {
      id: 'home',
      label: 'Home',
      icon: 'home',
      isDefault: true
    },
    {
      id: 'matched-experts',
      label: 'Experts',
      icon: 'explore'
    },
    {
      id: 'ai-chat',
      label: 'AI Chat',
      icon: 'auto_awesome'
    },
    {
      id: 'sessions',
      label: 'Sessions',
      icon: 'event_available',
      badge: upcomingCount > 0 ? upcomingCount : undefined
    },
    {
      id: 'profile',
      label: 'Profile',
      icon: 'person'
    }
  ];

  return (
    <nav
      className="fixed bottom-0 inset-x-0 w-full z-50 pb-safe bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_-2px_12px_rgba(15,41,66,0.05)] border-t border-[#e2e8f0]/60"
      aria-label="Main Navigation"
    >
      <div className="flex justify-around items-center h-16 max-w-lg mx-auto px-1">
        {tabs.map((tab) => {
          const isActive = currentScreen === tab.id || (tab.id === 'matched-experts' && currentScreen === 'experts');

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onNavigate(tab.id)}
              className={`flex-1 flex flex-col items-center justify-center min-h-[44px] min-w-[44px] py-1 transition-all duration-200 group relative ${
                isActive ? 'text-[#a73a00] font-semibold' : 'text-[#43474d] hover:text-[#001428]'
              }`}
            >
              <div className="relative flex items-center justify-center">
                <span
                  className="material-symbols-outlined text-[24px] group-hover:scale-105 transition-transform"
                  style={{
                    fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0"
                  }}
                >
                  {tab.icon}
                </span>
                {tab.badge && (
                  <span className="absolute -top-1 -right-2 w-4 h-4 bg-[#fd651e] text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-xs">
                    {tab.badge}
                  </span>
                )}
              </div>
              <span className={`text-[11px] mt-0.5 tracking-tight ${isActive ? 'font-bold text-[#a73a00]' : 'font-medium'}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

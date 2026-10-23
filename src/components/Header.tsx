import React from 'react';

interface HeaderProps {
  currentScreen: string;
  onNavigate: (screen: string) => void;
  onOpenNotifications: () => void;
  onBack?: () => void;
  title?: string;
  subtitle?: string;
  showStepIndicator?: boolean;
  stepNumber?: number; // 1, 2, or 3
  isBookmarked?: boolean;
  onToggleBookmark?: () => void;
  onShare?: () => void;
  viewMode?: 'phone' | 'desktop';
  onToggleViewMode?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentScreen,
  onNavigate,
  onOpenNotifications,
  onBack,
  title,
  subtitle,
  showStepIndicator,
  stepNumber = 1,
  isBookmarked,
  onToggleBookmark,
  onShare,
  viewMode = 'phone',
  onToggleViewMode
}) => {
  const renderViewModeToggle = () => {
    if (!onToggleViewMode) return null;
    return (
      <button
        type="button"
        onClick={onToggleViewMode}
        title={viewMode === 'desktop' ? 'Switch to Phone View' : 'Switch to Desktop View'}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#e5eeff] hover:bg-[#dce9ff] text-[#001428] text-[11px] font-bold shadow-2xs border border-[#d1e4ff] active:scale-95 transition-all"
      >
        <span className="material-symbols-outlined text-[15px] text-[#a73a00]">
          {viewMode === 'desktop' ? 'smartphone' : 'desktop_windows'}
        </span>
        <span className="hidden sm:inline">
          {viewMode === 'desktop' ? 'Phone view' : 'Desktop view'}
        </span>
        <span className="sm:hidden">
          {viewMode === 'desktop' ? 'Phone' : 'Desktop'}
        </span>
      </button>
    );
  };

  // If it's a detail / checkout / booking screen with custom header
  if (['booking', 'payment', 'confirmation'].includes(currentScreen)) {
    return (
      <header className="sticky top-0 inset-x-0 w-full z-40 bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] border-b border-[#e2e8f0]/60">
        <div className="h-24 px-4 flex flex-col justify-between py-1.5 max-w-5xl mx-auto">
          <div className="flex items-center justify-between w-full">
            <button
              type="button"
              aria-label="Go back"
              onClick={onBack}
              className="min-w-[44px] min-h-[44px] flex items-center justify-center -ml-2 rounded-full text-[#0b1c30] hover:bg-[#e5eeff] active:scale-95 transition-all"
            >
              <span className="material-symbols-outlined text-[22px]">arrow_back</span>
            </button>
            <div className="flex-1 text-center px-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#a73a00] block leading-none mb-0.5">
                Mentora Session
              </span>
              <h1 className="text-[18px] font-bold text-[#0b1c30] truncate">
                {title || (currentScreen === 'booking' ? 'Schedule Mentorship' : currentScreen === 'payment' ? 'Payment Method' : 'Booking Confirmation')}
              </h1>
            </div>
            <div className="flex items-center gap-2">
              {renderViewModeToggle()}
              <button
                type="button"
                onClick={() => onNavigate('profile')}
                className="w-8 h-8 rounded-full bg-[#001428] flex items-center justify-center shadow-sm text-white"
                aria-label="Profile"
              >
                <span className="material-symbols-outlined text-[18px]">person</span>
              </button>
            </div>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center justify-center gap-2 pb-1">
            <div className={`flex items-center gap-1.5 ${stepNumber >= 1 ? 'opacity-100' : 'opacity-60'}`}>
              <span className={`w-2 h-2 rounded-full ${stepNumber >= 1 ? 'bg-[#001428]' : 'bg-[#c3c6ce]'}`}></span>
              <span className={`text-[11px] font-semibold ${stepNumber >= 1 ? 'text-[#001428] font-bold' : 'text-[#43474d]'}`}>
                1. Schedule
              </span>
            </div>
            <span className="w-4 h-0.5 bg-[#c3c6ce]/40 rounded-full"></span>
            <div className={`flex items-center gap-1.5 ${stepNumber >= 2 ? 'opacity-100' : 'opacity-60'}`}>
              <span className={`w-2 h-2 rounded-full ${stepNumber >= 2 ? 'bg-[#001428]' : 'bg-[#c3c6ce]'}`}></span>
              <span className={`text-[11px] font-semibold ${stepNumber >= 2 ? 'text-[#001428] font-bold' : 'text-[#43474d]'}`}>
                2. Payment
              </span>
            </div>
            <span className="w-4 h-0.5 bg-[#c3c6ce]/40 rounded-full"></span>
            <div className={`flex items-center gap-1.5 ${stepNumber >= 3 ? 'opacity-100' : 'opacity-60'}`}>
              <span className={`w-2 h-2 rounded-full ${stepNumber >= 3 ? 'bg-[#001428]' : 'bg-[#c3c6ce]'}`}></span>
              <span className={`text-[11px] font-semibold ${stepNumber >= 3 ? 'text-[#001428] font-bold' : 'text-[#43474d]'}`}>
                3. Confirm
              </span>
            </div>
          </div>
        </div>
      </header>
    );
  }

  // Expert Profile Header
  if (currentScreen === 'expert-profile') {
    return (
      <header className="sticky top-0 inset-x-0 z-40 bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] pt-safe border-b border-[#e2e8f0]/60">
        <div className="h-16 px-4 flex items-center justify-between max-w-5xl mx-auto">
          <button
            type="button"
            aria-label="Go back"
            onClick={onBack}
            className="min-w-[44px] min-h-[44px] flex items-center justify-center -ml-2 text-[#001428] hover:text-[#0f2942] transition-colors"
          >
            <span className="material-symbols-outlined text-[24px]">arrow_back</span>
          </button>
          <h1 className="text-[18px] font-bold text-[#001428] tracking-tight truncate max-w-[200px]">
            {title || 'Mentora Expert Profile'}
          </h1>
          <div className="flex items-center gap-2">
            {renderViewModeToggle()}
            <button
              type="button"
              aria-label="Bookmark Expert"
              onClick={onToggleBookmark}
              className={`min-w-[36px] min-h-[36px] flex items-center justify-center rounded-full transition-colors ${
                isBookmarked ? 'text-[#a73a00]' : 'text-[#43474d] hover:text-[#001428]'
              }`}
            >
              <span className="material-symbols-outlined text-[22px]">
                {isBookmarked ? 'bookmark' : 'bookmark_border'}
              </span>
            </button>
            <button
              type="button"
              aria-label="Share Profile"
              onClick={onShare}
              className="min-w-[36px] min-h-[36px] flex items-center justify-center text-[#43474d] hover:text-[#001428] transition-colors"
            >
              <span className="material-symbols-outlined text-[22px]">share</span>
            </button>
          </div>
        </div>
      </header>
    );
  }

  // Default Header for Home, Experts, AI Chat, Sessions, Profile
  return (
    <header className="sticky top-0 w-full z-40 pt-safe bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] border-b border-[#e2e8f0]/60">
      <div className="h-16 px-4 flex items-center justify-between max-w-5xl mx-auto">
        <div
          onClick={() => onNavigate('home')}
          className="flex items-center gap-2 cursor-pointer select-none"
        >
          <div className="w-8 h-8 rounded-xl bg-[#001428] flex items-center justify-center text-white shadow-sm">
            <span className="material-symbols-outlined text-[18px]">school</span>
          </div>
          <span className="text-[20px] font-bold text-[#0f2942] tracking-tight">Mentora</span>
          <span className="hidden sm:inline text-[11px] font-semibold text-[#a73a00] bg-[#ffdbce] px-2 py-0.5 rounded-full ml-1">
            Academic Hub
          </span>
        </div>

        <div className="flex items-center gap-2">
          {renderViewModeToggle()}

          <button
            type="button"
            aria-label="Notifications"
            onClick={onOpenNotifications}
            className="w-9 h-9 flex items-center justify-center rounded-full text-[#43474d] hover:text-[#0f2942] hover:bg-[#e5eeff] transition-colors relative"
          >
            <span className="material-symbols-outlined text-[22px]">notifications</span>
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#fd651e] animate-pulse"></span>
          </button>
          <button
            type="button"
            onClick={() => onNavigate('profile')}
            className="w-9 h-9 flex items-center justify-center rounded-full transition-transform active:scale-95"
            aria-label="Profile"
          >
            <img
              alt="Elena Rostova Profile"
              className="w-8 h-8 rounded-full object-cover ring-2 ring-[#e5eeff]"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuA2VTTxi1zoK5YzJ7C2Hl0DTEQPPfygc806vetOKMVnW6jxM4hDr2fX3Q8vWqEh2fYXQyhimiJjMW7Vvs5HO7p9coq6pCqKV2Ba6yzywodQE0hEze0F2lRWzDOum2eLQVV-by-mWO4tdRlLdpkWCwOXD_oC4Dc3W1rX1ra9cJTmN9sLNBocY5MOAvqIKf64EPeMQBGG0jewKa0oFJ90uafmn0vLhJJPvnEX4hJfh5kUPF6b2h_Ukcbv"
            />
          </button>
        </div>
      </div>
    </header>
  );
};

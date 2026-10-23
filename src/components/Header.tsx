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
  onShare
}) => {
  // If it's a detail / checkout / booking screen with custom header
  if (['booking', 'payment', 'confirmation'].includes(currentScreen)) {
    return (
      <header className="fixed top-0 inset-x-0 w-full z-50 pt-safe bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] border-b border-[#e2e8f0]/60">
        <div className="h-24 px-4 flex flex-col justify-between py-1.5 max-w-lg mx-auto">
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
            <div className="min-w-[44px] min-h-[44px] flex items-center justify-end">
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
      <header className="fixed top-0 inset-x-0 z-50 bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] pt-safe border-b border-[#e2e8f0]/60">
        <div className="h-16 px-4 flex items-center justify-between max-w-lg mx-auto">
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
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Bookmark Expert"
              onClick={onToggleBookmark}
              className={`min-w-[40px] min-h-[40px] flex items-center justify-center rounded-full transition-colors ${
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
              className="min-w-[40px] min-h-[40px] flex items-center justify-center text-[#43474d] hover:text-[#001428] transition-colors"
            >
              <span className="material-symbols-outlined text-[22px]">share</span>
            </button>
          </div>
        </div>
      </header>
    );
  }

  // Onboarding Header
  if (currentScreen === 'onboarding') {
    return (
      <header className="fixed top-0 inset-x-0 z-50 bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] pt-safe border-b border-[#e2e8f0]/60">
        <div className="h-16 px-4 flex items-center justify-between max-w-lg mx-auto">
          <div className="flex items-center gap-2">
            {onBack && (
              <button
                type="button"
                aria-label="Go back"
                onClick={onBack}
                className="min-w-[44px] min-h-[44px] flex items-center justify-center -ml-2 text-[#0f2942] hover:text-[#001428] transition-colors"
              >
                <span className="material-symbols-outlined text-[24px]">arrow_back</span>
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[#0f2942] flex items-center justify-center text-white">
                <span className="material-symbols-outlined text-[16px]">school</span>
              </div>
              <span className="text-[20px] font-bold text-[#001428] tracking-tight">Mentora</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-end">
              <span className="text-[11px] text-[#43474d] font-medium">Personalize Experience</span>
              <div className="w-16 h-1.5 bg-[#e5eeff] rounded-full overflow-hidden mt-1">
                <div className="h-full bg-[#fd651e] rounded-full w-1/2"></div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('profile')}
              className="w-8 h-8 rounded-full bg-[#001428] flex items-center justify-center"
              aria-label="Profile"
            >
              <span className="material-symbols-outlined text-white text-[18px]">person</span>
            </button>
          </div>
        </div>
      </header>
    );
  }

  // Default Header for Home, Experts, AI Chat, Sessions, Profile
  return (
    <header className="fixed top-0 w-full z-50 pt-safe bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(15,41,66,0.04)] border-b border-[#e2e8f0]/60">
      <div className="h-16 px-4 flex items-center justify-between max-w-lg mx-auto">
        <div
          onClick={() => onNavigate('home')}
          className="flex items-center gap-2 cursor-pointer select-none"
        >
          <div className="w-8 h-8 rounded-xl bg-[#001428] flex items-center justify-center text-white shadow-sm">
            <span className="material-symbols-outlined text-[18px]">school</span>
          </div>
          <span className="text-[20px] font-bold text-[#0f2942] tracking-tight">Mentora</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Notifications"
            onClick={onOpenNotifications}
            className="w-10 h-10 flex items-center justify-center rounded-full text-[#43474d] hover:text-[#0f2942] hover:bg-[#e5eeff] transition-colors relative"
          >
            <span className="material-symbols-outlined text-[24px]">notifications</span>
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#fd651e] animate-pulse"></span>
          </button>
          <button
            type="button"
            onClick={() => onNavigate('profile')}
            className="w-10 h-10 flex items-center justify-center rounded-full transition-transform active:scale-95"
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

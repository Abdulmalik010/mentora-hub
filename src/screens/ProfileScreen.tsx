import React from 'react';
import { Expert } from '../data/expertsData';

interface ProfileScreenProps {
  onRestartOnboarding: () => void;
  onSelectExpert: (expert: Expert) => void;
  academicLevel: string;
  interests: string[];
  bookmarkedExperts: Expert[];
}

export const ProfileScreen: React.FC<ProfileScreenProps> = ({
  onRestartOnboarding,
  onSelectExpert,
  academicLevel,
  interests,
  bookmarkedExperts
}) => {
  return (
    <main className="flex flex-col relative w-full pt-18 pb-28 bg-[#f8f9ff] flex-1 min-h-screen max-w-lg mx-auto">
      <div className="flex flex-col w-full px-4 space-y-4">
        {/* Profile Card */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3">
          <div className="flex items-center gap-3.5">
            <div className="relative shrink-0">
              <img
                className="w-16 h-16 rounded-full object-cover ring-3 ring-[#dce9ff]"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA2VTTxi1zoK5YzJ7C2Hl0DTEQPPfygc806vetOKMVnW6jxM4hDr2fX3Q8vWqEh2fYXQyhimiJjMW7Vvs5HO7p9coq6pCqKV2Ba6yzywodQE0hEze0F2lRWzDOum2eLQVV-by-mWO4tdRlLdpkWCwOXD_oC4Dc3W1rX1ra9cJTmN9sLNBocY5MOAvqIKf64EPeMQBGG0jewKa0oFJ90uafmn0vLhJJPvnEX4hJfh5kUPF6b2h_Ukcbv"
                alt="Elena Rostova"
              />
              <span className="absolute bottom-0 right-0 w-4 h-4 bg-emerald-500 rounded-full ring-2 ring-white"></span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <h2 className="text-[18px] font-bold text-[#001428] truncate">Elena Rostova</h2>
                <span className="material-symbols-outlined text-[16px] text-emerald-600" style={{ fontVariationSettings: "'FILL' 1" }}>
                  verified
                </span>
              </div>
              <p className="text-[13px] text-[#43474d] truncate">
                {academicLevel} Candidate · Cambridge University
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2 py-0.5 rounded-full bg-[#ffdbce] text-[#7f2b00] text-[10px] font-bold uppercase tracking-wide">
                  12-Day Streak 🔥
                </span>
                <span className="text-[11px] text-[#74777e]">elena.rostova@cam.ac.uk</span>
              </div>
            </div>
          </div>
        </section>

        {/* Academic Profile Details */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[15px] font-bold text-[#001428]">Current Academic Track</h3>
            <button
              type="button"
              onClick={onRestartOnboarding}
              className="text-[12px] font-bold text-[#a73a00] hover:underline flex items-center gap-1"
            >
              <span>Edit Track</span>
              <span className="material-symbols-outlined text-[14px]">edit</span>
            </button>
          </div>

          <div className="bg-[#eff4ff] p-3 rounded-xl border border-[#d1e4ff]/60 flex items-center justify-between">
            <div>
              <span className="text-[10px] text-[#74777e] uppercase font-bold block">Degree Stage</span>
              <span className="text-[14px] font-bold text-[#001428]">{academicLevel}</span>
            </div>
            <span className="px-2.5 py-1 rounded-full bg-[#d1e4ff] text-[#011d35] text-[11px] font-bold">
              Active Doctoral Candidate
            </span>
          </div>

          <div className="space-y-1.5 pt-1">
            <span className="text-[11px] text-[#74777e] uppercase font-bold tracking-wider">
              Selected Disciplines & Frontiers:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {interests.map((it) => (
                <span
                  key={it}
                  className="px-2.5 py-1 rounded-full bg-[#e5eeff] text-[#001428] text-[11px] font-semibold"
                >
                  {it}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* Institutional Subsidy Status */}
        <section className="bg-gradient-to-r from-[#001428] to-[#0f2942] rounded-2xl p-4 text-white shadow-md flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-[#ffdbce] text-[22px]">workspace_premium</span>
            </div>
            <div>
              <span className="text-[10px] text-[#ffdbce] uppercase font-bold tracking-wide">
                Institutional Grant Active
              </span>
              <p className="text-[14px] font-bold text-white">Mentora Doctoral Co-Pay</p>
              <p className="text-[11px] text-[#adc6ff]">$15.00 reduction automatically credited on eligible faculty bookings.</p>
            </div>
          </div>
        </section>

        {/* Saved Scholars */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#a73a00] text-[20px]">bookmark</span>
              <h3 className="text-[15px] font-bold text-[#001428]">
                Saved Faculty ({bookmarkedExperts.length})
              </h3>
            </div>
          </div>

          {bookmarkedExperts.length === 0 ? (
            <p className="text-[12px] text-[#74777e] italic">
              No faculty bookmarked yet. Tap the bookmark icon on any faculty card to save them here for rapid booking.
            </p>
          ) : (
            <div className="space-y-2">
              {bookmarkedExperts.map((exp) => (
                <div
                  key={exp.id}
                  onClick={() => onSelectExpert(exp)}
                  className="flex items-center justify-between p-2.5 rounded-xl bg-[#eff4ff] hover:bg-[#dce9ff] cursor-pointer transition-colors border border-[#d1e4ff]/50"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <img
                      src={exp.avatarUrl}
                      alt={exp.name}
                      className="w-10 h-10 rounded-xl object-cover ring-1 ring-white"
                    />
                    <div className="min-w-0">
                      <p className="text-[13px] font-bold text-[#001428] truncate">{exp.name}</p>
                      <p className="text-[11px] text-[#43474d] truncate">{exp.institution}</p>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-[18px] text-[#a73a00]">arrow_forward</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Settings & Reset */}
        <section className="space-y-2 pt-2">
          <button
            type="button"
            onClick={onRestartOnboarding}
            className="w-full py-3 px-4 rounded-xl bg-[#eff4ff] hover:bg-[#dce9ff] text-[#001428] text-[13px] font-bold flex items-center justify-center gap-2 border border-[#d1e4ff] transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">tune</span>
            <span>Retune Onboarding Preferences</span>
          </button>
        </section>
      </div>
    </main>
  );
};

import React, { useState } from 'react';
import { Expert, formatNaira } from '../data/expertsData';

interface ExpertsScreenProps {
  onNavigate: (screen: string) => void;
  onSelectExpert: (expert: Expert) => void;
  onBookExpert: (expert: Expert) => void;
  onOpenDeepScout: () => void;
  experts: Expert[];
  bookmarkedIds: string[];
  onToggleBookmark: (expertId: string) => void;
}

export const ExpertsScreen: React.FC<ExpertsScreenProps> = ({
  onNavigate,
  onSelectExpert,
  onBookExpert,
  onOpenDeepScout,
  experts,
  bookmarkedIds,
  onToggleBookmark
}) => {
  const [activeDomainFilter, setActiveDomainFilter] = useState('All Domains');
  const [sortBy, setSortBy] = useState('best-match');
  const [searchQuery, setSearchQuery] = useState('Quantum Fault Tolerance & Surface Codes');
  const [isEditingQuery, setIsEditingQuery] = useState(false);

  // Filter logic
  let filtered = [...experts];

  if (activeDomainFilter === 'MIT / Harvard') {
    filtered = filtered.filter(
      (e) => e.institution.includes('MIT') || e.institution.includes('Harvard')
    );
  } else if (activeDomainFilter === 'Under ₦15,000') {
    filtered = filtered.filter((e) => e.hourlyRate <= 15000);
  } else if (activeDomainFilter === 'Available This Week') {
    filtered = filtered.filter((e) => e.nextSlotDate.includes('Wed') || e.nextSlotDate.includes('Thu') || e.nextSlotDate.includes('Fri'));
  }

  // Sort logic
  if (sortBy === 'best-match') {
    filtered.sort((a, b) => b.matchScore - a.matchScore);
  } else if (sortBy === 'highest-cited') {
    filtered.sort((a, b) => b.papersCited - a.papersCited);
  } else if (sortBy === 'rating') {
    filtered.sort((a, b) => b.rating - a.rating);
  } else if (sortBy === 'price-low') {
    filtered.sort((a, b) => a.hourlyRate - b.hourlyRate);
  }

  return (
    <main className="flex flex-col relative w-full pt-4 pb-24 bg-[#f8f9ff] flex-1 min-h-screen max-w-6xl mx-auto">
      <div className="flex flex-col w-full">
        {/* Query & Context Banner */}
        <div className="px-4 pt-4 pb-2 flex flex-col gap-3">
          <div className="bg-[#eff4ff] rounded-2xl p-4 shadow-sm relative overflow-hidden border border-[#d1e4ff]/70">
            <div className="absolute -right-6 -bottom-6 w-24 h-24 rounded-full bg-[#ffdbce]/30 pointer-events-none blur-xl"></div>
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#ffdbce]/60 text-[#370e00] text-[11px] font-bold">
                <span
                  className="material-symbols-outlined text-[15px] text-[#a73a00]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  auto_awesome
                </span>
                <span>Semantic Match</span>
              </div>
              <button
                type="button"
                onClick={() => setIsEditingQuery(!isEditingQuery)}
                className="inline-flex items-center gap-1 text-[12px] font-bold text-[#a73a00] hover:text-[#571a00] transition-colors py-1 px-2 rounded-lg hover:bg-[#ffdbce]/30 active:scale-95"
              >
                <span className="material-symbols-outlined text-[16px]">tune</span>
                <span>{isEditingQuery ? 'Done' : 'Edit Query'}</span>
              </button>
            </div>

            {isEditingQuery ? (
              <div className="mt-1">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full p-2 bg-white rounded-xl border border-[#b0c9e8] text-[15px] font-bold text-[#0b1c30] focus:outline-none focus:border-[#a73a00]"
                  placeholder="Enter custom research frontier or topic..."
                />
              </div>
            ) : (
              <div className="text-[20px] font-bold text-[#0b1c30] leading-tight tracking-tight pr-4">
                {searchQuery}
              </div>
            )}

            <p className="text-[12px] text-[#43474d] mt-1 flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-[#fd651e]"></span>
              Aggregating cross-institutional literature & verified laboratory leads
            </p>
          </div>

          {/* Results metadata + sort selector */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-baseline gap-1.5">
              <span className="text-[20px] font-bold text-[#001428]">{filtered.length}</span>
              <span className="text-[13px] text-[#43474d]">Faculty & Fellows available</span>
            </div>
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="appearance-none bg-[#ffffff] text-[#0b1c30] text-[12px] font-bold py-1.5 pl-3 pr-7 rounded-xl shadow-xs border border-[#e2e8f0] focus:outline-none cursor-pointer"
              >
                <option value="best-match">Best Match (98%)</option>
                <option value="highest-cited">Highest Cited</option>
                <option value="rating">Rating (High-Low)</option>
                <option value="price-low">Price (Low-High)</option>
              </select>
              <span className="material-symbols-outlined pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[18px] text-[#43474d]">
                expand_more
              </span>
            </div>
          </div>

          {/* Quick filter chips horizontal scroll */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-4 px-4 no-scrollbar">
            {['All Domains', 'MIT / Harvard', 'Virtual 1:1', 'Under ₦15,000', 'Available This Week'].map((f) => {
              const isSelected = activeDomainFilter === f;
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => setActiveDomainFilter(f)}
                  className={`shrink-0 px-3.5 py-1.5 rounded-full text-[12px] font-bold shadow-xs transition-all flex items-center gap-1 active:scale-95 ${
                    isSelected
                      ? 'bg-[#0f2942] text-white'
                      : 'bg-[#ffffff] text-[#43474d] hover:text-[#0b1c30] border border-[#e2e8f0]'
                  }`}
                >
                  {f === 'Virtual 1:1' && <span className="w-1.5 h-1.5 rounded-full bg-[#a73a00]"></span>}
                  <span>{f}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Expert Cards Feed in Multi-Column Grid */}
        <div className="px-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 py-2">
          {filtered.map((mentor) => {
            const isBookmarked = bookmarkedIds.includes(mentor.id);
            return (
              <div
                key={mentor.id}
                className="bg-[#ffffff] rounded-2xl p-4 shadow-md border border-[#e2e8f0]/80 relative overflow-hidden flex flex-col gap-3 group"
              >
                {/* Glow ambient top corner for top match */}
                {mentor.matchScore >= 95 && (
                  <div className="absolute -top-12 -right-12 w-32 h-32 rounded-full bg-[#ffdbce]/40 blur-2xl pointer-events-none"></div>
                )}

                {/* Top Badge / Rank Ribbon */}
                <div className="flex items-center justify-between relative z-10">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wide shadow-2xs ${
                      mentor.matchScore >= 95
                        ? 'bg-[#ffdbce] text-[#370e00]'
                        : 'bg-[#d1e4ff] text-[#011d35]'
                    }`}
                  >
                    <span
                      className="material-symbols-outlined text-[14px] text-[#a73a00]"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      stars
                    </span>
                    {mentor.matchLabel}
                  </span>
                  <button
                    type="button"
                    aria-label={`Bookmark ${mentor.name}`}
                    onClick={() => onToggleBookmark(mentor.id)}
                    className="w-8 h-8 rounded-full flex items-center justify-center text-[#43474d] hover:text-[#a73a00] hover:bg-[#eff4ff] transition-colors active:scale-90"
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      {isBookmarked ? 'bookmark' : 'bookmark_border'}
                    </span>
                  </button>
                </div>

                {/* Profile Header Row */}
                <div
                  onClick={() => onSelectExpert(mentor)}
                  className="flex items-start gap-3.5 relative z-10 cursor-pointer"
                >
                  <div className="relative shrink-0">
                    <img
                      className="w-16 h-16 rounded-2xl object-cover shadow-xs ring-2 ring-[#dce9ff]"
                      src={mentor.avatarUrl}
                      alt={mentor.name}
                    />
                    <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#0f2942] text-white flex items-center justify-center shadow-xs">
                      <span className="material-symbols-outlined text-[13px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                        verified
                      </span>
                    </span>
                  </div>
                  <div className="flex flex-col min-w-0 flex-1">
                    <h3 className="text-[17px] font-bold text-[#0b1c30] tracking-tight group-hover:text-[#a73a00] transition-colors truncate">
                      {mentor.name}
                    </h3>
                    <p className="text-[12px] text-[#a73a00] font-semibold truncate">{mentor.title}</p>
                    <p className="text-[12px] text-[#43474d] flex items-center gap-1 mt-0.5 truncate">
                      <span className="material-symbols-outlined text-[15px] shrink-0 text-[#43474d]">
                        account_balance
                      </span>
                      <span>{mentor.institution}</span>
                    </p>
                  </div>
                </div>

                {/* Discipline Chips */}
                <div className="flex flex-wrap gap-1.5 relative z-10">
                  {mentor.tags.slice(0, 3).map((t) => (
                    <span
                      key={t}
                      className="px-2.5 py-1 rounded-lg bg-[#e5eeff] text-[#43474d] text-[11px] font-medium"
                    >
                      {t}
                    </span>
                  ))}
                </div>

                {/* Stats Bar */}
                <div className="grid grid-cols-3 gap-2 py-2 px-3 bg-[#eff4ff] rounded-xl text-center border border-[#d1e4ff]/50">
                  <div className="flex flex-col items-center justify-center">
                    <span className="flex items-center gap-1 text-[13px] text-[#0b1c30] font-bold">
                      <span
                        className="material-symbols-outlined text-[15px] text-[#fd651e]"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        star
                      </span>
                      {mentor.rating.toFixed(2)}
                    </span>
                    <span className="text-[10px] text-[#74777e]">{mentor.reviewCount} reviews</span>
                  </div>
                  <div className="flex flex-col items-center justify-center">
                    <span className="text-[13px] text-[#0b1c30] font-bold">{mentor.papersCited}</span>
                    <span className="text-[10px] text-[#74777e]">Papers Cited</span>
                  </div>
                  <div className="flex flex-col items-center justify-center">
                    <span className="text-[13px] text-[#0b1c30] font-bold">{mentor.mentoringHours}+ hrs</span>
                    <span className="text-[10px] text-[#74777e]">Mentoring</span>
                  </div>
                </div>

                {/* Next Availability & Subsidy Pill */}
                <div className="flex flex-col gap-1.5 pt-0.5">
                  <div className="flex items-center justify-between text-[13px]">
                    <div className="flex items-center gap-1.5 text-[#0b1c30]">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                      <span className="font-bold text-[12px]">Next slot:</span>
                      <span className="text-[#43474d] text-[12px]">{mentor.nextSlotText}</span>
                    </div>
                    <span className="text-[#0b1c30] font-bold text-[16px]">
                      {formatNaira(mentor.hourlyRate)}
                      <span className="text-[11px] font-normal text-[#43474d]">/45m</span>
                    </span>
                  </div>
                  {mentor.subsidyEligible && (
                    <div className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#001a42] bg-[#e5eeff] px-2.5 py-1 rounded-md self-start border border-[#d1e4ff]">
                      <span className="material-symbols-outlined text-[14px] text-[#a73a00]">school</span>
                      <span>{mentor.subsidyLabel}</span>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="grid grid-cols-2 gap-2 pt-1 relative z-10">
                  <button
                    type="button"
                    onClick={() => onSelectExpert(mentor)}
                    className="py-2.5 px-3 rounded-xl bg-[#eff4ff] hover:bg-[#dce9ff] text-[#001428] text-[13px] font-bold shadow-xs transition-all active:scale-[0.98] text-center"
                  >
                    View Profile
                  </button>
                  <button
                    type="button"
                    onClick={() => onBookExpert(mentor)}
                    className="py-2.5 px-3 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[13px] font-bold shadow-xs transition-all active:scale-[0.98] flex items-center justify-center gap-1 text-center"
                  >
                    <span className="material-symbols-outlined text-[18px]">calendar_add_on</span>
                    <span>Quick Book</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Sub-footer AI Scout Card */}
        <div className="px-4 py-3">
          <div className="bg-gradient-to-br from-[#0f2942] to-[#002659] text-white rounded-2xl p-4 shadow-lg relative overflow-hidden flex flex-col gap-3">
            <div className="absolute -right-8 -top-8 w-28 h-28 rounded-full bg-[#fd651e]/20 blur-xl pointer-events-none"></div>
            <div className="flex items-start gap-3 relative z-10">
              <div className="w-10 h-10 rounded-xl bg-white/15 flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[24px] text-[#ffdbce]">travel_explore</span>
              </div>
              <div className="flex flex-col">
                <h4 className="text-[17px] text-white font-bold">Unmatched Niche?</h4>
                <p className="text-[13px] text-[#adc6ff] mt-1 leading-relaxed">
                  Can't find your exact research frontier? Let Mentora AI scout active lab directors across 450+ global partner institutions.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onOpenDeepScout}
              className="w-full py-3 px-4 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[14px] font-bold shadow-md transition-all active:scale-[0.98] flex items-center justify-center gap-2 mt-1 relative z-10"
            >
              <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
              <span>Launch Deep AI Faculty Scout</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

import React, { useState } from 'react';
import { Expert, formatNaira } from '../data/expertsData';

interface ExpertProfileScreenProps {
  expert: Expert;
  onBack: () => void;
  onBookSession: (expert: Expert, selectedDate: string, selectedTime: string) => void;
  isBookmarked: boolean;
  onToggleBookmark: () => void;
  onShare: () => void;
}

export const ExpertProfileScreen: React.FC<ExpertProfileScreenProps> = ({
  expert,
  onBack,
  onBookSession,
  isBookmarked,
  onToggleBookmark,
  onShare
}) => {
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const currentDay = expert.days[selectedDayIndex] || expert.days[0];
  const [selectedSlotTime, setSelectedSlotTime] = useState<string>(
    currentDay?.slots.find((s) => s.isAvailable)?.time || '2:30 PM - 3:15 PM'
  );

  const handleDaySelect = (index: number) => {
    setSelectedDayIndex(index);
    const day = expert.days[index];
    const firstAvail = day?.slots.find((s) => s.isAvailable);
    if (firstAvail) {
      setSelectedSlotTime(firstAvail.time);
    }
  };

  const handleBookClick = () => {
    const formattedDate = `${currentDay?.dayName}, ${currentDay?.monthName} ${currentDay?.dateNum}`;
    onBookSession(expert, formattedDate, selectedSlotTime);
  };

  return (
    <main className="flex flex-col relative w-full pt-4 pb-28 bg-[#f8f9ff] flex-1 max-w-3xl mx-auto">
      <div className="flex flex-col w-full px-4 pb-6 space-y-4">
        {/* Hero Profile Card */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 relative overflow-hidden">
          <div className="flex flex-col items-center text-center">
            {/* Avatar with Ring Accent */}
            <div className="relative mb-3">
              <div className="w-24 h-24 rounded-full overflow-hidden shadow-md bg-[#e5eeff] ring-3 ring-[#d1e4ff]">
                <img
                  className="w-full h-full object-cover"
                  src={expert.avatarUrl}
                  alt={expert.name}
                />
              </div>
              <div className="absolute -bottom-1 -right-1 bg-[#ffffff] rounded-full p-1 shadow-sm flex items-center justify-center">
                <span
                  className="material-symbols-outlined text-[#a73a00] text-[20px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  verified
                </span>
              </div>
            </div>

            {/* Verification Badge */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#d1e4ff] text-[#011d35] mb-2 shadow-2xs">
              <span className="material-symbols-outlined text-[14px]">school</span>
              <span className="text-[11px] font-bold">Verified Faculty • {expert.institution}</span>
            </div>

            {/* Name & Title */}
            <h2 className="text-[24px] font-bold text-[#001428] tracking-tight mt-1">
              {expert.name}
            </h2>
            <p className="text-[13px] text-[#a73a00] font-semibold mt-0.5">
              {expert.title}
            </p>

            {/* Affiliations */}
            <p className="text-[13px] text-[#43474d] max-w-sm mt-2 leading-relaxed">
              {expert.department}
            </p>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-2 mt-4 pt-2">
            <div className="bg-[#eff4ff] rounded-xl p-3 flex items-center gap-3 border border-[#d1e4ff]/50">
              <div className="w-9 h-9 rounded-lg bg-[#ffffff] flex items-center justify-center text-[#a73a00] shadow-xs">
                <span
                  className="material-symbols-outlined text-[20px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  star
                </span>
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[18px] font-extrabold text-[#001428] leading-none">
                  {expert.rating.toFixed(2)}
                </span>
                <span className="text-[11px] text-[#43474d] truncate mt-0.5">
                  {expert.reviewCount} reviews
                </span>
              </div>
            </div>

            <div className="bg-[#eff4ff] rounded-xl p-3 flex items-center gap-3 border border-[#d1e4ff]/50">
              <div className="w-9 h-9 rounded-lg bg-[#ffffff] flex items-center justify-center text-[#0f2942] shadow-xs">
                <span className="material-symbols-outlined text-[20px]">menu_book</span>
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[18px] font-extrabold text-[#001428] leading-none">
                  {expert.papersCited}
                </span>
                <span className="text-[11px] text-[#43474d] truncate mt-0.5">
                  Papers Cited
                </span>
              </div>
            </div>

            <div className="bg-[#eff4ff] rounded-xl p-3 flex items-center gap-3 border border-[#d1e4ff]/50">
              <div className="w-9 h-9 rounded-lg bg-[#ffffff] flex items-center justify-center text-[#fd651e] shadow-xs">
                <span className="material-symbols-outlined text-[20px]">groups</span>
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[18px] font-extrabold text-[#001428] leading-none">
                  {expert.scholarsGuided}+
                </span>
                <span className="text-[11px] text-[#43474d] truncate mt-0.5">
                  Scholars Guided
                </span>
              </div>
            </div>

            <div className="bg-[#eff4ff] rounded-xl p-3 flex items-center gap-3 border border-[#d1e4ff]/50">
              <div className="w-9 h-9 rounded-lg bg-[#ffffff] flex items-center justify-center text-[#001428] shadow-xs">
                <span className="material-symbols-outlined text-[20px]">history_edu</span>
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[18px] font-extrabold text-[#001428] leading-none">
                  {expert.yearsExperience} yrs
                </span>
                <span className="text-[11px] text-[#43474d] truncate mt-0.5">
                  Academic R&D
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Scholarly Bio & Academic Credentials */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[16px] font-bold text-[#001428]">Academic Background & Bio</h3>
            <span className="material-symbols-outlined text-[#74777e] text-[20px]">account_balance</span>
          </div>
          <p className="text-[14px] text-[#43474d] leading-relaxed">
            {expert.bio}
          </p>

          {/* University Degrees Pill List */}
          <div className="pt-1 flex flex-wrap gap-2">
            {expert.degrees.map((deg) => (
              <span
                key={deg}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#e5eeff] text-[#001428] text-[12px] font-semibold"
              >
                <span className="material-symbols-outlined text-[16px] text-[#001428]">workspace_premium</span>
                {deg}
              </span>
            ))}
          </div>
        </section>

        {/* Mentorship Expertise Chips */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[16px] font-bold text-[#001428]">Areas of Mentorship</h3>
            <span className="inline-flex items-center gap-1 text-[11px] text-[#a73a00] font-bold">
              <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
              Active Specializations
            </span>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {expert.specializations.map((spec, i) => (
              <span
                key={spec}
                className={`px-3 py-1.5 rounded-full text-[12px] font-semibold shadow-2xs ${
                  i === 3
                    ? 'bg-[#ffdbce] text-[#7f2b00] border border-[#ffb599]'
                    : 'bg-[#eff4ff] text-[#001428] border border-[#d1e4ff]/60'
                }`}
              >
                {spec}
              </span>
            ))}
          </div>
        </section>

        {/* Availability & Interactive Calendar Picker */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-[16px] font-bold text-[#001428]">Select Session Time</h3>
              <p className="text-[11px] text-[#43474d] mt-0.5">Timezone: America/New_York (EDT)</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-[#eff4ff] flex items-center justify-center text-[#001428]">
              <span className="material-symbols-outlined text-[18px]">calendar_today</span>
            </div>
          </div>

          {/* Date selector row */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar -mx-1 px-1">
            {expert.days.map((day, idx) => {
              const isSelected = selectedDayIndex === idx;
              return (
                <button
                  key={day.dateKey}
                  type="button"
                  onClick={() => handleDaySelect(idx)}
                  className={`shrink-0 flex flex-col items-center justify-center w-24 py-2.5 px-2 rounded-xl text-center transition-all active:scale-95 ${
                    isSelected
                      ? 'bg-[#001428] text-white shadow-md'
                      : 'bg-[#eff4ff] text-[#0b1c30] hover:bg-[#dce9ff] border border-[#d1e4ff]/60'
                  }`}
                >
                  <span className="text-[12px] font-semibold opacity-90">
                    {day.dayName}, {day.monthName} {day.dateNum}
                  </span>
                  <span
                    className={`text-[11px] font-bold mt-1 ${
                      isSelected ? 'text-[#ffb599]' : 'text-[#a73a00]'
                    }`}
                  >
                    {day.slotsCount}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Time Slots Grid */}
          <div className="space-y-2">
            <span className="text-[11px] text-[#43474d] uppercase tracking-wider font-bold">
              Available Windows
            </span>
            <div className="grid grid-cols-2 gap-2">
              {currentDay?.slots.map((slot) => {
                const isSelected = selectedSlotTime === slot.time;
                if (!slot.isAvailable) {
                  return (
                    <div
                      key={slot.time}
                      className="p-3 rounded-xl bg-[#e5eeff]/50 text-[#74777e] text-[12px] font-medium flex items-center justify-between opacity-50 cursor-not-allowed line-through"
                    >
                      <span>{slot.time}</span>
                      <span className="text-[10px]">Booked</span>
                    </div>
                  );
                }

                return (
                  <button
                    key={slot.time}
                    type="button"
                    onClick={() => setSelectedSlotTime(slot.time)}
                    className={`flex items-center justify-between p-3 rounded-xl text-[12px] font-bold transition-all active:scale-98 ${
                      isSelected
                        ? 'bg-[#a73a00] text-white shadow-sm'
                        : 'bg-[#eff4ff] text-[#0b1c30] hover:bg-[#dce9ff] border border-[#d1e4ff]/60'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      {isSelected && (
                        <span
                          className="material-symbols-outlined text-[16px] text-white"
                          style={{ fontVariationSettings: "'FILL' 1" }}
                        >
                          check_circle
                        </span>
                      )}
                      <span>{slot.time}</span>
                    </div>
                    {!isSelected && (
                      <span className="material-symbols-outlined text-[14px] text-[#74777e]">
                        schedule
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Meeting Format Note */}
          <div className="bg-[#eff4ff] rounded-xl p-3 flex items-start gap-2.5 border border-[#d1e4ff]/60">
            <span className="material-symbols-outlined text-[#a73a00] text-[20px] mt-0.5">lock</span>
            <p className="text-[12px] text-[#0b1c30] leading-snug">
              45-minute encrypted 1:1 Video Call • Includes session recording, whiteboard notes, and shared LaTeX sandbox.
            </p>
          </div>
        </section>

        {/* Student & Researcher Reviews */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-[16px] font-bold text-[#001428]">Student & Researcher Reviews</h3>
              <div className="flex items-center gap-1.5 mt-0.5">
                <div className="flex text-[#a73a00]">
                  {[...Array(5)].map((_, i) => (
                    <span
                      key={i}
                      className="material-symbols-outlined text-[15px]"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      star
                    </span>
                  ))}
                </div>
                <span className="text-[13px] font-bold text-[#001428]">{expert.rating.toFixed(2)}</span>
                <span className="text-[11px] text-[#43474d]">({expert.reviewCount} verified evaluations)</span>
              </div>
            </div>
            <button type="button" className="text-[#a73a00] text-[12px] font-bold hover:underline">
              See All
            </button>
          </div>

          <div className="space-y-3">
            {expert.reviews.map((rev) => (
              <div key={rev.id} className="bg-[#eff4ff] rounded-xl p-3.5 space-y-2 border border-[#d1e4ff]/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-[#e5eeff] flex items-center justify-center font-bold text-[#001428] text-[12px]">
                      {rev.author.substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-[13px] font-bold text-[#001428]">{rev.author}</p>
                      <p className="text-[11px] text-[#43474d]">{rev.role}</p>
                    </div>
                  </div>
                  <div className="flex text-[#a73a00]">
                    {[...Array(rev.rating)].map((_, idx) => (
                      <span
                        key={idx}
                        className="material-symbols-outlined text-[14px]"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        star
                      </span>
                    ))}
                  </div>
                </div>
                <p className="text-[13px] text-[#0b1c30] leading-relaxed">
                  {rev.text}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Sticky Bottom Dock */}
      <footer className="fixed bottom-0 inset-x-0 z-40 pb-safe bg-[#f8f9ff]/95 backdrop-blur-xl shadow-[0_-2px_12px_rgba(15,41,66,0.06)] border-t border-[#e2e8f0]/80">
        <div className="h-20 px-4 flex items-center justify-between gap-4 max-w-lg mx-auto">
          <div className="flex flex-col">
            <span className="text-[11px] text-[#43474d] uppercase tracking-wider font-semibold">
              Mentorship Rate
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-[24px] font-extrabold text-[#001428]">{formatNaira(expert.hourlyRate)}</span>
              <span className="text-[12px] text-[#43474d]">/ session</span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleBookClick}
            className="min-h-[48px] flex-1 max-w-[200px] flex items-center justify-center gap-2 px-4 bg-[#a73a00] hover:bg-[#571a00] text-white rounded-xl text-[14px] font-bold shadow-sm hover:opacity-95 active:scale-[0.99] transition-all"
          >
            <span>Book Session</span>
            <span className="material-symbols-outlined text-[18px]">calendar_month</span>
          </button>
        </div>
      </footer>
    </main>
  );
};

import React, { useState } from 'react';
import { Expert } from '../data/expertsData';

interface BookingScreenProps {
  expert: Expert;
  onBack: () => void;
  onProceedToPayment: (bookingDetails: {
    format: 'video' | 'async';
    formatTitle: string;
    date: string;
    time: string;
    agenda: string;
    price: number;
    platformFee: number;
    subsidyDiscount: number;
    totalDue: number;
  }) => void;
  preSelectedDate?: string;
  preSelectedTime?: string;
}

export const BookingScreen: React.FC<BookingScreenProps> = ({
  expert,
  onBack,
  onProceedToPayment,
  preSelectedDate = 'Wed, Oct 25',
  preSelectedTime = '2:30 PM - 3:15 PM'
}) => {
  const [format, setFormat] = useState<'video' | 'async'>('video');
  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0);

  // Available days from expert
  const days = expert.days && expert.days.length > 0 ? expert.days : [
    {
      dateKey: '2024-10-25',
      dayName: 'Wed',
      dateNum: '25',
      monthName: 'Oct',
      slotsCount: '4 slots',
      slots: [
        { time: '10:00 - 10:45 AM', period: 'morning' as const, isAvailable: false },
        { time: '11:30 - 12:15 PM', period: 'morning' as const, isAvailable: true },
        { time: '2:30 PM - 3:15 PM', period: 'afternoon' as const, isAvailable: true, isBestFit: true },
        { time: '4:00 - 4:45 PM', period: 'afternoon' as const, isAvailable: true },
        { time: '5:30 - 6:15 PM', period: 'afternoon' as const, isAvailable: true }
      ]
    }
  ];

  const currentDay = days[selectedDayIndex] || days[0];
  const currentDateString = `${currentDay.dayName}, ${currentDay.monthName} ${currentDay.dateNum}`;
  const [selectedDate, setSelectedDate] = useState<string>(preSelectedDate || currentDateString);

  // Select initial slot
  const defaultSlot = currentDay.slots.find((s) => s.isAvailable)?.time || preSelectedTime || '2:30 PM - 3:15 PM';
  const [selectedTime, setSelectedTime] = useState<string>(defaultSlot);

  const [selectedTag, setSelectedTag] = useState<string>('PhD Proposal');
  const [agenda, setAgenda] = useState<string>(
    'Reviewing dissertation chapter 3 on rotated surface codes error threshold simulations.'
  );

  // Pricing calculations
  const baseRate = format === 'video' ? expert.hourlyRate : expert.asyncRate;
  const platformFee = 5.0;
  const subsidyDiscount = expert.subsidyEligible ? 15.0 : 0.0;
  const totalDue = Math.max(0, baseRate + platformFee - subsidyDiscount);

  const handleDateChange = (idx: number) => {
    setSelectedDayIndex(idx);
    const day = days[idx];
    const dateStr = `${day.dayName}, ${day.monthName} ${day.dateNum}`;
    setSelectedDate(dateStr);
    const firstAvail = day.slots.find((s) => s.isAvailable);
    if (firstAvail) {
      setSelectedTime(firstAvail.time);
    }
  };

  const handleContinue = () => {
    onProceedToPayment({
      format,
      formatTitle: format === 'video' ? '1:1 Video Consultation (45 mins)' : 'Async Paper & Math Review (24h)',
      date: selectedDate,
      time: selectedTime,
      agenda,
      price: baseRate,
      platformFee,
      subsidyDiscount,
      totalDue
    });
  };

  const morningSlots = currentDay.slots.filter((s) => s.period === 'morning');
  const afternoonSlots = currentDay.slots.filter((s) => s.period === 'afternoon');

  return (
    <main className="flex-1 flex flex-col relative w-full pt-24 bg-[#f8f9ff] pb-safe max-w-lg mx-auto">
      <div className="flex flex-col w-full pb-40">
        {/* Top Mentor Context Strip */}
        <div className="px-4 pt-3 pb-3">
          <div className="bg-[#ffffff] rounded-xl p-3.5 shadow-sm border border-[#e2e8f0]/80 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="relative w-12 h-12 rounded-full overflow-hidden shrink-0 shadow-inner">
                <img
                  className="w-full h-full object-cover"
                  src={expert.avatarUrl}
                  alt={expert.name}
                />
                <span className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-[#a73a00] rounded-full flex items-center justify-center">
                  <span className="material-symbols-outlined text-[10px] text-white" style={{ fontVariationSettings: "'FILL' 1" }}>
                    bolt
                  </span>
                </span>
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[15px] font-bold text-[#0b1c30] truncate">{expert.name}</span>
                  <span className="material-symbols-outlined text-[16px] text-[#0f2942]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    verified
                  </span>
                </div>
                <span className="text-[11px] text-[#43474d] truncate">{expert.title}</span>
              </div>
            </div>
            <div className="flex flex-col items-end shrink-0 pl-1">
              <div className="flex items-center gap-1 bg-[#e5eeff] px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-[14px] text-[#a73a00]" style={{ fontVariationSettings: "'FILL' 1" }}>
                  star
                </span>
                <span className="text-[11px] text-[#0b1c30] font-bold">{expert.rating.toFixed(2)}</span>
              </div>
              <span className="text-[10px] text-[#74777e] mt-0.5">{expert.reviewCount}+ sessions</span>
            </div>
          </div>

          {/* Step Progress Micro-Card */}
          <div className="mt-3 bg-[#eff4ff] rounded-xl px-3.5 py-2.5 flex flex-col gap-1.5 shadow-xs border border-[#d1e4ff]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#a73a00] text-[16px]">edit_calendar</span>
                <span className="text-[11px] font-bold text-[#0b1c30] uppercase tracking-wide">
                  Step 1 of 3: Session Details
                </span>
              </div>
              <span className="text-[11px] font-bold text-[#a73a00]">33%</span>
            </div>
            <div className="w-full h-1.5 bg-[#d3e4fe] rounded-full overflow-hidden">
              <div className="h-full bg-[#a73a00] rounded-full transition-all duration-500" style={{ width: '33%' }}></div>
            </div>
          </div>
        </div>

        {/* Main Booking Flow Form */}
        <div className="px-4 flex flex-col gap-5">
          {/* SECTION 1: Session Format / Type */}
          <section className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-bold text-[#0b1c30]">1. Choose Session Type</h2>
              <span className="text-[11px] font-bold text-[#a73a00] flex items-center gap-0.5">
                <span className="material-symbols-outlined text-[13px]">auto_awesome</span> Live LaTeX Included
              </span>
            </div>

            {/* Option 1: 1:1 Video Consultation (Selected) */}
            <div
              role="button"
              tabIndex={0}
              data-testid="format-video"
              onClick={() => setFormat('video')}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setFormat('video'); }}
              className={`relative rounded-xl p-3.5 cursor-pointer transition-all border ${
                format === 'video'
                  ? 'bg-gradient-to-br from-white via-[#eff4ff] to-white shadow-md border-[#a73a00]'
                  : 'bg-white shadow-sm border-[#e2e8f0] opacity-85 hover:opacity-100'
              }`}
            >
              <div className="flex items-start justify-between gap-3 relative z-10">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      format === 'video' ? 'bg-[#ffdbce] text-[#a73a00]' : 'bg-[#e5eeff] text-[#43474d]'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                      videocam
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[14px] font-bold text-[#0b1c30]">1:1 Video Consultation</span>
                      <span className="bg-[#ffdbce] text-[#370e00] text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-wider font-bold">
                        Recommended
                      </span>
                    </div>
                    <span className="text-[12px] text-[#43474d]">45 minutes • High-definition live sync</span>
                  </div>
                </div>
                <div className="flex flex-col items-end shrink-0">
                  <span className="text-[18px] font-extrabold text-[#0b1c30]">${expert.hourlyRate}</span>
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center mt-1 ${
                      format === 'video' ? 'bg-[#a73a00] text-white' : 'bg-[#e5eeff] text-transparent'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[13px] font-bold">check</span>
                  </div>
                </div>
              </div>
              <p className="text-[12px] text-[#43474d] relative z-10 pl-11 mt-1.5 leading-relaxed">
                Interactive video with live LaTeX collaborative sandbox, screen review, and encrypted tamper-proof recording.
              </p>
            </div>

            {/* Option 2: Async Paper & Math Review */}
            <div
              role="button"
              tabIndex={0}
              data-testid="format-async"
              onClick={() => setFormat('async')}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setFormat('async'); }}
              className={`relative rounded-xl p-3.5 cursor-pointer transition-all border ${
                format === 'async'
                  ? 'bg-gradient-to-br from-white via-[#eff4ff] to-white shadow-md border-[#a73a00]'
                  : 'bg-white shadow-sm border-[#e2e8f0] opacity-85 hover:opacity-100'
              }`}
            >
              <div className="flex items-start justify-between gap-3 relative z-10">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      format === 'async' ? 'bg-[#ffdbce] text-[#a73a00]' : 'bg-[#e5eeff] text-[#43474d]'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[20px]">assignment_turned_in</span>
                  </div>
                  <div>
                    <span className="text-[14px] font-bold text-[#0b1c30]">Async Paper & Math Review</span>
                    <div className="text-[12px] text-[#43474d]">Annotated feedback • Delivered within 24h</div>
                  </div>
                </div>
                <div className="flex flex-col items-end shrink-0">
                  <span className="text-[18px] font-extrabold text-[#0b1c30]">${expert.asyncRate}</span>
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center mt-1 ${
                      format === 'async' ? 'bg-[#a73a00] text-white' : 'bg-[#e5eeff] text-transparent'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[13px] font-bold">check</span>
                  </div>
                </div>
              </div>
              <p className="text-[12px] text-[#43474d] relative z-10 pl-11 mt-1.5 leading-relaxed">
                Comprehensive dissertation, preprint, or grant feedback with margin notes and a 10-minute companion audio walk-through.
              </p>
            </div>
          </section>

          {/* SECTION 2: Select Date */}
          <section className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-bold text-[#0b1c30]">2. Select Date</h2>
              <div className="flex items-center gap-1 bg-[#eff4ff] px-2 py-1 rounded-full border border-[#d1e4ff]/60">
                <button type="button" className="w-5 h-5 flex items-center justify-center rounded-full text-[#0b1c30]">
                  <span className="material-symbols-outlined text-[14px]">chevron_left</span>
                </button>
                <span className="text-[11px] font-bold text-[#0b1c30] px-1">October 2024</span>
                <button type="button" className="w-5 h-5 flex items-center justify-center rounded-full text-[#0b1c30]">
                  <span className="material-symbols-outlined text-[14px]">chevron_right</span>
                </button>
              </div>
            </div>

            {/* Horizontal Date Picker Strip */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1.5 -mx-4 px-4 no-scrollbar">
              {days.map((d, idx) => {
                const isSelected = selectedDayIndex === idx;
                return (
                  <button
                    key={d.dateKey}
                    type="button"
                    onClick={() => handleDateChange(idx)}
                    className={`shrink-0 flex flex-col items-center justify-between w-[68px] h-[82px] py-2 px-1 rounded-xl transition-all active:scale-95 text-center ${
                      isSelected
                        ? 'bg-[#001428] text-white shadow-md'
                        : 'bg-[#ffffff] text-[#0b1c30] shadow-sm hover:bg-[#e5eeff] border border-[#e2e8f0]'
                    }`}
                  >
                    <span className="text-[11px] font-semibold opacity-80 uppercase">{d.dayName}</span>
                    <span className="text-[24px] font-extrabold leading-none">{d.dateNum}</span>
                    <span
                      className={`text-[10px] font-bold leading-tight ${
                        isSelected ? 'text-[#b0c9e8]' : 'text-[#a73a00]'
                      }`}
                    >
                      {d.slotsCount}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Timezone Badge */}
            <div className="flex items-center gap-1.5 bg-[#eff4ff] px-3 py-1.5 rounded-lg text-[#43474d] text-xs border border-[#d1e4ff]/50">
              <span className="material-symbols-outlined text-[15px] text-[#001428]">schedule</span>
              <span className="truncate">
                Timezone: <strong className="text-[#0b1c30]">America/New_York (EDT)</strong> • Automatically adjusted
              </span>
            </div>
          </section>

          {/* SECTION 3: Available Slots */}
          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-bold text-[#0b1c30]">3. Available Slots</h2>
              <span className="text-[11px] text-[#43474d] font-semibold">{selectedDate}</span>
            </div>

            {/* Morning Group if available */}
            {morningSlots.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-1.5 text-[#43474d]">
                  <span className="material-symbols-outlined text-[16px]">wb_twilight</span>
                  <span className="text-[11px] font-bold uppercase tracking-wider">Morning</span>
                </div>
                <div className="grid grid-cols-2 gap-2.5">
                  {morningSlots.map((slot) => {
                    const isSelected = selectedTime === slot.time;
                    if (!slot.isAvailable) {
                      return (
                        <div
                          key={slot.time}
                          className="bg-[#e5eeff]/50 rounded-xl p-3 flex flex-col items-start opacity-50 cursor-not-allowed border border-[#d1e4ff]/30"
                        >
                          <span className="text-[13px] font-semibold text-[#0b1c30] line-through">{slot.time}</span>
                          <span className="text-[10px] text-[#74777e] mt-0.5">Booked</span>
                        </div>
                      );
                    }

                    return (
                      <button
                        key={slot.time}
                        type="button"
                        onClick={() => setSelectedTime(slot.time)}
                        className={`rounded-xl p-3 flex flex-col items-start shadow-xs transition-all text-left border ${
                          isSelected
                            ? 'bg-[#a73a00] text-white border-[#a73a00]'
                            : 'bg-[#ffffff] text-[#0b1c30] hover:bg-[#eff4ff] border-[#e2e8f0]'
                        }`}
                      >
                        <div className="flex items-center gap-1 w-full justify-between">
                          <span className="text-[13px] font-bold">{slot.time}</span>
                          {isSelected && (
                            <span className="material-symbols-outlined text-[15px] text-white font-bold">check</span>
                          )}
                        </div>
                        <span className={`text-[10px] font-medium mt-0.5 ${isSelected ? 'text-white/90' : 'text-[#0f2942]'}`}>
                          {isSelected ? 'Selected' : 'Available'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Afternoon Group */}
            <div className="flex flex-col gap-1.5 pt-1">
              <div className="flex items-center gap-1.5 text-[#43474d]">
                <span className="material-symbols-outlined text-[16px]">wb_sunny</span>
                <span className="text-[11px] font-bold uppercase tracking-wider">Afternoon & Evening</span>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                {afternoonSlots.map((slot) => {
                  const isSelected = selectedTime === slot.time;
                  if (!slot.isAvailable) {
                    return (
                      <div
                        key={slot.time}
                        className="bg-[#e5eeff]/50 rounded-xl p-3 flex flex-col items-start opacity-50 cursor-not-allowed border border-[#d1e4ff]/30"
                      >
                        <span className="text-[13px] font-semibold text-[#0b1c30] line-through">{slot.time}</span>
                        <span className="text-[10px] text-[#74777e] mt-0.5">Booked</span>
                      </div>
                    );
                  }

                  return (
                    <button
                      key={slot.time}
                      type="button"
                      onClick={() => setSelectedTime(slot.time)}
                      className={`rounded-xl p-3.5 flex flex-col items-start shadow-xs transition-all text-left border ${
                        isSelected
                          ? 'bg-[#a73a00] text-white border-[#a73a00] shadow-sm'
                          : 'bg-[#ffffff] text-[#0b1c30] hover:bg-[#eff4ff] border-[#e2e8f0]'
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="text-[13px] font-bold">{slot.time}</span>
                        {isSelected && (
                          <span className="material-symbols-outlined text-[16px] text-white font-bold">
                            check_circle
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        {slot.isBestFit && !isSelected && (
                          <span className="text-[10px] text-[#a73a00] font-bold">Best fit</span>
                        )}
                        <span className={`text-[10px] font-medium ${isSelected ? 'text-white/90' : 'text-[#74777e]'}`}>
                          {isSelected ? 'Selected' : 'Available'}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </section>

          {/* SECTION 4: Price Summary Box */}
          <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0] space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-[13px] font-bold uppercase tracking-wider text-[#0b1c30]">
                Session Price Summary
              </h3>
              <span className="text-[11px] font-bold text-[#a73a00] bg-[#ffdbce] px-2 py-0.5 rounded-full">
                {format === 'video' ? '1:1 Video (45m)' : 'Async Review (24h)'}
              </span>
            </div>

            <div className="space-y-1.5 text-[13px] pt-1 border-t border-[#f1f5f9]">
              <div className="flex justify-between text-[#43474d]">
                <span>Base Advisory Fee</span>
                <span className="font-semibold text-[#0b1c30]">${baseRate.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-[#43474d]">
                <span>Mentora Platform & Live Tooling</span>
                <span className="font-semibold text-[#0b1c30]">${platformFee.toFixed(2)}</span>
              </div>
              {expert.subsidyEligible && (
                <div className="flex justify-between text-[#a73a00] font-medium">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">school</span>
                    Doctoral Subsidy (Mentora Grant)
                  </span>
                  <span className="font-bold">-${subsidyDiscount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-[15px] font-bold text-[#001428] pt-2 border-t border-[#e2e8f0]">
                <span>Estimated Total Due</span>
                <span className="text-[18px] font-extrabold text-[#001428]">${totalDue.toFixed(2)}</span>
              </div>
            </div>
          </section>

          {/* SECTION 5: Consultation Focus */}
          <section className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <label className="text-[16px] font-bold text-[#0b1c30]" htmlFor="agenda-input">
                5. Consultation Focus & Agenda
              </label>
              <span className="text-[11px] text-[#43474d]">Optional</span>
            </div>

            {/* Quick Topic Tags */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {['PhD Proposal', 'Paper Defense Prep', 'Code / Math Audit'].map((tag) => {
                const isSelected = selectedTag === tag;
                return (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setSelectedTag(tag)}
                    className={`text-[11px] font-bold px-3 py-1.5 rounded-full shadow-xs flex items-center gap-1 active:scale-95 transition-all ${
                      isSelected
                        ? 'bg-[#001428] text-white'
                        : 'bg-[#ffffff] text-[#43474d] hover:bg-[#e5eeff] border border-[#e2e8f0]'
                    }`}
                  >
                    {isSelected && <span className="material-symbols-outlined text-[13px]">check</span>}
                    <span>{isSelected ? tag : `+ ${tag}`}</span>
                  </button>
                );
              })}
            </div>

            {/* Agenda Textarea */}
            <div className="bg-[#ffffff] rounded-xl p-3 shadow-xs border border-[#e2e8f0] focus-within:border-[#0f2942] transition-colors">
              <textarea
                id="agenda-input"
                rows={3}
                value={agenda}
                onChange={(e) => setAgenda(e.target.value)}
                maxLength={500}
                className="w-full bg-transparent text-[13px] text-[#0b1c30] placeholder:text-[#74777e] focus:outline-none resize-none"
                placeholder="e.g., Reviewing PhD thesis proposal on rotated surface codes threshold reduction..."
              />
              <div className="flex items-center justify-between pt-2 border-t border-[#f1f5f9]">
                <span className="text-[10px] text-[#74777e] flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">lock</span> Shared exclusively with {expert.name}
                </span>
                <span className="text-[10px] text-[#74777e] font-semibold">{agenda.length} / 500</span>
              </div>
            </div>
          </section>

          {/* Scholarly Trust Guarantee Banner */}
          <div className="bg-[#eff4ff] rounded-xl p-3 flex items-start gap-2.5 shadow-xs border border-[#d1e4ff]/60">
            <div className="w-7 h-7 rounded-full bg-[#001428] flex items-center justify-center shrink-0 text-white">
              <span className="material-symbols-outlined text-[16px]">verified_user</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[12px] font-bold text-[#0b1c30]">Mentora Guarantee & Rescheduling</span>
              <span className="text-[11px] text-[#43474d] leading-relaxed">
                Free cancellation or reschedule up to 12 hours before start time. Full refund if session objective is unsatisfied.
              </span>
            </div>
          </div>
        </div>

        {/* Sticky Bottom Action Bar */}
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#ffffff]/95 backdrop-blur-xl shadow-[0_-4px_20px_rgba(15,41,66,0.08)] px-4 py-3 pb-safe border-t border-[#e2e8f0]">
          <div className="max-w-lg mx-auto flex items-center justify-between gap-3">
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1 text-[#43474d]">
                <span className="material-symbols-outlined text-[14px] text-[#a73a00]">
                  {format === 'video' ? 'videocam' : 'assignment'}
                </span>
                <span className="text-[11px] font-bold uppercase truncate">
                  {format === 'video' ? '1:1 Video (45m)' : 'Async Review (24h)'}
                </span>
              </div>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-[22px] font-extrabold text-[#0b1c30]">${totalDue.toFixed(2)}</span>
                <span className="text-[11px] text-[#74777e]">total due</span>
              </div>
              <span className="text-[11px] text-[#a73a00] font-bold truncate">
                {selectedDate} • {selectedTime.split(' - ')[0]}
              </span>
            </div>

            <button
              type="button"
              onClick={handleContinue}
              className="bg-[#a73a00] hover:bg-[#571a00] text-white px-5 py-3.5 rounded-xl text-[14px] font-bold flex items-center gap-2 shadow-md active:scale-95 transition-all shrink-0"
            >
              <span>Continue to Payment</span>
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

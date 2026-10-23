import React, { useState } from 'react';
import { Expert, formatNaira } from '../data/expertsData';

interface HomeScreenProps {
  onNavigate: (screen: string) => void;
  onSelectExpert: (expert: Expert) => void;
  onBookExpert: (expert: Expert) => void;
  onOpenAIChatWithPrompt: (promptText: string) => void;
  onOpenFilter: () => void;
  onPrepareSession: () => void;
  experts: Expert[];
  learnerName?: string;
  streakDays?: number;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onNavigate,
  onSelectExpert,
  onBookExpert,
  onOpenAIChatWithPrompt,
  onOpenFilter,
  onPrepareSession,
  experts,
  learnerName = 'Elena',
  streakDays = 12
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [selectedDiscipline, setSelectedDiscipline] = useState('Quantum Computing');

  const disciplines = [
    { label: 'Quantum Computing', emoji: '🔬' },
    { label: 'Cognitive Neuroscience', emoji: '🧠' },
    { label: 'Machine Learning', emoji: '📊' },
    { label: 'Constitutional Law', emoji: '⚖️' },
    { label: 'Behavioral Economics', emoji: '📈' },
    { label: 'Bioengineering', emoji: '🧬' },
    { label: 'Modern Architecture', emoji: '🏛️' }
  ];

  const handleVoiceSearch = () => {
    setIsListening(!isListening);
    if (!isListening) {
      setSearchQuery('Quantum error correction in surface codes');
      setTimeout(() => {
        setIsListening(false);
      }, 1500);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onOpenAIChatWithPrompt(searchQuery);
    }
  };

  return (
    <main className="flex flex-col relative w-full pt-4 pb-24 bg-[#f8f9ff] flex-1 min-h-screen max-w-6xl mx-auto">
      <div className="flex flex-col w-full px-4 space-y-4">
        {/* 1. Warm Greeting & Streak Banner */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-1.5">
              <h1 className="text-[24px] font-bold text-[#0b1c30] tracking-tight">
                Good morning, {learnerName}
              </h1>
              <span className="text-[20px] select-none">👋</span>
            </div>
            <p className="text-[13px] text-[#43474d] truncate">
              Ready to advance your academic & career journey?
            </p>
          </div>
          <div className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#ffdbce] text-[#370e00] shadow-xs">
            <span
              className="material-symbols-outlined text-[18px] text-[#a73a00]"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              local_fire_department
            </span>
            <span className="text-[11px] font-bold tracking-tight whitespace-nowrap">
              {streakDays}-day streak
            </span>
          </div>
        </div>

        {/* 2. Prominent Search Bar with Filter Action */}
        <div className="relative w-full">
          <form
            onSubmit={handleSearchSubmit}
            className="flex items-center w-full h-12 bg-[#ffffff] rounded-2xl shadow-[0_2px_10px_rgba(15,41,66,0.06)] px-3.5 gap-2.5 border border-[#e2e8f0]/80"
          >
            <span className="material-symbols-outlined text-[#74777e] text-[22px]">search</span>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent text-[14px] text-[#0b1c30] placeholder:text-[#74777e] focus:outline-none min-w-0"
              placeholder={isListening ? 'Listening for academic query...' : 'What do you want to learn today?'}
              type="text"
            />
            <button
              aria-label="Voice Search"
              type="button"
              onClick={handleVoiceSearch}
              className={`w-8 h-8 flex items-center justify-center rounded-xl transition-all active:scale-95 ${
                isListening ? 'bg-[#ffdbce] text-[#a73a00]' : 'text-[#43474d] hover:bg-[#e5eeff]'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">mic</span>
            </button>
            <button
              aria-label="Open Filter"
              type="button"
              onClick={onOpenFilter}
              className="w-8 h-8 flex items-center justify-center rounded-xl bg-[#dce9ff] text-[#0f2942] active:scale-95 transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </button>
          </form>
        </div>

        {/* Next Scheduled Session Quick Glance */}
        <div className="w-full bg-[#ffffff] rounded-2xl p-3.5 shadow-sm border border-[#e2e8f0]/70 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-[#0f2942] text-white flex items-center justify-center shrink-0 shadow-sm">
              <span className="material-symbols-outlined text-[20px]">calendar_clock</span>
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#a73a00] animate-pulse"></span>
                <span className="text-[11px] text-[#a73a00] uppercase tracking-wider font-bold">
                  Upcoming Session
                </span>
              </div>
              <p className="text-[14px] text-[#0b1c30] font-bold truncate">Thesis Review with Dr. Vance</p>
              <p className="text-[12px] text-[#43474d]">Tomorrow at 3:00 PM · Video Call</p>
            </div>
          </div>
          <button
            aria-label="Join preparation"
            type="button"
            onClick={onPrepareSession}
            className="px-3.5 py-1.5 rounded-xl bg-[#e5eeff] text-[#0f2942] text-[12px] font-bold shrink-0 hover:bg-[#d3e4fe] transition-colors active:scale-95"
          >
            Prepare
          </button>
        </div>

        {/* 3. Hero Feature Card: "Chat with Mentora AI" */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#001428] via-[#0f2942] to-[#001232] text-white p-4 shadow-[0_12px_28px_-6px_rgba(15,41,66,0.3)]">
          {/* Glowing Accent Circles */}
          <div className="absolute -right-8 -top-8 w-36 h-36 bg-[#fd651e]/20 rounded-full blur-2xl pointer-events-none"></div>
          <div className="absolute right-12 bottom-0 w-24 h-24 bg-[#498cff]/15 rounded-full blur-xl pointer-events-none"></div>

          <div className="relative z-10 flex flex-col space-y-3.5">
            {/* AI Status Badge */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/15 backdrop-blur-md text-[#ffdbce] text-xs self-start">
              <span
                className="material-symbols-outlined text-[15px] text-[#fd651e]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                auto_awesome
              </span>
              <span className="text-[11px] font-semibold tracking-wide">Mentora AI · Online 24/7</span>
            </div>

            {/* Headline */}
            <div className="space-y-1">
              <h2 className="text-[20px] text-white font-bold tracking-tight leading-snug">
                Instant academic insights & expert mentor matching
              </h2>
              <p className="text-[13px] text-[#b0c9e8] leading-relaxed">
                Synthesize complex papers, formulate research theses, or ask for direct scholar connections.
              </p>
            </div>

            {/* CTA Button */}
            <button
              type="button"
              onClick={() => onNavigate('ai-chat')}
              className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[14px] font-bold shadow-md hover:brightness-105 active:scale-[0.99] transition-all"
            >
              <span className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                <span>Start AI Consultation</span>
              </span>
              <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
            </button>

            {/* Quick prompts pill carousel */}
            <div className="flex flex-col space-y-1.5 pt-1">
              <span className="text-[10px] text-[#b0c9e8] uppercase tracking-wider font-bold">
                Suggested inquiries:
              </span>
              <div className="flex gap-2 overflow-x-auto no-scrollbar pb-0.5">
                <button
                  type="button"
                  onClick={() => onOpenAIChatWithPrompt('Draft research thesis comparing rotated surface codes with 2D color codes')}
                  className="shrink-0 px-2.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-[12px] text-white transition-colors active:scale-95 flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[14px] text-[#fd651e]">edit_note</span>
                  <span>Draft research thesis</span>
                </button>
                <button
                  type="button"
                  onClick={() => onOpenAIChatWithPrompt('Find MIT Robotics mentor specializing in neural kinematics and DARPA challenge')}
                  className="shrink-0 px-2.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-[12px] text-white transition-colors active:scale-95 flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[14px] text-[#fd651e]">school</span>
                  <span>Find MIT Robotics mentor</span>
                </button>
                <button
                  type="button"
                  onClick={() => onOpenAIChatWithPrompt('Review tech product strategy and executive career pivot advice')}
                  className="shrink-0 px-2.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-[12px] text-white transition-colors active:scale-95 flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[14px] text-[#fd651e]">cases</span>
                  <span>McKinsey case study prep</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 4. Popular Fields Filter Chips */}
        <div className="flex flex-col space-y-2 pt-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#001428] text-[20px]">category</span>
              <h2 className="text-[17px] font-bold text-[#0b1c30]">Explore Disciplines</h2>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('matched-experts')}
              className="text-[12px] text-[#a73a00] font-bold hover:underline flex items-center"
            >
              <span>View all</span>
              <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            </button>
          </div>

          {/* Filter chips horizontal list */}
          <div className="flex gap-2 overflow-x-auto no-scrollbar py-0.5">
            {disciplines.map((d) => {
              const isSelected = selectedDiscipline === d.label;
              return (
                <button
                  key={d.label}
                  type="button"
                  onClick={() => {
                    setSelectedDiscipline(d.label);
                    onNavigate('matched-experts');
                  }}
                  className={`shrink-0 px-3.5 py-2 rounded-full text-[12px] font-semibold shadow-xs flex items-center gap-1.5 transition-transform active:scale-95 ${
                    isSelected
                      ? 'bg-[#001428] text-white'
                      : 'bg-[#ffffff] text-[#0b1c30] hover:bg-[#e5eeff] border border-[#e2e8f0]/80'
                  }`}
                >
                  <span>{d.emoji}</span>
                  <span>{d.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 5. Featured Mentors & Professors */}
        <div className="flex flex-col space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#a73a00] text-[22px]">verified_user</span>
              <h2 className="text-[17px] font-bold text-[#0b1c30]">Top Scholars & Mentors</h2>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('matched-experts')}
              className="text-[12px] text-[#a73a00] font-bold hover:underline flex items-center"
            >
              <span>Browse {experts.length}+</span>
              <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            </button>
          </div>

          {/* Top Mentor Cards in Responsive Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {experts.slice(0, 3).map((mentor) => (
              <div
                key={mentor.id}
                className="w-full bg-[#ffffff] rounded-2xl p-4 shadow-[0_2px_12px_rgba(15,41,66,0.05)] border border-[#e2e8f0]/70 space-y-3.5 flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div
                      onClick={() => onSelectExpert(mentor)}
                      className="flex items-center gap-3 min-w-0 cursor-pointer group"
                    >
                      <div className="relative shrink-0">
                        <img
                          className="w-13 h-13 rounded-2xl object-cover ring-2 ring-[#d1e4ff] group-hover:scale-105 transition-transform"
                          src={mentor.avatarUrl}
                          alt={mentor.name}
                        />
                        <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#001428] flex items-center justify-center text-white">
                          <span className="material-symbols-outlined text-[13px]">check</span>
                        </span>
                      </div>
                      <div className="flex flex-col min-w-0">
                        <h3 className="text-[16px] font-bold text-[#0b1c30] group-hover:text-[#a73a00] transition-colors truncate">
                          {mentor.name}
                        </h3>
                        <p className="text-[12px] text-[#43474d] truncate">{mentor.title}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-[#e5eeff] text-[11px] font-bold text-[#0f2942]">
                            <span
                              className="material-symbols-outlined text-[14px] text-[#a73a00]"
                              style={{ fontVariationSettings: "'FILL' 1" }}
                            >
                              star
                            </span>
                            <span>{mentor.rating.toFixed(2)}</span>
                          </span>
                          <span className="text-[11px] text-[#74777e]">{mentor.reviewCount}+ reviews</span>
                          <span className="text-[11px] text-[#74777e]">•</span>
                          <span className="text-[11px] font-bold text-[#001428]">{formatNaira(mentor.hourlyRate)}/45m</span>
                        </div>
                      </div>
                    </div>

                    <span className="shrink-0 px-2.5 py-1 rounded-full bg-[#ffdbce] text-[#370e00] text-[11px] font-bold">
                      {mentor.nextSlotDate}
                    </span>
                  </div>

                  {/* Specialization snippet */}
                  <div className="bg-[#eff4ff] rounded-xl p-2.5 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[#a73a00] text-[18px] shrink-0">lightbulb</span>
                    <p className="text-[12px] text-[#43474d] truncate">
                      Specialization: {mentor.specializations[0]} & {mentor.specializations[1]}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => onBookExpert(mentor)}
                    className="flex-1 py-2.5 px-3 rounded-xl bg-[#001428] text-white text-[13px] font-semibold text-center hover:bg-[#0f2942] active:scale-95 transition-all shadow-xs"
                  >
                    Book 1:1 Session
                  </button>
                  <button
                    type="button"
                    aria-label={`Ask ${mentor.name} a question`}
                    onClick={() => onOpenAIChatWithPrompt(`Connect with ${mentor.name} regarding research methodology`)}
                    className="py-2.5 px-3 rounded-xl bg-[#e5eeff] text-[#0f2942] text-[13px] font-semibold flex items-center justify-center hover:bg-[#dce9ff] active:scale-95 transition-all"
                  >
                    <span className="material-symbols-outlined text-[18px]">chat</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
};

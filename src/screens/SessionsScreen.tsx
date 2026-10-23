import React, { useState } from 'react';
import { InitialSession } from '../data/expertsData';

interface SessionsScreenProps {
  sessions: InitialSession[];
  onOpenChamber: (session: InitialSession) => void;
  onNavigateHome: () => void;
  onNavigateExplore: () => void;
  onCancelSession: (sessionId: string) => void;
}

export const SessionsScreen: React.FC<SessionsScreenProps> = ({
  sessions,
  onOpenChamber,
  onNavigateHome,
  onNavigateExplore,
  onCancelSession
}) => {
  const [filterTab, setFilterTab] = useState<'upcoming' | 'completed' | 'all'>('upcoming');
  const [expandedChecklistSessionId, setExpandedChecklistSessionId] = useState<string | null>(null);

  const displayedSessions = sessions.filter((s) => {
    if (filterTab === 'upcoming') return s.status === 'upcoming';
    if (filterTab === 'completed') return s.status === 'completed';
    return true;
  });

  return (
    <main className="flex flex-col relative w-full pt-18 pb-24 bg-[#f8f9ff] flex-1 min-h-screen max-w-lg mx-auto">
      <div className="flex flex-col w-full px-4 space-y-4">
        {/* Header Title */}
        <div className="flex items-center justify-between pt-1">
          <div>
            <h1 className="text-[22px] font-bold text-[#001428] tracking-tight">My Mentorship Sessions</h1>
            <p className="text-[12px] text-[#43474d]">Manage your 1:1 faculty colloquia and pre-session checklists</p>
          </div>
          <button
            type="button"
            onClick={onNavigateExplore}
            className="px-3 py-1.5 rounded-xl bg-[#001428] text-white text-[12px] font-bold shadow-xs hover:bg-[#0f2942] active:scale-95 transition-all flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            <span>Book New</span>
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-1.5 p-1 bg-[#e5eeff] rounded-xl border border-[#d1e4ff]/60">
          <button
            type="button"
            onClick={() => setFilterTab('upcoming')}
            className={`flex-1 py-1.5 rounded-lg text-[12px] font-bold transition-colors ${
              filterTab === 'upcoming'
                ? 'bg-[#ffffff] text-[#001428] shadow-xs'
                : 'text-[#43474d] hover:text-[#001428]'
            }`}
          >
            Upcoming ({sessions.filter((s) => s.status === 'upcoming').length})
          </button>
          <button
            type="button"
            onClick={() => setFilterTab('completed')}
            className={`flex-1 py-1.5 rounded-lg text-[12px] font-bold transition-colors ${
              filterTab === 'completed'
                ? 'bg-[#ffffff] text-[#001428] shadow-xs'
                : 'text-[#43474d] hover:text-[#001428]'
            }`}
          >
            Completed ({sessions.filter((s) => s.status === 'completed').length})
          </button>
          <button
            type="button"
            onClick={() => setFilterTab('all')}
            className={`flex-1 py-1.5 rounded-lg text-[12px] font-bold transition-colors ${
              filterTab === 'all'
                ? 'bg-[#ffffff] text-[#001428] shadow-xs'
                : 'text-[#43474d] hover:text-[#001428]'
            }`}
          >
            All ({sessions.length})
          </button>
        </div>

        {/* Sessions List */}
        {displayedSessions.length === 0 ? (
          <div className="p-8 text-center bg-[#ffffff] rounded-2xl border border-[#e2e8f0] shadow-sm flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-[#eff4ff] flex items-center justify-center text-[#0f2942] mb-3">
              <span className="material-symbols-outlined text-[24px]">event_busy</span>
            </div>
            <h3 className="text-[16px] font-bold text-[#001428]">No {filterTab} sessions found</h3>
            <p className="text-[13px] text-[#43474d] mt-1 max-w-xs">
              Explore 180+ verified scholars across MIT, Oxford, and Stanford to book your next consultation.
            </p>
            <button
              type="button"
              onClick={onNavigateExplore}
              className="mt-4 px-5 py-2.5 rounded-xl bg-[#fd651e] text-white text-[13px] font-bold shadow-md hover:bg-[#a73a00]"
            >
              Explore Faculty Directory
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {displayedSessions.map((s) => {
              const isChecklistOpen = expandedChecklistSessionId === s.id;
              return (
                <div
                  key={s.id}
                  className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 space-y-3.5 transition-all"
                >
                  {/* Top Status & Date */}
                  <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-2.5">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#fd651e] animate-pulse"></span>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-[#a73a00]">
                        {s.scheduledDate}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-[#74777e]">{s.bookingId}</span>
                  </div>

                  {/* Mentor Details */}
                  <div className="flex items-start gap-3">
                    <img
                      src={s.expertAvatar}
                      alt={s.expertName}
                      className="w-13 h-13 rounded-2xl object-cover shadow-xs ring-2 ring-[#dce9ff]"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h3 className="text-[15px] font-bold text-[#001428] truncate">{s.expertName}</h3>
                        <span className="text-[11px] font-bold text-emerald-800 bg-emerald-100/80 px-2.5 py-0.5 rounded-full flex items-center gap-1 border border-emerald-300">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
                          <span>{s.status === 'upcoming' ? 'Upcoming' : s.status === 'completed' ? 'Completed' : 'Cancelled'}</span>
                        </span>
                      </div>
                      <p className="text-[12px] text-[#43474d] truncate">{s.expertTitle}</p>
                      <p className="text-[11px] text-[#74777e] truncate">{s.expertInstitution}</p>
                    </div>
                  </div>

                  {/* Topic & Room info */}
                  <div className="bg-[#eff4ff] p-3 rounded-xl border border-[#d1e4ff]/60 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-[#43474d]">Topic Agenda</span>
                      <span className="text-[11px] font-bold text-[#001428]">{s.scheduledTime}</span>
                    </div>
                    <p className="text-[13px] font-semibold text-[#001428]">{s.consultationTopic}</p>
                    {s.consultationNotes && (
                      <p className="text-[11px] text-[#43474d] mt-0.5 italic">{s.consultationNotes}</p>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => onOpenChamber(s)}
                      className="py-2.5 px-3 rounded-xl bg-[#0f2942] hover:bg-[#001428] text-white text-[12px] font-bold flex items-center justify-center gap-1.5 shadow-sm active:scale-95 transition-all"
                    >
                      <span className="material-symbols-outlined text-[16px]">videocam</span>
                      <span>Enter Chamber</span>
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedChecklistSessionId(isChecklistOpen ? null : s.id)
                      }
                      className="py-2.5 px-3 rounded-xl bg-[#e5eeff] hover:bg-[#dce9ff] text-[#001428] text-[12px] font-bold flex items-center justify-center gap-1.5 transition-all"
                    >
                      <span className="material-symbols-outlined text-[16px]">checklist</span>
                      <span>{isChecklistOpen ? 'Hide Prep' : 'Pre-Session Prep'}</span>
                    </button>
                  </div>

                  {/* Collapsible Pre-Session Prep Checklist */}
                  {isChecklistOpen && (
                    <div className="pt-2 border-t border-[#e2e8f0] space-y-2 text-xs">
                      <span className="font-bold text-[#001428] uppercase text-[10px] tracking-wider block">
                        Prep Checklist:
                      </span>
                      {s.checklist.map((chk) => (
                        <div
                          key={chk.id}
                          className="flex items-center gap-2 p-2 rounded-lg bg-[#f8f9ff] border border-[#e2e8f0]"
                        >
                          <span
                            className={`material-symbols-outlined text-[16px] ${
                              chk.isDone ? 'text-emerald-600' : 'text-[#c3c6ce]'
                            }`}
                          >
                            {chk.isDone ? 'check_circle' : 'radio_button_unchecked'}
                          </span>
                          <div className="flex-1 min-w-0">
                            <span className="font-semibold text-[#0b1c30]">{chk.label}</span>
                            {chk.subtext && <span className="text-[#74777e] block text-[10px]">{chk.subtext}</span>}
                          </div>
                        </div>
                      ))}
                      <div className="flex justify-end pt-1">
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm('Cancel this session booking?')) {
                              onCancelSession(s.id);
                            }
                          }}
                          className="text-[11px] text-red-600 hover:underline font-bold"
                        >
                          Cancel / Reschedule Booking
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
};

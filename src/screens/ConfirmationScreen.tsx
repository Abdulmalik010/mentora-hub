import React, { useState } from 'react';
import { Expert } from '../data/expertsData';

interface ConfirmationScreenProps {
  expert: Expert;
  bookingInfo: {
    bookingId: string;
    date: string;
    time: string;
    formatTitle: string;
    totalPaid: number;
    method: string;
    cardLast4: string;
    agenda: string;
  };
  onNavigateToSessions: () => void;
  onNavigateHome: () => void;
  onOpenChamber: () => void;
  onSendMessage: () => void;
}

export const ConfirmationScreen: React.FC<ConfirmationScreenProps> = ({
  expert,
  bookingInfo,
  onNavigateToSessions,
  onNavigateHome,
  onOpenChamber,
  onSendMessage
}) => {
  const [copiedId, setCopiedId] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [calendarAdded, setCalendarAdded] = useState(false);

  // Interactive Checklist
  const [checklist, setChecklist] = useState([
    {
      id: 'chk-1',
      label: 'Upload arXiv draft or thesis abstract',
      fileName: 'quantum_surface_codes_v2.pdf',
      fileSize: '1.4 MB',
      isDone: true
    },
    {
      id: 'chk-2',
      label: 'Test shared LaTeX whiteboard sandbox',
      actionLabel: 'Try Now',
      subtext: 'Ensure formula rendering and pen tablet support function smoothly.',
      isDone: false
    },
    {
      id: 'chk-3',
      label: 'Prepare 3 focal questions',
      actionLabel: 'Add Notes',
      subtext: 'Focus areas: Fault-tolerance threshold reduction & ancilla qubit routing.',
      isDone: false
    }
  ]);

  const toggleChecklist = (id: string) => {
    setChecklist(
      checklist.map((item) => (item.id === id ? { ...item, isDone: !item.isDone } : item))
    );
  };

  const handleCopyId = () => {
    navigator.clipboard?.writeText(bookingInfo.bookingId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyLink = () => {
    const link = `https://mentora.ai/room/${expert.id}-${bookingInfo.bookingId.replace(/[^0-9]/g, '')}`;
    navigator.clipboard?.writeText(link);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const handleAddCalendar = () => {
    setCalendarAdded(true);
    setTimeout(() => setCalendarAdded(false), 3000);
  };

  const completedCount = checklist.filter((c) => c.isDone).length;

  return (
    <main className="flex-1 flex flex-col relative w-full pt-24 bg-[#f8f9ff] pb-safe max-w-lg mx-auto">
      <div className="flex flex-col w-full px-4 py-3 space-y-5 relative overflow-hidden">
        {/* Subtle Ambient Glow */}
        <div className="absolute -top-16 left-1/2 -translate-x-1/2 w-80 h-80 bg-[#fd651e]/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Top Hero Celebration Banner */}
        <section className="flex flex-col items-center text-center relative z-10 pt-2">
          {/* Radiant Animated Academic Seal */}
          <div className="relative flex items-center justify-center mb-4">
            <div className="absolute w-20 h-20 rounded-full bg-[#ffdbce]/50 animate-ping opacity-60"></div>
            <div className="absolute w-24 h-24 rounded-full bg-[#dce9ff]/70"></div>
            <div className="relative w-16 h-16 rounded-full bg-[#001428] flex items-center justify-center shadow-lg shadow-[#001428]/20">
              <span className="material-symbols-outlined text-white text-[34px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                verified
              </span>
            </div>
            <div className="absolute -bottom-1 -right-1 bg-[#fd651e] text-white px-1.5 py-0.5 rounded-full flex items-center shadow-xs">
              <span className="material-symbols-outlined text-[13px]">auto_awesome</span>
            </div>
          </div>

          {/* Confirmation Titles */}
          <div className="inline-flex items-center gap-1.5 bg-[#eff4ff] px-3 py-1 rounded-full mb-1.5 border border-[#d1e4ff]/60">
            <span className="w-1.5 h-1.5 rounded-full bg-[#fd651e]"></span>
            <span className="text-[11px] text-[#43474d] uppercase tracking-wider font-bold">
              Step 3 of 3 • Session Confirmed
            </span>
          </div>

          <h2 className="text-[24px] font-bold text-[#0b1c30] tracking-tight mb-1">
            Session Successfully Confirmed!
          </h2>
          <p className="text-[13px] text-[#43474d] max-w-xs leading-relaxed mb-3">
            A calendar invitation and encrypted seminar portal link have been dispatched to{' '}
            <span className="font-semibold text-[#001428] underline decoration-[#ffb599]">
              elena.rostova@cam.ac.uk
            </span>
            .
          </p>

          {/* Reference Pill */}
          <div className="inline-flex items-center gap-2 bg-[#ffffff] px-3 py-1.5 rounded-full shadow-xs border border-[#e2e8f0]">
            <span className="text-[11px] text-[#43474d] font-medium">Booking ID</span>
            <span className="text-[12px] text-[#001428] font-mono font-bold tracking-wider">
              {bookingInfo.bookingId}
            </span>
            <button
              type="button"
              aria-label="Copy booking reference"
              onClick={handleCopyId}
              className="text-[#43474d] hover:text-[#001428] transition-colors flex items-center"
            >
              <span className="material-symbols-outlined text-[15px]">
                {copiedId ? 'check' : 'content_copy'}
              </span>
            </button>
          </div>
        </section>

        {/* Session Academic Ticket Card */}
        <section className="bg-[#ffffff] rounded-2xl shadow-md border border-[#e2e8f0] overflow-hidden relative z-10 flex flex-col">
          {/* Header Ribbon */}
          <div className="bg-[#0f2942] px-4 py-3 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#fd651e] text-[18px]">school</span>
              <span className="text-[11px] font-bold tracking-wider uppercase text-[#b0c9e8]">
                Colloquium & Review
              </span>
            </div>
            <span className="text-[11px] bg-[#001428]/60 text-[#b0c9e8] px-2 py-0.5 rounded-full font-semibold">
              45 Min 1:1
            </span>
          </div>

          {/* Mentor Row */}
          <div className="p-4 space-y-4">
            <div className="flex items-start gap-3.5">
              <div className="relative shrink-0">
                <img
                  className="w-14 h-14 rounded-2xl object-cover shadow-xs ring-2 ring-[#dce9ff]"
                  src={expert.avatarUrl}
                  alt={expert.name}
                />
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#001428] flex items-center justify-center text-white">
                  <span className="material-symbols-outlined text-[12px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    check
                  </span>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-[16px] font-bold text-[#0b1c30] truncate">{expert.name}</h3>
                <p className="text-[12px] text-[#43474d] truncate">{expert.department}</p>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] bg-[#eff4ff] text-[#001428] px-2 py-0.5 rounded-full font-bold">
                    Faculty Fellow
                  </span>
                  <span className="text-[11px] text-[#a73a00] font-semibold flex items-center gap-0.5">
                    <span className="material-symbols-outlined text-[13px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                      star
                    </span>
                    5.0 (68 reviews)
                  </span>
                </div>
              </div>
            </div>

            {/* Topic Block */}
            <div className="bg-[#eff4ff] rounded-xl p-3.5 space-y-1 border border-[#d1e4ff]/60">
              <span className="text-[11px] uppercase tracking-wider text-[#43474d] font-bold block">
                Consultation Topic
              </span>
              <h4 className="text-[14px] text-[#001428] font-bold leading-snug">
                Quantum Fault Tolerance & Surface Codes Thesis Review
              </h4>
              <div className="flex flex-wrap gap-1.5 pt-1.5">
                <span className="text-[11px] bg-[#ffffff] text-[#43474d] px-2.5 py-0.5 rounded-full font-medium border border-[#e2e8f0]">
                  Toric Codes
                </span>
                <span className="text-[11px] bg-[#ffffff] text-[#43474d] px-2.5 py-0.5 rounded-full font-medium border border-[#e2e8f0]">
                  Syndrome Extraction
                </span>
                <span className="text-[11px] bg-[#ffffff] text-[#43474d] px-2.5 py-0.5 rounded-full font-medium border border-[#e2e8f0]">
                  Decoders
                </span>
              </div>
            </div>

            {/* Schedule Time & Channel */}
            <div className="space-y-2.5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
                  <span className="material-symbols-outlined text-[20px]">calendar_clock</span>
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-[10px] text-[#43474d] uppercase tracking-wider block font-bold">
                    Scheduled Window
                  </span>
                  <p className="text-[13px] text-[#0b1c30] font-bold truncate">
                    {bookingInfo.date}, 2024
                  </p>
                  <p className="text-[12px] text-[#a73a00] font-semibold">
                    {bookingInfo.time} EDT (UTC-4)
                  </p>
                </div>
              </div>

              {/* Meeting Room Link & Camera Test Row */}
              <div className="bg-[#f8f9ff] rounded-xl p-3 border border-[#e2e8f0] space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="material-symbols-outlined text-[#fd651e] text-[18px] shrink-0">
                      videocam
                    </span>
                    <span className="text-[11px] font-mono font-bold text-[#0b1c30] truncate">
                      mentora.ai/room/{expert.id}-9842
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="text-[#001428] hover:text-[#fd651e] px-2 py-1 rounded-lg bg-[#e5eeff] flex items-center gap-1 text-[11px] font-bold transition-colors"
                  >
                    <span className="material-symbols-outlined text-[13px]">
                      {copiedLink ? 'check' : 'content_copy'}
                    </span>
                    <span>{copiedLink ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[#e2e8f0]/60">
                  <span className="text-[11px] text-[#43474d] flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#fd651e] animate-pulse"></span>
                    Room unlocked 10m before call
                  </span>
                  <button
                    type="button"
                    onClick={onOpenChamber}
                    className="text-[#0b1c30] text-[11px] font-bold flex items-center gap-1 hover:text-[#a73a00] transition-colors"
                  >
                    <span className="material-symbols-outlined text-[14px]">settings_video_camera</span>
                    <span>Test AV Setup</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Payment Summary Pill Row */}
            <div className="pt-2 flex items-center justify-between border-t border-[#e2e8f0]">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#43474d] text-[18px]">
                  {bookingInfo.method.includes('Bank') ? 'account_balance' : 'credit_card'}
                </span>
                <span className="text-[12px] text-[#43474d]">
                  Paid via {bookingInfo.method} (•••• {bookingInfo.cardLast4})
                </span>
              </div>
              <div className="text-right">
                <span className="text-[16px] font-bold text-[#001428]">
                  ${bookingInfo.totalPaid.toFixed(2)}
                </span>
                <span className="text-[10px] text-[#fd651e] font-bold block leading-none">
                  Receipt Emailed
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Quick Action Buttons */}
        <section className="space-y-2.5 z-10">
          <button
            type="button"
            onClick={handleAddCalendar}
            className="w-full h-12 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[13px] font-bold flex items-center justify-center gap-2 shadow-md hover:opacity-95 active:scale-[0.98] transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">calendar_add_on</span>
            <span>{calendarAdded ? '✓ Added to Calendar (.ics sync)' : 'Add to Google / Apple Calendar'}</span>
          </button>
          <button
            type="button"
            onClick={onSendMessage}
            className="w-full h-12 rounded-xl bg-[#ffffff] text-[#001428] text-[13px] font-bold flex items-center justify-center gap-2 shadow-sm border border-[#e2e8f0] hover:bg-[#eff4ff] active:scale-[0.98] transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">chat_bubble</span>
            <span>Send Message to {expert.name}</span>
          </button>
        </section>

        {/* Elena's Pre-Session Preparation Checklist Card */}
        <section className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0] space-y-3 z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#dce9ff] flex items-center justify-center text-[#001428]">
                <span className="material-symbols-outlined text-[18px]">checklist</span>
              </div>
              <h4 className="text-[15px] font-bold text-[#0b1c30]">Pre-Session Checklist</h4>
            </div>
            <span className="text-[11px] bg-[#e5eeff] text-[#001428] font-bold px-2.5 py-0.5 rounded-full">
              {completedCount} of {checklist.length} Done
            </span>
          </div>

          <div className="space-y-2.5">
            {checklist.map((item) => (
              <div
                key={item.id}
                onClick={() => toggleChecklist(item.id)}
                className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer border transition-all ${
                  item.isDone
                    ? 'bg-[#eff4ff] border-[#d1e4ff]'
                    : 'bg-[#ffffff] border-[#e2e8f0] hover:bg-[#f8f9ff]'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    item.isDone ? 'bg-[#001428] text-white shadow-2xs' : 'bg-[#dce9ff] text-transparent'
                  }`}
                >
                  <span className="material-symbols-outlined text-[13px] font-bold">check</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className={`text-[13px] font-bold ${item.isDone ? 'text-[#001428]' : 'text-[#0b1c30]'}`}>
                      {item.label}
                    </p>
                    {item.actionLabel && (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          if (item.actionLabel === 'Try Now') onOpenChamber();
                        }}
                        className="text-[11px] font-bold text-[#a73a00] hover:underline"
                      >
                        {item.actionLabel}
                      </span>
                    )}
                  </div>
                  {item.fileName ? (
                    <div className="flex items-center gap-1.5 mt-1 text-[#001428]">
                      <span className="material-symbols-outlined text-[15px]">description</span>
                      <span className="text-[11px] font-semibold truncate">{item.fileName}</span>
                      <span className="text-[10px] text-[#74777e] shrink-0">({item.fileSize})</span>
                    </div>
                  ) : (
                    <p className="text-[11px] text-[#43474d] mt-0.5">{item.subtext}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* AI Companion Advice Note */}
        <section className="bg-[#eff4ff] rounded-2xl p-4 flex items-start gap-3 z-10 border border-[#d1e4ff]/60">
          <div className="w-9 h-9 rounded-xl bg-[#ffdbce] flex items-center justify-center text-[#a73a00] shrink-0">
            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              psychology
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#a73a00]">
                Mentora Assistant Insight
              </span>
              <span className="text-[10px] bg-[#ffffff] text-[#43474d] px-1.5 py-0.2 rounded font-semibold border border-[#e2e8f0]">
                Summary Sync
              </span>
            </div>
            <p className="text-[12px] text-[#43474d] leading-relaxed">
              Live automated transcripts and an indexed LaTeX equation breakdown will be generated in your workspace immediately post-session.
            </p>
          </div>
        </section>

        {/* Academic Department Context Graphic */}
        <section className="rounded-2xl overflow-hidden shadow-sm relative h-28 bg-[#dce9ff] z-10">
          <div
            className="w-full h-full bg-cover bg-center"
            style={{
              backgroundImage: `url('https://lh3.googleusercontent.com/aida-public/AB6AXuBZuugSxFH7RhQm-0n7xClmz2e4xRrB-LwjKv50y9aBNMPmMW_dCTwEpWP4UQvUC9dibu4Wq_ya-oK-b4yN6VAh9W7X85NYekO84G52hup4CGhR2DcmpVTbT2s2g_42hsH6p6IuW_q-EfnuCeNYfIw3VIY1trovE8ObwFZeFy-8cT6LS6sjt-NO_GrSE7evEMy83Pmmb0YusUnLHZ7YpwzWLmY1k46RcL5l7YcsxUT0zVtNxaHGPp3U')`
            }}
          >
            <div className="w-full h-full bg-[#001428]/75 backdrop-blur-[2px] p-4 flex flex-col justify-end text-white">
              <span className="text-[10px] uppercase tracking-wider text-[#b0c9e8] font-bold">
                Host Institution
              </span>
              <p className="text-[15px] font-bold text-white">
                {expert.institution}
              </p>
            </div>
          </div>
        </section>

        {/* Bottom Actions */}
        <footer className="pt-2 pb-10 flex flex-col items-center space-y-3 z-10">
          <button
            type="button"
            onClick={onNavigateToSessions}
            className="w-full h-13 py-3.5 rounded-xl bg-[#001428] text-white text-[14px] font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#001428]/25 hover:bg-[#0f2942] active:scale-[0.98] transition-all"
          >
            <span className="material-symbols-outlined text-[20px]">event_available</span>
            <span>Go to My Sessions</span>
          </button>
          <button
            type="button"
            onClick={onNavigateHome}
            className="text-[13px] text-[#43474d] hover:text-[#001428] transition-colors flex items-center gap-1 font-semibold py-1"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            <span>Return to Home</span>
          </button>
        </footer>
      </div>
    </main>
  );
};

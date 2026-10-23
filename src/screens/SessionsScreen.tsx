import React, { useState } from 'react';
import { InitialSession, formatNaira } from '../data/expertsData';

interface SessionsScreenProps {
  sessions: InitialSession[];
  onOpenChamber: (session: InitialSession) => void;
  onNavigateHome: () => void;
  onNavigateExplore: () => void;
  onCancelSession: (sessionId: string) => void;
  onUpdateSessionFeedback?: (sessionId: string, rating: number, feedback: string) => void;
  onMarkSessionCompleted?: (sessionId: string) => void;
}

export const SessionsScreen: React.FC<SessionsScreenProps> = ({
  sessions,
  onOpenChamber,
  onNavigateHome,
  onNavigateExplore,
  onCancelSession,
  onUpdateSessionFeedback,
  onMarkSessionCompleted
}) => {
  const [filterTab, setFilterTab] = useState<'upcoming' | 'completed' | 'all'>('upcoming');
  const [expandedChecklistSessionId, setExpandedChecklistSessionId] = useState<string | null>(null);

  // Feedback form state
  const [activeFeedbackSessionId, setActiveFeedbackSessionId] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [feedbackTags, setFeedbackTags] = useState<string[]>(['Clear Explanations', 'Deep Academic Insight']);
  const [feedbackSubmittedIds, setFeedbackSubmittedIds] = useState<Record<string, { rating: number; text: string }>>({
    'sample-completed-1': {
      rating: 5,
      text: 'Dr. Thorne helped refine the toric code syndrome extraction simulation. Immensely valuable insights!'
    }
  });

  const availableTags = [
    'Clear Explanations',
    'Deep Academic Insight',
    'Actionable Paper Critique',
    'Patient & Rigorous',
    'LaTeX Whiteboard Mastery'
  ];

  const toggleFeedbackTag = (tag: string) => {
    if (feedbackTags.includes(tag)) {
      setFeedbackTags(feedbackTags.filter((t) => t !== tag));
    } else {
      setFeedbackTags([...feedbackTags, tag]);
    }
  };

  const handleOpenFeedback = (session: InitialSession) => {
    setActiveFeedbackSessionId(session.id);
    setFeedbackRating(session.rating || 5);
    setFeedbackText(session.feedback || '');
  };

  const handleSubmitFeedback = (sessionId: string) => {
    const finalFeedback = feedbackText.trim()
      ? `${feedbackText.trim()} [Tags: ${feedbackTags.join(', ')}]`
      : `Outstanding colloquium! [Tags: ${feedbackTags.join(', ')}]`;

    setFeedbackSubmittedIds((prev) => ({
      ...prev,
      [sessionId]: { rating: feedbackRating, text: finalFeedback }
    }));

    if (onUpdateSessionFeedback) {
      onUpdateSessionFeedback(sessionId, feedbackRating, finalFeedback);
    }
    setActiveFeedbackSessionId(null);
  };

  const displayedSessions = sessions.filter((s) => {
    if (filterTab === 'upcoming') return s.status === 'upcoming';
    if (filterTab === 'completed') return s.status === 'completed';
    return true;
  });

  return (
    <main className="flex flex-col relative w-full pt-6 pb-28 bg-[#f8f9ff] flex-1 min-h-screen max-w-4xl mx-auto px-4">
      <div className="flex flex-col w-full space-y-4">
        {/* Header Title */}
        <div className="flex items-center justify-between pt-1">
          <div>
            <h1 className="text-[24px] font-bold text-[#001428] tracking-tight">My Mentorship Sessions</h1>
            <p className="text-[12px] text-[#43474d]">Manage your 1:1 faculty colloquia, prep checklists, and mentor ratings</p>
          </div>
          <button
            type="button"
            onClick={onNavigateExplore}
            className="px-3.5 py-2 rounded-xl bg-[#001428] text-white text-[12px] font-bold shadow-xs hover:bg-[#0f2942] active:scale-95 transition-all flex items-center gap-1"
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
            className={`flex-1 py-2 rounded-lg text-[12px] font-bold transition-colors ${
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
            className={`flex-1 py-2 rounded-lg text-[12px] font-bold transition-colors ${
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
            className={`flex-1 py-2 rounded-lg text-[12px] font-bold transition-colors ${
              filterTab === 'all'
                ? 'bg-[#ffffff] text-[#001428] shadow-xs'
                : 'text-[#43474d] hover:text-[#001428]'
            }`}
          >
            All Sessions ({sessions.length})
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
              Explore 180+ verified scholars across MIT, Oxford, and Stanford to schedule your next 1:1 advisory session.
            </p>
            <button
              type="button"
              onClick={onNavigateExplore}
              className="mt-4 px-5 py-2.5 rounded-xl bg-[#001428] text-white text-[13px] font-bold shadow-md hover:bg-[#0f2942]"
            >
              Explore Faculty Directory
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {displayedSessions.map((s) => {
              const isChecklistOpen = expandedChecklistSessionId === s.id;
              const isFeedbackFormOpen = activeFeedbackSessionId === s.id;
              const existingReview = feedbackSubmittedIds[s.id] || (s.rating ? { rating: s.rating, text: s.feedback || '' } : null);

              return (
                <div
                  key={s.id}
                  className="bg-[#ffffff] rounded-2xl p-4 sm:p-5 shadow-sm border border-[#e2e8f0]/80 space-y-3.5 transition-all"
                >
                  {/* Top Status & Date */}
                  <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${s.status === 'upcoming' ? 'bg-[#fd651e] animate-pulse' : 'bg-emerald-600'}`}></span>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-[#a73a00]">
                        {s.scheduledDate}
                      </span>
                      {s.pricePaid && (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#eff4ff] text-[#001428] font-bold">
                          {formatNaira(s.pricePaid)} Paid
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-[#74777e]">{s.bookingId}</span>
                  </div>

                  {/* Mentor Details */}
                  <div className="flex items-start gap-3.5">
                    <img
                      src={s.expertAvatar}
                      alt={s.expertName}
                      className="w-13 h-13 rounded-2xl object-cover shadow-xs ring-2 ring-[#dce9ff]"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h3 className="text-[16px] font-bold text-[#001428] truncate">{s.expertName}</h3>
                        <span
                          className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1 border ${
                            s.status === 'upcoming'
                              ? 'text-[#a73a00] bg-[#ffdbce]/80 border-[#ffb599]'
                              : 'text-emerald-800 bg-emerald-100/80 border-emerald-300'
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${s.status === 'upcoming' ? 'bg-[#fd651e] animate-pulse' : 'bg-emerald-600'}`}></span>
                          <span>{s.status === 'upcoming' ? 'Upcoming' : 'Completed'}</span>
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

                  {/* Existing Review Badge if Rated */}
                  {existingReview && (
                    <div className="bg-emerald-50 rounded-xl p-3 border border-emerald-200 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-emerald-900 flex items-center gap-1">
                          <span className="material-symbols-outlined text-[15px] text-emerald-700">verified</span>
                          <span>Your Mentor Rating & Review</span>
                        </span>
                        <div className="flex items-center text-amber-500 text-[14px]">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <span
                              key={star}
                              className="material-symbols-outlined text-[16px]"
                              style={{ fontVariationSettings: star <= existingReview.rating ? "'FILL' 1" : "'FILL' 0" }}
                            >
                              star
                            </span>
                          ))}
                        </div>
                      </div>
                      {existingReview.text && (
                        <p className="text-[12px] text-emerald-900 italic">"{existingReview.text}"</p>
                      )}
                    </div>
                  )}

                  {/* Post-Session Feedback Form Modal/Inline when Completed */}
                  {isFeedbackFormOpen && (
                    <div className="bg-[#ffffff] rounded-xl p-4 border-2 border-[#001428] shadow-md space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="text-[14px] font-bold text-[#001428]">Rate & Review {s.expertName}</h4>
                          <p className="text-[11px] text-[#43474d]">Your feedback helps the academic community calibrate mentorship quality.</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveFeedbackSessionId(null)}
                          className="text-[#74777e] hover:text-[#001428]"
                        >
                          <span className="material-symbols-outlined text-[18px]">close</span>
                        </button>
                      </div>

                      {/* Interactive Stars */}
                      <div className="flex items-center gap-1.5 py-1">
                        <span className="text-[12px] font-bold text-[#0b1c30] mr-2">Overall Score:</span>
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            onClick={() => setFeedbackRating(star)}
                            className="p-1 text-amber-500 hover:scale-110 transition-transform"
                          >
                            <span
                              className="material-symbols-outlined text-[26px]"
                              style={{ fontVariationSettings: star <= feedbackRating ? "'FILL' 1" : "'FILL' 0" }}
                            >
                              star
                            </span>
                          </button>
                        ))}
                        <span className="text-[12px] font-bold text-[#a73a00] ml-2">
                          {feedbackRating === 5 ? 'Exceptional (5/5)' : feedbackRating === 4 ? 'Very Good (4/5)' : `${feedbackRating}/5`}
                        </span>
                      </div>

                      {/* Attribute Badges */}
                      <div>
                        <span className="text-[11px] font-bold text-[#43474d] block mb-1.5">What stood out most?</span>
                        <div className="flex flex-wrap gap-1.5">
                          {availableTags.map((tag) => {
                            const isSelected = feedbackTags.includes(tag);
                            return (
                              <button
                                key={tag}
                                type="button"
                                onClick={() => toggleFeedbackTag(tag)}
                                className={`px-2.5 py-1 rounded-full text-[11px] font-bold transition-all ${
                                  isSelected
                                    ? 'bg-[#001428] text-white shadow-2xs'
                                    : 'bg-[#eff4ff] text-[#001428] hover:bg-[#dce9ff]'
                                }`}
                              >
                                {isSelected ? '✓ ' : '+ '}{tag}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Text Review */}
                      <div>
                        <label className="text-[11px] font-bold text-[#43474d] block mb-1">
                          Written Recommendation for Fellow Scholars:
                        </label>
                        <textarea
                          rows={3}
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Highlight specific guidance, methodology breakthroughs, or code review advice that helped you..."
                          className="w-full bg-[#f8f9ff] rounded-xl p-2.5 text-[12px] text-[#0b1c30] border border-[#d1e4ff] focus:outline-none focus:border-[#001428]"
                        />
                      </div>

                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setActiveFeedbackSessionId(null)}
                          className="px-3 py-1.5 rounded-lg text-[12px] font-bold text-[#43474d] hover:bg-[#eff4ff]"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSubmitFeedback(s.id)}
                          className="px-4 py-2 rounded-xl bg-[#001428] hover:bg-[#0f2942] text-white text-[12px] font-bold shadow-sm active:scale-95 transition-all"
                        >
                          Submit Mentor Rating
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
                    {s.status === 'upcoming' ? (
                      <>
                        <button
                          type="button"
                          onClick={() => onOpenChamber(s)}
                          className="py-2.5 px-3 rounded-xl bg-[#001428] hover:bg-[#0f2942] text-white text-[12px] font-bold flex items-center justify-center gap-1.5 shadow-sm active:scale-95 transition-all"
                        >
                          <span className="material-symbols-outlined text-[16px]">videocam</span>
                          <span>Enter Chamber</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setExpandedChecklistSessionId(isChecklistOpen ? null : s.id)}
                          className="py-2.5 px-3 rounded-xl bg-[#e5eeff] hover:bg-[#dce9ff] text-[#001428] text-[12px] font-bold flex items-center justify-center gap-1.5 transition-all"
                        >
                          <span className="material-symbols-outlined text-[16px]">checklist</span>
                          <span>{isChecklistOpen ? 'Hide Prep' : 'Pre-Session Prep'}</span>
                        </button>
                        {/* Simulation button to mark as completed so learner can rate */}
                        <button
                          type="button"
                          onClick={() => {
                            if (onMarkSessionCompleted) {
                              onMarkSessionCompleted(s.id);
                            }
                          }}
                          className="col-span-2 sm:col-span-1 py-2.5 px-3 rounded-xl bg-[#eff4ff] hover:bg-[#dce9ff] text-[#a73a00] text-[11px] font-bold flex items-center justify-center gap-1 border border-[#ffdbce] transition-all"
                          title="Simulate session completion to test feedback flow"
                        >
                          <span className="material-symbols-outlined text-[14px]">done_all</span>
                          <span>Mark Completed</span>
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => handleOpenFeedback(s)}
                          className="py-2.5 px-3 rounded-xl bg-[#001428] hover:bg-[#0f2942] text-white text-[12px] font-bold flex items-center justify-center gap-1.5 shadow-sm active:scale-95 transition-all"
                        >
                          <span className="material-symbols-outlined text-[16px]">rate_review</span>
                          <span>{existingReview ? 'Update Rating' : 'Rate Mentor'}</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => onOpenChamber(s)}
                          className="py-2.5 px-3 rounded-xl bg-[#e5eeff] hover:bg-[#dce9ff] text-[#001428] text-[12px] font-bold flex items-center justify-center gap-1.5 transition-all"
                        >
                          <span className="material-symbols-outlined text-[16px]">description</span>
                          <span>View Transcripts</span>
                        </button>
                      </>
                    )}
                  </div>

                  {/* Collapsible Pre-Session Prep Checklist */}
                  {isChecklistOpen && (
                    <div className="pt-2 border-t border-[#e2e8f0] space-y-2 text-xs">
                      <span className="font-bold text-[#001428] uppercase text-[10px] tracking-wider block">
                        Academic Prep Checklist:
                      </span>
                      {s.checklist.map((chk) => (
                        <div
                          key={chk.id}
                          className="flex items-center gap-2 p-2.5 rounded-lg bg-[#f8f9ff] border border-[#e2e8f0]"
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

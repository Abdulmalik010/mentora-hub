import React, { useState, useRef, useEffect } from 'react';
import { Expert } from '../data/expertsData';
import { ChatMessage, INITIAL_CHAT_MESSAGES, callGeminiChat } from '../services/aiAdvisor';

interface AIChatScreenProps {
  onNavigate: (screen: string) => void;
  onSelectExpert: (expert: Expert) => void;
  onBookExpert: (expert: Expert) => void;
  allExperts: Expert[];
  initialPrompt?: string;
  onClearInitialPrompt?: () => void;
  academicLevel?: string;
  interests?: string[];
}

export const AIChatScreen: React.FC<AIChatScreenProps> = ({
  onNavigate,
  onSelectExpert,
  onBookExpert,
  allExperts,
  initialPrompt,
  onClearInitialPrompt,
  academicLevel = 'PhD',
  interests = ['Quantum Computing', 'Cognitive Neuroscience', 'Artificial Intelligence & ML']
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES);
  const [inputVal, setInputVal] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFile, setAttachedFile] = useState<{ name: string; size: string } | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [activePrompts, setActivePrompts] = useState<string[]>([
    'Quantum fault tolerance & surface codes',
    'Autonomous robotics & motion planning',
    'Genomic therapeutics & CRISPR',
    'AI governance & copyright law'
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Handle incoming initial prompt from other screens (e.g. Home suggested inquiries)
  useEffect(() => {
    if (initialPrompt && initialPrompt.trim()) {
      handleSend(initialPrompt);
      if (onClearInitialPrompt) onClearInitialPrompt();
    }
  }, [initialPrompt]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputVal;
    if (!text.trim() && !attachedFile) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      delivered: true,
      attachment: attachedFile || undefined
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInputVal('');
    setAttachedFile(null);
    setIsTyping(true);

    // Format chat history for Gemini API
    const historyPayload = updatedMessages.map((m) => ({
      role: (m.sender === 'user' ? 'user' : 'model') as 'user' | 'model',
      text: m.text
    }));

    // Call Gemini API through full-stack backend
    try {
      const response = await callGeminiChat(
        userMsg.text,
        historyPayload,
        academicLevel,
        interests,
        allExperts
      );

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: response.text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        expertRecommendations:
          response.recommendedExperts && response.recommendedExperts.length > 0
            ? response.recommendedExperts
            : undefined,
        suggestedReplies: response.quickPrompts
      };

      setMessages((prev) => [...prev, aiMsg]);
      if (response.quickPrompts && response.quickPrompts.length > 0) {
        setActivePrompts(response.quickPrompts);
      }
    } catch (err) {
      console.error('Failed to get Gemini response:', err);
    } finally {
      setIsTyping(false);
    }
  };

  const handlePromptClick = (prompt: string) => {
    handleSend(prompt);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAttachedFile({
        name: file.name,
        size: `${(file.size / 1024).toFixed(0)} KB`
      });
    }
  };

  const handleResetChat = () => {
    if (window.confirm('Reset conversation and begin a new academic inquiry?')) {
      setMessages(INITIAL_CHAT_MESSAGES);
      setActivePrompts([
        'Quantum fault tolerance & surface codes',
        'Autonomous robotics & motion planning',
        'Genomic therapeutics & CRISPR',
        'AI governance & copyright law'
      ]);
    }
  };

  return (
    <main className="flex flex-col relative w-full pt-16 pb-24 bg-[#f8f9ff] flex-1 min-h-screen max-w-lg mx-auto">
      {/* Sticky Academic Intelligence Sub-Header */}
      <div className="sticky top-16 z-40 px-4 py-2 bg-[#f8f9ff]/95 backdrop-blur-md shadow-xs border-b border-[#e2e8f0]/60 flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="relative shrink-0">
              <div className="w-8 h-8 rounded-full bg-[#0f2942] text-white flex items-center justify-center shadow-xs">
                <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                  auto_awesome
                </span>
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full ring-2 ring-[#f8f9ff]"></span>
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5">
                <h1 className="text-[14px] font-bold text-[#001428] truncate leading-tight">
                  Mentora AI Scholar
                </h1>
                <span className="px-1.5 py-0.5 rounded-full bg-[#ffdbce] text-[#7f2b00] text-[10px] tracking-wide uppercase font-bold">
                  Gemini 3.8
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[#43474d]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-[11px] truncate text-[#43474d]">
                  Active Faculty Matching • 8 Specialists
                </span>
              </div>
            </div>
          </div>

          {/* Action items & Topic pill */}
          <div className="flex items-center gap-1.5">
            <div className="hidden xs:flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#dce9ff] text-[#0f2942] text-[11px] font-semibold">
              <span className="material-symbols-outlined text-[13px] text-[#a73a00]">tune</span>
              <span>{academicLevel} Track</span>
            </div>
            <button
              type="button"
              aria-label="Restart dialogue"
              onClick={handleResetChat}
              className="w-8 h-8 rounded-full bg-[#e5eeff] hover:bg-[#dce9ff] text-[#0b1c30] flex items-center justify-center active:scale-95 transition-all"
              title="New Session"
            >
              <span className="material-symbols-outlined text-[18px]">refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Chat Stream Container */}
      <div className="flex flex-col px-4 py-4 space-y-4">
        {/* Timeline Badge */}
        <div className="flex items-center justify-center my-1">
          <span className="px-3 py-1 rounded-full bg-[#eff4ff] text-[#43474d] text-[11px] font-semibold shadow-2xs border border-[#d1e4ff]/50">
            Live Consultation Stream • Mentora AI & Gemini
          </span>
        </div>

        {/* Messages */}
        {messages.map((msg) => (
          <div key={msg.id} className="w-full">
            {msg.sender === 'user' ? (
              /* User Bubble */
              <div className="flex items-end justify-end gap-2 ml-auto max-w-[90%]">
                <div className="flex flex-col items-end gap-1">
                  <div className="bg-[#001428] text-white p-3.5 rounded-2xl rounded-tr-sm shadow-md">
                    {msg.attachment && (
                      <div className="mb-2 p-2 bg-white/10 rounded-lg flex items-center gap-2 text-xs">
                        <span className="material-symbols-outlined text-[16px] text-[#ffb599]">description</span>
                        <span className="font-semibold truncate">{msg.attachment.name}</span>
                        <span className="text-white/60">({msg.attachment.size})</span>
                      </div>
                    )}
                    <p className="text-[13px] leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-[#74777e] pr-1">
                    <span>{msg.timestamp}</span>
                    <span>•</span>
                    <span className="text-[#a73a00] font-medium">Delivered</span>
                    <span className="material-symbols-outlined text-[14px] text-[#a73a00]">done_all</span>
                  </div>
                </div>
              </div>
            ) : (
              /* AI Response Node */
              <div className="flex items-start gap-2 max-w-full">
                <div className="w-8 h-8 rounded-full bg-[#0f2942] text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
                  <span className="material-symbols-outlined text-[17px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    neurology
                  </span>
                </div>
                <div className="flex flex-col gap-3 flex-1 min-w-0">
                  {/* Synthesis Bubble */}
                  <div className="bg-[#ffffff] text-[#0b1c30] p-3.5 rounded-2xl rounded-tl-sm shadow-sm border border-[#e2e8f0]/80 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] text-[#001428] font-bold">
                        Mentora Academic Advisor
                      </span>
                      <span className="text-[11px] text-[#74777e]">{msg.timestamp}</span>
                    </div>

                    <p className="text-[13px] text-[#0b1c30] leading-relaxed whitespace-pre-wrap">
                      {msg.text}
                    </p>

                    {/* Benchmark Matrix Card if present */}
                    {msg.benchmarkMatrix && (
                      <div className="rounded-xl bg-[#eff4ff] p-2.5 space-y-2 border border-[#d1e4ff]/60">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-[#001428] uppercase tracking-wider">
                            {msg.benchmarkMatrix.title}
                          </span>
                          <span className="text-[11px] text-[#a73a00] font-semibold">
                            {msg.benchmarkMatrix.arxivRef}
                          </span>
                        </div>
                        <div className="space-y-1.5 text-[12px]">
                          {msg.benchmarkMatrix.items.map((it, idx) => (
                            <div key={idx} className="flex items-start gap-2">
                              <span className="material-symbols-outlined text-[#a73a00] text-[16px] mt-0.5 shrink-0">
                                {it.icon}
                              </span>
                              <p className="text-[#0b1c30]">
                                <strong className="font-bold">{it.title}: </strong>
                                {it.desc}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* RECOMMENDATION SECTION: Tappable Expert Cards that open Profile */}
                  {(msg.expertRecommendations || (msg.expertRecommendation ? [msg.expertRecommendation] : []))?.length > 0 && (
                    <div className="space-y-2.5 pt-1">
                      <div className="flex items-center justify-between px-1">
                        <span className="text-[11px] uppercase tracking-wider text-[#001428] font-bold flex items-center gap-1">
                          <span className="material-symbols-outlined text-[15px] text-[#fd651e]" style={{ fontVariationSettings: "'FILL' 1" }}>
                            stars
                          </span>
                          <span>Recommended Mentors ({(msg.expertRecommendations || (msg.expertRecommendation ? [msg.expertRecommendation] : [])).length} Matches)</span>
                        </span>
                        <span className="text-[10px] text-[#74777e] font-semibold">Tap card to view profile</span>
                      </div>

                      <div className="space-y-3">
                        {(msg.expertRecommendations || (msg.expertRecommendation ? [msg.expertRecommendation] : [])).map((expert) => (
                          <div
                            key={expert.id}
                            onClick={() => onSelectExpert(expert)}
                            className="bg-[#ffffff] rounded-2xl p-3.5 shadow-md border border-[#e2e8f0] flex flex-col gap-2.5 relative overflow-hidden transition-all hover:shadow-lg hover:border-[#a73a00] cursor-pointer group active:scale-[0.99]"
                          >
                            {/* Top compatibility banner */}
                            <div className="flex items-center justify-between bg-[#dce9ff] px-3 py-1.5 rounded-xl">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className="material-symbols-outlined text-[#a73a00] text-[18px]"
                                  style={{ fontVariationSettings: "'FILL' 1" }}
                                >
                                  verified
                                </span>
                                <span className="text-[11px] font-bold text-[#001428]">
                                  {expert.domain} Specialist
                                </span>
                              </div>
                              <div className="flex items-center gap-1 bg-[#a73a00] text-white px-2 py-0.5 rounded-full text-[11px] font-bold">
                                <span className="material-symbols-outlined text-[12px]">bolt</span>
                                <span>{expert.matchScore}% Fit</span>
                              </div>
                            </div>

                            {/* Scholar Profile Row */}
                            <div className="flex items-start gap-3 pt-1">
                              <div className="relative shrink-0">
                                <img
                                  className="w-15 h-15 rounded-xl object-cover shadow-xs ring-2 ring-[#dce9ff] group-hover:scale-105 transition-transform"
                                  src={expert.avatarUrl}
                                  alt={expert.name}
                                />
                                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#ffffff] shadow flex items-center justify-center">
                                  <span className="material-symbols-outlined text-[13px] text-emerald-600 font-bold">
                                    check
                                  </span>
                                </div>
                              </div>
                              <div className="flex flex-col min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-1">
                                  <h2 className="text-[15px] text-[#001428] font-bold truncate group-hover:text-[#a73a00] transition-colors">
                                    {expert.name}
                                  </h2>
                                  <div className="flex items-center gap-0.5 text-[#a73a00] shrink-0">
                                    <span
                                      className="material-symbols-outlined text-[14px]"
                                      style={{ fontVariationSettings: "'FILL' 1" }}
                                    >
                                      star
                                    </span>
                                    <span className="text-[12px] font-bold text-[#0b1c30]">
                                      {expert.rating.toFixed(2)}
                                    </span>
                                  </div>
                                </div>
                                <p className="text-[12px] text-[#43474d] truncate">
                                  {expert.title}
                                </p>
                                <div className="flex items-center gap-1 mt-0.5">
                                  <span className="material-symbols-outlined text-[13px] text-[#0f2942]">
                                    account_balance
                                  </span>
                                  <span className="text-[11px] text-[#0f2942] font-semibold truncate">
                                    {expert.institution}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Tags */}
                            <div className="flex flex-wrap gap-1.5 pt-0.5">
                              <span className="px-2 py-0.5 rounded-full bg-[#eff4ff] text-[#001428] text-[10px] font-semibold flex items-center gap-1">
                                <span className="material-symbols-outlined text-[12px] text-[#a73a00]">auto_stories</span>
                                {expert.papersCited} Papers
                              </span>
                              {expert.tags.slice(0, 2).map((t) => (
                                <span key={t} className="px-2 py-0.5 rounded-full bg-[#e5eeff] text-[#43474d] text-[10px] font-medium">
                                  {t}
                                </span>
                              ))}
                              <span className="px-2 py-0.5 rounded-full bg-[#ffdbce] text-[#7f2b00] text-[10px] font-bold ml-auto">
                                ${expert.hourlyRate}/45m
                              </span>
                            </div>

                            {/* Next Availability Slot */}
                            <div className="flex items-center justify-between px-2.5 py-1.5 rounded-xl bg-[#eff4ff] text-[#0b1c30]">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span className="material-symbols-outlined text-[#a73a00] text-[16px]">calendar_today</span>
                                <span className="text-[11px] font-semibold text-[#001428] truncate">
                                  Next: {expert.nextSlotText}
                                </span>
                              </div>
                              <span className="text-[11px] font-bold text-[#a73a00] flex items-center gap-0.5">
                                <span>Profile</span>
                                <span className="material-symbols-outlined text-[14px]">chevron_right</span>
                              </span>
                            </div>

                            {/* Action Buttons Group */}
                            <div className="grid grid-cols-2 gap-2 pt-1">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSelectExpert(expert);
                                }}
                                className="w-full py-2 px-3 rounded-xl bg-[#dce9ff] hover:bg-[#d3e4fe] text-[#001428] text-[12px] font-bold flex items-center justify-center gap-1.5 active:scale-98 transition-all"
                              >
                                <span className="material-symbols-outlined text-[15px]">school</span>
                                <span>View Profile</span>
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onBookExpert(expert);
                                }}
                                className="w-full py-2 px-3 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[12px] font-bold flex items-center justify-center gap-1.5 shadow-sm active:scale-98 transition-all"
                              >
                                <span
                                  className="material-symbols-outlined text-[15px]"
                                  style={{ fontVariationSettings: "'FILL' 1" }}
                                >
                                  event_available
                                </span>
                                <span>Book Consult</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Follow-up AI Suggestion if any */}
                  {msg.followUpSuggestion && (
                    <div className="bg-[#ffffff] text-[#0b1c30] p-3 rounded-2xl rounded-tl-sm shadow-xs border border-[#e2e8f0]/80 flex items-start gap-2.5">
                      <span
                        className="material-symbols-outlined text-[#a73a00] text-[18px] shrink-0 mt-0.5"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        tips_and_updates
                      </span>
                      <p className="text-[12px] text-[#0b1c30] leading-snug">
                        {msg.followUpSuggestion}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-start gap-2 max-w-[92%]">
            <div className="w-8 h-8 rounded-full bg-[#0f2942] text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
              <span className="material-symbols-outlined text-[17px]">neurology</span>
            </div>
            <div className="bg-[#ffffff] text-[#0b1c30] p-3.5 rounded-2xl rounded-tl-sm shadow-sm border border-[#e2e8f0] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#a73a00] animate-ping"></span>
              <span className="text-[13px] text-[#43474d]">
                Mentora AI analyzing inquiry with Gemini 3.8 & finding faculty matches...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sticky Bottom Controls & Input Area */}
      <div className="sticky bottom-0 z-30 w-full bg-[#f8f9ff]/95 backdrop-blur-lg pt-2 pb-3 shadow-[0_-4px_16px_rgba(15,41,66,0.06)] px-4 flex flex-col gap-2 border-t border-[#e2e8f0]/60">
        {/* Interactive Prompt Suggestions Carousel */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5 -mx-4 px-4">
          {activePrompts.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handlePromptClick(p)}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#ffffff] hover:bg-[#e5eeff] text-[#001428] shadow-xs text-[12px] font-semibold border border-[#e2e8f0] transition-colors active:scale-95"
            >
              <span className="material-symbols-outlined text-[#a73a00] text-[16px]">chat_bubble_outline</span>
              <span>{p}</span>
            </button>
          ))}
        </div>

        {/* File Attachment Pill Preview if uploaded */}
        {attachedFile && (
          <div className="flex items-center justify-between p-2 bg-[#eff4ff] border border-[#d1e4ff] rounded-xl text-xs">
            <div className="flex items-center gap-2 truncate">
              <span className="material-symbols-outlined text-[#a73a00] text-[18px]">attachment</span>
              <span className="font-bold text-[#001428] truncate">{attachedFile.name}</span>
              <span className="text-[#43474d]">({attachedFile.size})</span>
            </div>
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              className="w-5 h-5 rounded-full hover:bg-[#dce9ff] flex items-center justify-center text-[#74777e]"
            >
              <span className="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        )}

        {/* Active Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 bg-[#ffffff] rounded-2xl p-1.5 shadow-md border border-[#e2e8f0]"
        >
          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.tex,.txt,.docx"
            className="hidden"
          />

          {/* Attachment Trigger */}
          <button
            type="button"
            aria-label="Upload proposal PDF or TeX file"
            onClick={() => fileInputRef.current?.click()}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-[#43474d] hover:text-[#001428] hover:bg-[#e5eeff] transition-colors shrink-0"
          >
            <span className="material-symbols-outlined text-[20px]">attach_file</span>
          </button>

          {/* Text Field */}
          <input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            className="flex-1 bg-transparent border-0 outline-none text-[13px] text-[#0b1c30] placeholder:text-[#74777e] py-2 px-1 focus:ring-0 min-w-0"
            placeholder={
              isListening ? 'Listening to scholarly query...' : 'Ask Mentora AI or state your research goal...'
            }
            type="text"
          />

          {/* Voice Dictation Trigger */}
          <button
            type="button"
            aria-label="Voice input"
            onClick={() => {
              setIsListening(!isListening);
              if (!isListening) {
                setInputVal('I am a PhD student looking for guidance on quantum fault tolerance');
                setTimeout(() => setIsListening(false), 1200);
              }
            }}
            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-colors shrink-0 ${
              isListening ? 'text-[#a73a00] bg-[#ffdbce]' : 'text-[#43474d] hover:text-[#a73a00]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">mic</span>
          </button>

          {/* Submit / Send Button */}
          <button
            type="submit"
            aria-label="Send message"
            className="w-10 h-10 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white flex items-center justify-center shadow-md active:scale-90 transition-transform shrink-0"
          >
            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              send
            </span>
          </button>
        </form>

        <div className="flex items-center justify-center gap-1.5 text-[#43474d]">
          <span className="material-symbols-outlined text-[13px]">lock</span>
          <span className="text-[11px] text-center">
            Encrypted institutional link • Connected to Gemini API & Mentora Scholars
          </span>
        </div>
      </div>
    </main>
  );
};

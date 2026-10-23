import React, { useState, useRef, useEffect } from 'react';
import { Expert, formatNaira } from '../data/expertsData';
import { ChatMessage, INITIAL_CHAT_MESSAGES, streamGeminiChat } from '../services/aiAdvisor';

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
    // Show typing indicator immediately
    setIsTyping(true);

    // Prepare streaming AI response placeholder
    const streamingAiMsgId = `ai-${Date.now()}`;
    let hasCreatedStreamingBubble = false;

    // Format chat history for Gemini API (only last 6 messages)
    const historyPayload = updatedMessages.slice(-6).map((m) => ({
      role: (m.sender === 'user' ? 'user' : 'model') as 'user' | 'model',
      text: m.text
    }));

    try {
      const response = await streamGeminiChat(
        userMsg.text,
        historyPayload,
        academicLevel,
        interests,
        allExperts,
        (textSoFar: string) => {
          // As soon as first token arrives, replace typing indicator with streaming text
          setIsTyping(false);
          setMessages((prev) => {
            const existingIdx = prev.findIndex((m) => m.id === streamingAiMsgId);
            if (existingIdx !== -1) {
              const copy = [...prev];
              copy[existingIdx] = {
                ...copy[existingIdx],
                text: textSoFar
              };
              return copy;
            } else {
              hasCreatedStreamingBubble = true;
              return [
                ...prev,
                {
                  id: streamingAiMsgId,
                  sender: 'ai',
                  text: textSoFar,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
              ];
            }
          });
        }
      );

      // Finalize with expert recommendations and suggested replies
      setMessages((prev) => {
        const existingIdx = prev.findIndex((m) => m.id === streamingAiMsgId);
        const finalMsg: ChatMessage = {
          id: streamingAiMsgId,
          sender: 'ai',
          text: response.text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          expertRecommendations:
            response.recommendedExperts && response.recommendedExperts.length > 0
              ? response.recommendedExperts
              : undefined,
          suggestedReplies: response.quickPrompts
        };

        if (existingIdx !== -1) {
          const copy = [...prev];
          copy[existingIdx] = finalMsg;
          return copy;
        } else {
          return [...prev, finalMsg];
        }
      });

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
    <main className="flex flex-col relative w-full pt-4 pb-28 bg-[#f8f9ff] flex-1 min-h-screen max-w-3xl mx-auto">
      {/* Sticky Academic Intelligence Sub-Header */}
      <div className="sticky top-0 z-30 px-4 py-2 bg-[#f8f9ff]/95 backdrop-blur-md shadow-xs border-b border-[#e2e8f0]/60 flex flex-col gap-1 rounded-2xl mb-3">
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
                  Fast Flash Stream
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[#43474d]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-[11px] truncate text-[#43474d]">
                  Active Faculty Matching • Rates in ₦ Naira
                </span>
              </div>
            </div>
          </div>

          {/* Action items & Track pill */}
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
      <div className="flex flex-col px-4 py-2 space-y-4">
        {/* Timeline Badge */}
        <div className="flex items-center justify-center my-1">
          <span className="px-3 py-1 rounded-full bg-[#eff4ff] text-[#43474d] text-[11px] font-semibold shadow-2xs border border-[#d1e4ff]/50">
            Live Stream • Under 80 Words • ₦5,000–₦25,000
          </span>
        </div>

        {/* Messages */}
        {messages.map((msg) => (
          <div key={msg.id} className="w-full">
            {msg.sender === 'user' ? (
              /* User Bubble */
              <div className="flex items-end justify-end gap-2 ml-auto max-w-[85%]">
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
                  <div className="bg-[#ffffff] text-[#0b1c30] p-4 rounded-2xl rounded-tl-sm shadow-sm border border-[#e2e8f0]/80 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] text-[#001428] font-bold flex items-center gap-1">
                        <span>Mentora Advisor</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
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
                          <span>Matched Mentors ({(msg.expertRecommendations || (msg.expertRecommendation ? [msg.expertRecommendation] : [])).length})</span>
                        </span>
                        <span className="text-[10px] text-[#74777e] font-semibold">Tap card to view profile</span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {(msg.expertRecommendations || (msg.expertRecommendation ? [msg.expertRecommendation] : [])).map((expert) => (
                          <div
                            key={expert.id}
                            onClick={() => onSelectExpert(expert)}
                            className="bg-[#ffffff] rounded-2xl p-3.5 shadow-md border border-[#e2e8f0] flex flex-col gap-2.5 relative overflow-hidden transition-all hover:shadow-lg hover:border-[#a73a00] cursor-pointer group active:scale-[0.99]"
                          >
                            {/* Top compatibility banner */}
                            <div className="flex items-center justify-between bg-[#dce9ff] px-2.5 py-1 rounded-xl">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span
                                  className="material-symbols-outlined text-[#a73a00] text-[16px] shrink-0"
                                  style={{ fontVariationSettings: "'FILL' 1" }}
                                >
                                  verified
                                </span>
                                <span className="text-[11px] font-bold text-[#001428] truncate">
                                  {expert.domain}
                                </span>
                              </div>
                              <div className="flex items-center gap-0.5 bg-[#a73a00] text-white px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0">
                                <span className="material-symbols-outlined text-[11px]">bolt</span>
                                <span>{expert.matchScore}% Fit</span>
                              </div>
                            </div>

                            {/* Scholar Profile Row */}
                            <div className="flex items-start gap-3 pt-0.5">
                              <div className="relative shrink-0">
                                <img
                                  className="w-13 h-13 rounded-xl object-cover shadow-xs ring-2 ring-[#dce9ff] group-hover:scale-105 transition-transform"
                                  src={expert.avatarUrl}
                                  alt={expert.name}
                                />
                                <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-[#ffffff] shadow flex items-center justify-center">
                                  <span className="material-symbols-outlined text-[11px] text-emerald-600 font-bold">
                                    check
                                  </span>
                                </div>
                              </div>
                              <div className="flex flex-col min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-1">
                                  <h2 className="text-[14px] text-[#001428] font-bold truncate group-hover:text-[#a73a00] transition-colors">
                                    {expert.name}
                                  </h2>
                                  <div className="flex items-center gap-0.5 text-[#a73a00] shrink-0">
                                    <span
                                      className="material-symbols-outlined text-[13px]"
                                      style={{ fontVariationSettings: "'FILL' 1" }}
                                    >
                                      star
                                    </span>
                                    <span className="text-[11px] font-bold text-[#0b1c30]">
                                      {expert.rating.toFixed(2)}
                                    </span>
                                  </div>
                                </div>
                                <p className="text-[11px] text-[#43474d] truncate">
                                  {expert.title}
                                </p>
                                <div className="flex items-center gap-1 mt-0.5">
                                  <span className="material-symbols-outlined text-[12px] text-[#0f2942]">
                                    account_balance
                                  </span>
                                  <span className="text-[10px] text-[#0f2942] font-semibold truncate">
                                    {expert.institution}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Tags & Naira Price */}
                            <div className="flex items-center justify-between pt-0.5 border-t border-[#f1f5f9]">
                              <span className="text-[10px] text-[#43474d] truncate">
                                Next: {expert.nextSlotDate}
                              </span>
                              <span className="px-2 py-0.5 rounded-full bg-[#ffdbce] text-[#7f2b00] text-[11px] font-bold">
                                {formatNaira(expert.hourlyRate)}/45m
                              </span>
                            </div>

                            {/* Action Buttons */}
                            <div className="grid grid-cols-2 gap-2 pt-0.5">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSelectExpert(expert);
                                }}
                                className="w-full py-1.5 px-2 rounded-xl bg-[#dce9ff] hover:bg-[#d3e4fe] text-[#001428] text-[11px] font-bold flex items-center justify-center gap-1 active:scale-98 transition-all"
                              >
                                <span>Profile</span>
                                <span className="material-symbols-outlined text-[13px]">chevron_right</span>
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onBookExpert(expert);
                                }}
                                className="w-full py-1.5 px-2 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[11px] font-bold flex items-center justify-center gap-1 shadow-xs active:scale-98 transition-all"
                              >
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

        {/* Immediate Typing indicator */}
        {isTyping && (
          <div className="flex items-start gap-2 max-w-[90%] animate-fadeIn">
            <div className="w-8 h-8 rounded-full bg-[#0f2942] text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
              <span className="material-symbols-outlined text-[17px]">neurology</span>
            </div>
            <div className="bg-[#ffffff] text-[#0b1c30] p-3 rounded-2xl rounded-tl-sm shadow-sm border border-[#e2e8f0] flex items-center gap-2">
              <span className="text-[12px] text-[#43474d] font-semibold">Mentora AI is thinking</span>
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-[#a73a00] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 bg-[#a73a00] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 bg-[#a73a00] rounded-full animate-bounce"></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Inquiry Prompts */}
      <div className="px-4 py-2">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {activePrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handlePromptClick(prompt)}
              className="shrink-0 px-3 py-1.5 rounded-full bg-[#eff4ff] hover:bg-[#dce9ff] text-[#001428] text-[11px] font-bold border border-[#d1e4ff] transition-all flex items-center gap-1.5 active:scale-95 shadow-2xs"
            >
              <span className="material-symbols-outlined text-[13px] text-[#a73a00]">auto_awesome</span>
              <span>{prompt}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sticky Bottom Input Dock */}
      <div className="sticky bottom-0 inset-x-0 bg-[#f8f9ff]/95 backdrop-blur-md border-t border-[#e2e8f0]/80 p-3 max-w-3xl mx-auto w-full">
        {attachedFile && (
          <div className="mb-2 p-2 bg-[#e5eeff] rounded-xl flex items-center justify-between text-xs border border-[#d1e4ff]">
            <div className="flex items-center gap-2 truncate">
              <span className="material-symbols-outlined text-[16px] text-[#a73a00]">attachment</span>
              <span className="font-bold text-[#001428] truncate">{attachedFile.name}</span>
              <span className="text-[#74777e]">({attachedFile.size})</span>
            </div>
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              className="w-5 h-5 rounded-full flex items-center justify-center text-[#74777e] hover:bg-white/50"
            >
              <span className="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 bg-[#ffffff] rounded-2xl p-1.5 border border-[#e2e8f0] shadow-sm focus-within:border-[#0f2942] transition-colors"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-[#74777e] hover:text-[#001428] hover:bg-[#eff4ff] transition-colors shrink-0"
            title="Attach preprint/thesis abstract"
          >
            <span className="material-symbols-outlined text-[20px]">attach_file</span>
          </button>

          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Ask anything or state your learning goal..."
            className="flex-1 bg-transparent text-[13px] text-[#0b1c30] placeholder:text-[#74777e] focus:outline-none px-1"
          />

          <button
            type="button"
            onClick={() => {
              setIsListening(!isListening);
              if (!isListening) {
                setInputVal('Quantum error correction in surface codes');
                setTimeout(() => setIsListening(false), 1200);
              }
            }}
            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-colors shrink-0 ${
              isListening ? 'text-[#fd651e] bg-[#ffdbce]' : 'text-[#74777e] hover:text-[#001428] hover:bg-[#eff4ff]'
            }`}
            title="Speech input"
          >
            <span className="material-symbols-outlined text-[20px]">mic</span>
          </button>

          <button
            type="submit"
            disabled={!inputVal.trim() && !attachedFile}
            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0 ${
              inputVal.trim() || attachedFile
                ? 'bg-[#001428] hover:bg-[#0f2942] text-white shadow-xs active:scale-95'
                : 'bg-[#e2e8f0] text-[#74777e] cursor-not-allowed'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">send</span>
          </button>
        </form>
      </div>
    </main>
  );
};

import React, { useState } from 'react';

interface VirtualChamberModalProps {
  isOpen: boolean;
  onClose: () => void;
  roomTitle?: string;
  expertName?: string;
}

export const VirtualChamberModal: React.FC<VirtualChamberModalProps> = ({
  isOpen,
  onClose,
  roomTitle = '1:1 Doctoral Colloquium',
  expertName = 'Dr. Aris Thorne'
}) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [activeTab, setActiveTab] = useState<'latex' | 'notes' | 'chat'>('latex');
  const [latexCode, setLatexCode] = useState(
    '\\mathcal{H} = -J \\sum_{\\langle i, j \\rangle} Z_i Z_j - g \\sum_{i} X_i\n\n' +
    '\\text{Toric Code Stabilizers:}\n' +
    'A_s = \\prod_{j \\in s} X_j, \\quad B_p = \\prod_{j \\in p} Z_j\n\n' +
    '\\text{Threshold Bound: } P_{\\text{err}} < 1.05\\%'
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-[#001428]/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-[#0b1c30] text-white rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden border border-[#1e3a5f] flex flex-col h-[90vh]">
        {/* Top Header */}
        <div className="p-3.5 bg-[#001428] border-b border-[#1e3a5f] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <div>
              <h3 className="text-[14px] font-bold text-white leading-tight">{roomTitle}</h3>
              <p className="text-[11px] text-[#7991af]">Encrypted Chamber • Peer Link Active with {expertName}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-[#0f2942] hover:bg-[#1e3a5f] flex items-center justify-center text-white transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Video Area */}
        <div className="grid grid-cols-2 gap-2 p-3 bg-[#001428]/60 shrink-0">
          {/* Mentor Screen */}
          <div className="relative aspect-video rounded-xl overflow-hidden bg-[#0f2942] border border-[#1e3a5f] flex items-center justify-center">
            <img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuAQvXUeV2LR8eOr1nfW_ZP3dJbQWT1d-wN8b61rvam5cMHlI4IoK_EEIkgq91cOKU4S2vvOGq0RWoq0c5o8-zRJiKdlsbEpnN7x_3w1iP3Q5iR6RQMBhSYnoo-JT_tNjtUAWaGmTDz0SkCelB5sqBSTtT8Bmov5_SrmicEoA1SHHhGFHWEm40ArRznJkN3e42CBvMqiuDwLMF85YQhYYH5_MOIvSXXvL-iBQYnm2iEjh6GWxbgOi94j"
              alt={expertName}
              className="w-full h-full object-cover"
            />
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-[#001428]/80 backdrop-blur-sm text-[11px] font-semibold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>{expertName} (Host)</span>
            </div>
          </div>

          {/* Student Screen */}
          <div className="relative aspect-video rounded-xl overflow-hidden bg-[#0f2942] border border-[#1e3a5f] flex items-center justify-center">
            {isVideoOff ? (
              <div className="w-12 h-12 rounded-full bg-[#1e3a5f] flex items-center justify-center text-white text-[16px] font-bold">
                ER
              </div>
            ) : (
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA2VTTxi1zoK5YzJ7C2Hl0DTEQPPfygc806vetOKMVnW6jxM4hDr2fX3Q8vWqEh2fYXQyhimiJjMW7Vvs5HO7p9coq6pCqKV2Ba6yzywodQE0hEze0F2lRWzDOum2eLQVV-by-mWO4tdRlLdpkWCwOXD_oC4Dc3W1rX1ra9cJTmN9sLNBocY5MOAvqIKf64EPeMQBGG0jewKa0oFJ90uafmn0vLhJJPvnEX4hJfh5kUPF6b2h_Ukcbv"
                alt="Elena Rostova"
                className="w-full h-full object-cover"
              />
            )}
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-[#001428]/80 backdrop-blur-sm text-[11px] font-semibold flex items-center gap-1.5">
              <span>Elena Rostova (You)</span>
              {isMuted && <span className="material-symbols-outlined text-red-400 text-[13px]">mic_off</span>}
            </div>
          </div>
        </div>

        {/* Interactive Workspace Area: Shared LaTeX & Notes */}
        <div className="flex-1 flex flex-col min-h-0 bg-[#071322] border-t border-[#1e3a5f]">
          <div className="flex items-center justify-between px-3 py-2 bg-[#001428] border-b border-[#1e3a5f]">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveTab('latex')}
                className={`px-3 py-1 rounded-lg text-[12px] font-semibold flex items-center gap-1.5 transition-colors ${
                  activeTab === 'latex' ? 'bg-[#0f2942] text-[#fd651e]' : 'text-[#7991af] hover:text-white'
                }`}
              >
                <span className="material-symbols-outlined text-[15px]">code</span>
                <span>Shared LaTeX Whiteboard</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('notes')}
                className={`px-3 py-1 rounded-lg text-[12px] font-semibold flex items-center gap-1.5 transition-colors ${
                  activeTab === 'notes' ? 'bg-[#0f2942] text-[#fd651e]' : 'text-[#7991af] hover:text-white'
                }`}
              >
                <span className="material-symbols-outlined text-[15px]">edit_note</span>
                <span>Colloquium Notes</span>
              </button>
            </div>
            <span className="text-[10px] uppercase font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
              Syncing Realtime
            </span>
          </div>

          <div className="flex-1 p-3 overflow-y-auto">
            {activeTab === 'latex' ? (
              <div className="space-y-3 h-full flex flex-col">
                <div className="text-[12px] text-[#7991af] flex items-center justify-between">
                  <span>Collaborative Mathematical Notation Canvas:</span>
                  <span className="text-[#adc6ff]">TeX Engine: KaTeX 0.16.8</span>
                </div>
                <textarea
                  value={latexCode}
                  onChange={(e) => setLatexCode(e.target.value)}
                  className="w-full flex-1 p-3 rounded-xl bg-[#030912] text-[#d1e4ff] font-mono text-[13px] border border-[#1e3a5f] focus:outline-none focus:border-[#fd651e] resize-none"
                  placeholder="Type or edit mathematical formulas..."
                />
                <div className="p-3 bg-[#0a1829] rounded-xl border border-[#1e3a5f]/80 text-[13px]">
                  <p className="text-[11px] font-bold text-[#7991af] uppercase mb-1">Live Formula Rendering Preview:</p>
                  <div className="font-serif italic text-white tracking-wide space-y-1">
                    <div>ℋ = -J ∑₍ᵢ,ⱼ₎ Zᵢ Zⱼ - g ∑ᵢ Xᵢ</div>
                    <div className="text-[#fd651e]">A_s = ∏ⱼ∈s Xⱼ,  B_p = ∏ⱼ∈p Zⱼ</div>
                    <div className="text-emerald-400 font-sans text-xs">P_err &lt; 1.05% (Threshold Satisfied)</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-2 text-[13px] text-[#d1e4ff]">
                <h4 className="font-bold text-white">Live Discussion Key Takeaways:</h4>
                <ul className="list-disc pl-5 space-y-1 text-[#adc6ff]">
                  <li>Color codes transversal gates save ~42% non-Clifford state distillation rounds.</li>
                  <li>Verify rotated surface code boundary conditions with 3D defect lattices.</li>
                  <li>Dr. Thorne suggested attaching pre-print Appendix B to Oxford fellowship application.</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Video Controls Bar */}
        <div className="p-3 bg-[#001428] border-t border-[#1e3a5f] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsMuted(!isMuted)}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
                isMuted ? 'bg-red-600 text-white' : 'bg-[#0f2942] hover:bg-[#1e3a5f] text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">
                {isMuted ? 'mic_off' : 'mic'}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setIsVideoOff(!isVideoOff)}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
                isVideoOff ? 'bg-red-600 text-white' : 'bg-[#0f2942] hover:bg-[#1e3a5f] text-white'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">
                {isVideoOff ? 'videocam_off' : 'videocam'}
              </span>
            </button>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-[13px] flex items-center gap-1.5 transition-colors shadow-md"
          >
            <span className="material-symbols-outlined text-[16px]">call_end</span>
            <span>Leave Chamber</span>
          </button>
        </div>
      </div>
    </div>
  );
};

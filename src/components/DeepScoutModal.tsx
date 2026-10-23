import React, { useState } from 'react';

interface DeepScoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScoutComplete: (query: string) => void;
}

export const DeepScoutModal: React.FC<DeepScoutModalProps> = ({
  isOpen,
  onClose,
  onScoutComplete
}) => {
  const [thesisQuery, setThesisQuery] = useState('');
  const [isScouting, setIsScouting] = useState(false);
  const [targetCluster, setTargetCluster] = useState('Global Tier-1 (MIT, Oxford, Stanford, ETH)');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!thesisQuery.trim()) return;

    setIsScouting(true);
    setTimeout(() => {
      setIsScouting(false);
      onScoutComplete(thesisQuery);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#001428]/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#ffffff] rounded-2xl w-full max-w-md shadow-2xl overflow-hidden border border-[#e2e8f0] flex flex-col">
        {/* Header */}
        <div className="p-4 bg-gradient-to-r from-[#001428] to-[#0f2942] text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#fd651e] text-[22px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              travel_explore
            </span>
            <div>
              <h3 className="text-[16px] font-bold">Deep AI Faculty Scout</h3>
              <p className="text-[11px] text-[#adc6ff]">Scanning 450+ universities & 12,000 active lab directors</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="text-[12px] font-bold text-[#001428] uppercase tracking-wider block mb-1">
              Your Research Proposal / Frontier Topic
            </label>
            <textarea
              value={thesisQuery}
              onChange={(e) => setThesisQuery(e.target.value)}
              placeholder="e.g. Exploring non-abelian anyon braiding in semiconductor-superconductor nanowires for fault-tolerant topological quantum memory..."
              rows={4}
              className="w-full p-3 rounded-xl bg-[#eff4ff] text-[#0b1c30] text-[13px] border border-[#d1e4ff] focus:outline-none focus:border-[#a73a00] resize-none"
              required
            />
          </div>

          <div>
            <label className="text-[12px] font-bold text-[#001428] uppercase tracking-wider block mb-1">
              Target Academic Cluster
            </label>
            <select
              value={targetCluster}
              onChange={(e) => setTargetCluster(e.target.value)}
              className="w-full p-2.5 rounded-xl bg-[#eff4ff] text-[#0b1c30] text-[13px] border border-[#d1e4ff] focus:outline-none focus:border-[#a73a00]"
            >
              <option>Global Tier-1 (MIT, Oxford, Stanford, ETH)</option>
              <option>European Research Council / Max Planck</option>
              <option>Ivy Plus & North American Laboratories</option>
              <option>Biomedical Clinical Research Centers</option>
            </select>
          </div>

          <div className="p-3 bg-[#f8f9ff] rounded-xl border border-[#e2e8f0] text-[12px] text-[#43474d] flex items-center gap-2">
            <span className="material-symbols-outlined text-[#a73a00] text-[18px]">bolt</span>
            <span>Mentora AI cross-checks grant citations, recent open office hours, and faculty review availability.</span>
          </div>

          <button
            type="submit"
            disabled={isScouting}
            className="w-full py-3 px-4 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white font-bold text-[14px] flex items-center justify-center gap-2 shadow-md transition-all active:scale-[0.98] disabled:opacity-70"
          >
            {isScouting ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                <span>Scouting Global Faculties...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
                <span>Scout Compatible Faculty</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

import React from 'react';

interface FilterModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedDomain: string;
  onSelectDomain: (domain: string) => void;
  maxPrice: number;
  onSelectMaxPrice: (price: number) => void;
  onlySubsidized: boolean;
  onToggleSubsidized: () => void;
}

export const FilterModal: React.FC<FilterModalProps> = ({
  isOpen,
  onClose,
  selectedDomain,
  onSelectDomain,
  maxPrice,
  onSelectMaxPrice,
  onlySubsidized,
  onToggleSubsidized
}) => {
  if (!isOpen) return null;

  const disciplines = [
    'All Disciplines',
    'Quantum Computing',
    'Cognitive Neuroscience',
    'Artificial Intelligence & ML',
    'Medicine & Bioengineering',
    'Constitutional Law',
    'Behavioral Economics',
    'Business & Tech Strategy'
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-[#001428]/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#ffffff] rounded-t-3xl sm:rounded-2xl w-full max-w-md shadow-2xl overflow-hidden border border-[#e2e8f0] flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 bg-[#f8f9ff] border-b border-[#e2e8f0] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#0f2942] text-[20px]">tune</span>
            <h3 className="text-[16px] font-bold text-[#001428]">Filter Scholars & Mentors</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[#74777e] hover:bg-[#e5eeff]"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 overflow-y-auto space-y-4">
          <div>
            <label className="text-[12px] font-bold text-[#001428] uppercase tracking-wider block mb-2">
              Discipline / Research Field
            </label>
            <div className="flex flex-wrap gap-1.5">
              {disciplines.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => onSelectDomain(d)}
                  className={`px-3 py-1.5 rounded-full text-[12px] font-semibold transition-all ${
                    (d === 'All Disciplines' && (!selectedDomain || selectedDomain === 'All Disciplines')) ||
                    selectedDomain === d
                      ? 'bg-[#001428] text-white shadow-xs'
                      : 'bg-[#eff4ff] text-[#0b1c30] hover:bg-[#dce9ff]'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[12px] font-bold text-[#001428] uppercase tracking-wider">
                Max Rate per Session
              </label>
              <span className="text-[14px] font-extrabold text-[#a73a00]">${maxPrice} / session</span>
            </div>
            <input
              type="range"
              min="50"
              max="150"
              step="5"
              value={maxPrice}
              onChange={(e) => onSelectMaxPrice(Number(e.target.value))}
              className="w-full accent-[#fd651e] cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-[#74777e] mt-1">
              <span>$50</span>
              <span>$100</span>
              <span>$150+</span>
            </div>
          </div>

          <div className="pt-2 border-t border-[#e2e8f0]">
            <label className="flex items-center justify-between p-3 rounded-xl bg-[#eff4ff] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#a73a00] text-[20px]">school</span>
                <div>
                  <p className="text-[13px] font-bold text-[#001428]">Mentora Doctoral Subsidy</p>
                  <p className="text-[11px] text-[#43474d]">Show only sessions eligible for $15-$20 grant reduction</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={onlySubsidized}
                onChange={onToggleSubsidized}
                className="w-5 h-5 accent-[#a73a00] rounded"
              />
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-[#f8f9ff] border-t border-[#e2e8f0] flex gap-2">
          <button
            type="button"
            onClick={() => {
              onSelectDomain('All Disciplines');
              onSelectMaxPrice(130);
              onClose();
            }}
            className="flex-1 py-2.5 rounded-xl border border-[#c3c6ce] text-[#001428] text-[13px] font-bold hover:bg-[#e5eeff]"
          >
            Reset Filters
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl bg-[#001428] text-white text-[13px] font-bold shadow-md hover:bg-[#0f2942]"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
};

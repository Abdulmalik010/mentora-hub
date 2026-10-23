import React, { useState } from 'react';

interface OnboardingScreenProps {
  onComplete: (academicLevel: string, interests: string[]) => void;
  onSkip: () => void;
  initialAcademicLevel?: string;
  initialInterests?: string[];
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({
  onComplete,
  onSkip,
  initialAcademicLevel = 'PhD',
  initialInterests = ['Quantum Computing', 'Cognitive Neuroscience', 'Artificial Intelligence & ML']
}) => {
  const [selectedLevel, setSelectedLevel] = useState<string>(initialAcademicLevel);
  const [selectedInterests, setSelectedInterests] = useState<string[]>(initialInterests);

  const academicLevels = [
    {
      id: 'Undergraduate',
      title: 'Undergraduate',
      desc: 'Bachelor degree, coursework & foundational research',
      icon: 'school'
    },
    {
      id: "Master's",
      title: "Master's",
      desc: 'Advanced specialization, thesis preparation & industry links',
      icon: 'history_edu'
    },
    {
      id: 'PhD',
      title: 'PhD',
      desc: 'Doctoral research, peer publications & academic faculty mentorship',
      icon: 'biotech'
    },
    {
      id: 'Professional',
      title: 'Professional',
      desc: 'Career advancement, executive skills & applied industry expertise',
      icon: 'badge'
    },
    {
      id: 'Curious learner',
      title: 'Curious learner',
      desc: 'Self-directed exploration, passion projects & lifelong learning',
      icon: 'explore'
    }
  ];

  const allInterests = [
    'Quantum Computing',
    'Cognitive Neuroscience',
    'Artificial Intelligence & ML',
    'Bioengineering & Genomics',
    'Applied Mathematics',
    'Climate Science & Energy',
    'Behavioral Economics',
    'Astrophysics',
    'Philosophy of Mind',
    'Robotics & Automation',
    'Human-Computer Interaction',
    'Science Policy & Law'
  ];

  const toggleInterest = (interest: string) => {
    if (selectedInterests.includes(interest)) {
      setSelectedInterests(selectedInterests.filter((i) => i !== interest));
    } else {
      setSelectedInterests([...selectedInterests, interest]);
    }
  };

  const handleContinue = () => {
    onComplete(selectedLevel, selectedInterests);
  };

  return (
    <main className="flex flex-col relative w-full px-4 pt-20 pb-32 bg-[#f8f9ff] flex-1 max-w-lg mx-auto">
      <div className="flex flex-col w-full pb-6 space-y-6">
        {/* Progress & Context Area */}
        <div className="flex flex-col space-y-2">
          <div className="flex items-center justify-between">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#e5eeff] text-[#43474d] text-[11px] font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#fd651e] animate-pulse"></span>
              <span>Step 1 of 3</span>
            </div>
            <span className="text-[12px] text-[#fd651e] font-semibold">33% Completed</span>
          </div>
          {/* Micro progress bar */}
          <div className="w-full h-1.5 bg-[#dce9ff] rounded-full overflow-hidden">
            <div className="h-full bg-[#fd651e] rounded-full w-1/3 transition-all duration-500"></div>
          </div>
          <div className="pt-2">
            <h1 className="text-[26px] font-bold text-[#001428] tracking-tight leading-tight">
              Tailor your learning journey
            </h1>
            <p className="text-[15px] text-[#43474d] mt-1 leading-relaxed">
              Tell us about your background so Mentora AI can match you with the right mentors and research tracks.
            </p>
          </div>
        </div>

        {/* Section 1: Academic Level (Single Select Cards) */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[14px] font-bold text-[#001428] tracking-tight">Current Academic Level</span>
            <span className="text-[11px] text-[#43474d] font-medium">Single choice</span>
          </div>
          <div className="space-y-2.5" role="radiogroup" aria-label="Select your academic level">
            {academicLevels.map((lvl) => {
              const isSelected = selectedLevel === lvl.id;
              return (
                <div
                  key={lvl.id}
                  onClick={() => setSelectedLevel(lvl.id)}
                  role="radio"
                  aria-checked={isSelected}
                  className={`academic-card group cursor-pointer relative flex items-start gap-3.5 p-3.5 rounded-xl transition-all active:scale-[0.99] ${
                    isSelected
                      ? 'bg-[#eff4ff] shadow-md border border-[#b0c9e8]'
                      : 'bg-[#ffffff] shadow-sm hover:shadow-md border border-[#e2e8f0]/60'
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                      isSelected ? 'bg-[#0f2942] text-white' : 'bg-[#e5eeff] text-[#0f2942] group-hover:bg-[#d1e4ff]'
                    }`}
                  >
                    <span
                      className="material-symbols-outlined text-[20px]"
                      style={{ fontVariationSettings: isSelected ? "'FILL' 1" : "'FILL' 0" }}
                    >
                      {lvl.icon}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0 pr-6">
                    <div className="flex items-center gap-2">
                      <span className={`text-[15px] text-[#001428] leading-tight ${isSelected ? 'font-bold' : 'font-medium'}`}>
                        {lvl.title}
                      </span>
                      {isSelected && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#ffdbce] text-[#7f2b00] text-[10px] tracking-wider uppercase font-bold">
                          <span className="w-1 h-1 rounded-full bg-[#fd651e]"></span>
                          Selected
                        </span>
                      )}
                    </div>
                    <div className="text-[13px] text-[#43474d] mt-0.5">{lvl.desc}</div>
                  </div>
                  <div
                    className={`absolute top-4 right-3.5 w-5 h-5 rounded-full flex items-center justify-center ${
                      isSelected ? 'bg-[#0f2942] text-white shadow-xs' : 'bg-[#dce9ff]'
                    }`}
                  >
                    {isSelected ? (
                      <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-transparent"></div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Discovery Callout Banner with imagery */}
        <div className="relative overflow-hidden rounded-2xl bg-[#0f2942] p-4 text-white shadow-md">
          <div className="absolute -right-6 -bottom-6 w-28 h-28 rounded-full bg-[#fd651e]/20 blur-xl pointer-events-none"></div>
          <div className="flex items-center gap-3 relative z-10">
            <div className="relative w-12 h-12 rounded-xl overflow-hidden shrink-0 bg-[#e5eeff]">
              <img
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDbxIWIPhVU_GKSppbTpAb_84wtYUTbpyXoAU8KPvmll0I4D6dOgN1xuwLaH2R-0ns_hQWStKySYXkHMNWb66F5A6adY2CMrUg6O2KjcoRzppZlNTA9RQ2lZvwmzbAwfoSxPax1uGOsT3cObnieRKUG7NIi8Pz2FtH6Dd2rU98JL_8lhW8cdOBS9VL1tgMnLtdc63vPiL9l5Nr8N98p_NVJIhTEP1o6QnN2KaDnXMNG2qwuDCkdT-aw"
                alt="Faculty match engine artwork"
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#ffdbce] text-[16px]">auto_awesome</span>
                <span className="text-[11px] text-[#ffdbce] uppercase tracking-wider font-bold">
                  Faculty Match Engine
                </span>
              </div>
              <p className="text-[13px] text-[#7991af] mt-0.5 leading-snug">
                Doctoral cohorts unlock curated lab affiliations & thesis peer reviews.
              </p>
            </div>
          </div>
        </div>

        {/* Section 2: Areas of Interest (Multi-Select Pill Chips) */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-bold text-[#001428] tracking-tight">Areas of Interest</span>
              <span
                className={`inline-flex items-center justify-center px-2 py-0.5 rounded-full text-[11px] font-bold ${
                  selectedInterests.length >= 3
                    ? 'bg-[#fd651e] text-white'
                    : 'bg-[#d3e4fe] text-[#43474d]'
                }`}
              >
                {selectedInterests.length} selected
              </span>
            </div>
            <span className="text-[11px] text-[#43474d]">Pick 3 or more</span>
          </div>

          {/* Chips Grid */}
          <div className="flex flex-wrap gap-2">
            {allInterests.map((interest) => {
              const isSelected = selectedInterests.includes(interest);
              return (
                <button
                  key={interest}
                  type="button"
                  onClick={() => toggleInterest(interest)}
                  className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-[13px] font-medium transition-all active:scale-95 shadow-xs ${
                    isSelected
                      ? 'bg-[#0f2942] text-white shadow-sm font-semibold'
                      : 'bg-[#e5eeff] text-[#0b1c30] hover:bg-[#d3e4fe]'
                  }`}
                >
                  {isSelected && (
                    <span className="material-symbols-outlined text-[15px]">check</span>
                  )}
                  <span>{interest}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Peer Matching Preview Graphic */}
        <div className="rounded-2xl bg-[#ffffff] p-4 shadow-sm border border-[#e2e8f0]/60 flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#fd651e] text-[18px]">hub</span>
              <span className="text-[13px] text-[#001428] font-bold">Active Scholars in your cluster</span>
            </div>
            <span className="text-[11px] text-[#43474d] font-semibold">1,480+ mentors</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2.5 overflow-hidden">
              <img
                className="w-8 h-8 rounded-full ring-2 ring-white object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuB9slI45sy6IBwPKACJfVAa5OyNtGgOtVY9FX9SaiUAgrV1g07itbeyzGs2tLfzgL_VTenBmlw6FmjP5pK6HCVX0hhkdIYzNnevYU6OodwZkJnmuWLVl97_netdB_xJuFFtsF6LDgDiUmJduZq3xWvFnrfkB_Zs9Y5S4ZqPlcmEbwbIF4ILBKXMvbIfFVmDISYQYHSkzzUs9I7xYMOFIzvWlyfMTJgNPUn4RK1P5L473c5lNvaiOmtI"
                alt="Scholar"
              />
              <img
                className="w-8 h-8 rounded-full ring-2 ring-white object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAYXQaOdGLSwD6CvUNKCjlVP6EVOzEVVMfX0GftIAGJPfNjaBe_-O2aoCbrEu3AzKuVCAVIKcmIH5sM8MjjsmekScLv5BVWCEJbWd3Xtt112lhW8CxVzNDKBOpv0tnne7YBkidxmsx24Uf9udv7X1T3D7-w3879hrb_lHwJ7mHqd9XdkHks4QLoTw02A_fSQFdnTE9fBRPB0kiPnX15ybSPyueisoZ3_GIEcqRfk1LX57-0eahJo-Mq"
                alt="Scholar"
              />
              <img
                className="w-8 h-8 rounded-full ring-2 ring-white object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDwqRmgINNOuXdcf9lryfSxSbTWlwFAo1e-tsm4b_Z-ZttiNt94FbMATY_jBszWqMziruJ44LsX100pguWPxwnLmnEx76fK3R22Kx5mqIDBjrvrtUlhsTXSi4oIlN-6yiWWCLyGH6_05V4jlPQ1JyESefcg_NzfgHOZTv8YYsqGdYKIxCKhABFr3iXsodJomgUYOZ2lBlSZC_AkyTuEiSpCf55HogdhOEKUbd7bdj9-Zk2gWqhBR87K"
                alt="Scholar"
              />
              <div className="w-8 h-8 rounded-full ring-2 ring-white bg-[#0f2942] text-white flex items-center justify-center text-[10px] font-bold">
                +48
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-[#43474d] truncate">
                Matching with Stanford, Oxford & Max Planck faculties
              </p>
            </div>
          </div>
        </div>

        {/* Section: Bottom In-Page Action Block */}
        <div className="flex flex-col space-y-3 pt-1">
          <div className="flex items-start gap-2 px-1">
            <span className="material-symbols-outlined text-[16px] text-[#43474d] shrink-0 mt-0.5">info</span>
            <p className="text-[13px] text-[#43474d]">
              You can update your academic level and preferences anytime in your Profile settings.
            </p>
          </div>
          <div className="flex flex-col gap-2 pt-1">
            <button
              type="button"
              onClick={handleContinue}
              className="w-full min-h-[50px] flex items-center justify-center gap-2 px-6 bg-[#0f2942] text-white rounded-xl text-[15px] font-bold shadow-md hover:bg-[#001428] transition-all active:scale-[0.99]"
            >
              <span>Continue to Academic Goals</span>
              <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
            </button>
            <button
              type="button"
              onClick={onSkip}
              className="w-full py-2.5 text-center text-[13px] font-semibold text-[#43474d] hover:text-[#001428] transition-colors"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>

      {/* Sticky Bottom Actions Bar */}
      <footer className="fixed bottom-0 inset-x-0 z-40 pb-safe bg-[#f8f9ff]/90 backdrop-blur-xl shadow-[0_-2px_12px_rgba(15,41,66,0.06)] border-t border-[#e2e8f0]/60">
        <div className="h-20 px-4 flex items-center justify-between gap-4 max-w-lg mx-auto">
          <button
            type="button"
            onClick={onSkip}
            className="min-h-[44px] px-3 text-[#43474d] hover:text-[#001428] text-[14px] font-bold transition-colors"
          >
            Skip
          </button>
          <button
            type="button"
            onClick={handleContinue}
            className="min-h-[48px] flex-1 max-w-xs flex items-center justify-center gap-1.5 px-6 bg-[#fd651e] text-white rounded-xl text-[14px] font-bold shadow-sm hover:opacity-95 active:scale-[0.99] transition-all"
          >
            <span>Continue</span>
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
        </div>
      </footer>
    </main>
  );
};

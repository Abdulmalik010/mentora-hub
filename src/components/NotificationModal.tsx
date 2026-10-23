import React from 'react';

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateToSession: () => void;
}

export const NotificationModal: React.FC<NotificationModalProps> = ({
  isOpen,
  onClose,
  onNavigateToSession
}) => {
  if (!isOpen) return null;

  const notifications = [
    {
      id: 'n1',
      title: 'Upcoming Session in 24 Hours',
      desc: 'Thesis Review with Dr. Marcus Vance is scheduled for tomorrow at 3:00 PM EDT. Please complete the pre-session checklist.',
      time: '10 mins ago',
      type: 'session',
      actionLabel: 'View Session',
      isUnread: true
    },
    {
      id: 'n2',
      title: 'Doctoral Subsidy Grant Approved',
      desc: 'Mentora Academic Foundation has credited a $15.00 institutional co-pay to all verified doctoral consultations.',
      time: '2 hours ago',
      type: 'grant',
      isUnread: true
    },
    {
      id: 'n3',
      title: 'New arXiv Preprint in Surface Codes',
      desc: 'Dr. Aris Thorne cited a new publication on rotated surface codes threshold reduction (arXiv:2403.1189).',
      time: 'Yesterday',
      type: 'paper',
      isUnread: false
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#001428]/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#ffffff] rounded-2xl w-full max-w-md shadow-2xl overflow-hidden border border-[#e2e8f0] flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 bg-[#f8f9ff] border-b border-[#e2e8f0] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#a73a00] text-[22px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              notifications
            </span>
            <h3 className="text-[17px] font-bold text-[#001428]">Notifications</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[#74777e] hover:bg-[#e5eeff] transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* List */}
        <div className="p-4 overflow-y-auto space-y-3 flex-1">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`p-3.5 rounded-xl border transition-all ${
                n.isUnread ? 'bg-[#eff4ff] border-[#d1e4ff]' : 'bg-[#ffffff] border-[#e2e8f0]'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  {n.isUnread && <span className="w-2 h-2 rounded-full bg-[#fd651e] shrink-0"></span>}
                  <h4 className="text-[14px] font-bold text-[#001428]">{n.title}</h4>
                </div>
                <span className="text-[11px] text-[#74777e] shrink-0">{n.time}</span>
              </div>
              <p className="text-[13px] text-[#43474d] mt-1 leading-relaxed">{n.desc}</p>
              {n.actionLabel && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateToSession();
                  }}
                  className="mt-2.5 inline-flex items-center gap-1 text-[12px] font-bold text-[#a73a00] hover:underline"
                >
                  <span>{n.actionLabel}</span>
                  <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#f8f9ff] border-t border-[#e2e8f0] text-center">
          <button
            type="button"
            onClick={onClose}
            className="text-[13px] font-semibold text-[#0f2942] hover:underline py-1"
          >
            Mark all as read & close
          </button>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Expert } from '../data/expertsData';

interface PaymentScreenProps {
  expert: Expert;
  bookingDetails: {
    format: 'video' | 'async';
    formatTitle: string;
    date: string;
    time: string;
    agenda: string;
    price: number;
    platformFee?: number;
    subsidyDiscount?: number;
    totalDue?: number;
  };
  onBack: () => void;
  onEditBooking: () => void;
  onPaymentSuccess: (paymentInfo: {
    method: string;
    cardLast4: string;
    totalPaid: number;
    bookingId: string;
  }) => void;
}

export const PaymentScreen: React.FC<PaymentScreenProps> = ({
  expert,
  bookingDetails,
  onBack,
  onEditBooking,
  onPaymentSuccess
}) => {
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'bank' | 'grant'>('card');
  const [selectedBankId, setSelectedBankId] = useState<string>('bank-1');
  const [showNewCardForm, setShowNewCardForm] = useState(false);
  const [cardName, setCardName] = useState('Prof. Elena Vance');
  const [cardNumber, setCardNumber] = useState('4000 1234 5678 4242');
  const [cardExpiry, setCardExpiry] = useState('08/26');
  const [cardCvc, setCardCvc] = useState('842');
  const [grantVoucherCode, setGrantVoucherCode] = useState('');
  const [isVoucherApplied, setIsVoucherApplied] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Verified institutions for ACH bank transfer
  const verifiedBanks = [
    {
      id: 'bank-1',
      name: 'Harvard FCU Checking',
      accountNumber: '•••• 8192',
      verified: true
    },
    {
      id: 'bank-2',
      name: 'Cambridge University Endowment Account',
      accountNumber: '•••• 4103',
      verified: true
    }
  ];

  // Calculation
  const advisoryCost = bookingDetails.price;
  const platformFee = bookingDetails.platformFee ?? 5.0;
  const doctoralSubsidy = bookingDetails.subsidyDiscount ?? (expert.subsidyEligible ? 15.0 : 0.0);
  const voucherDiscount = isVoucherApplied ? 10.0 : 0.0;
  const totalDue = Math.max(0, advisoryCost + platformFee - doctoralSubsidy - voucherDiscount);

  const handleApplyVoucher = () => {
    if (grantVoucherCode.trim()) {
      setIsVoucherApplied(true);
    }
  };

  const handlePay = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      const randomRef = `#MEN-${Math.floor(1000 + Math.random() * 9000)}-QT`;
      const selectedBank = verifiedBanks.find((b) => b.id === selectedBankId);

      onPaymentSuccess({
        method:
          paymentMethod === 'card'
            ? 'Credit Card'
            : paymentMethod === 'bank'
            ? `Institutional Bank Transfer (${selectedBank?.name || 'ACH'})`
            : 'Institutional Grant Voucher',
        cardLast4: paymentMethod === 'card' ? '4242' : selectedBank?.accountNumber.replace(/[^0-9]/g, '') || '8192',
        totalPaid: totalDue,
        bookingId: randomRef
      });
    }, 1200);
  };

  return (
    <main className="flex-1 flex flex-col relative w-full pt-24 bg-[#f8f9ff] pb-safe max-w-lg mx-auto">
      <div className="flex flex-col w-full px-4 pb-28">
        {/* Progress Header Tracker */}
        <div className="w-full pt-2 pb-4">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#fd651e]"></span>
              <span className="text-[11px] text-[#a73a00] font-bold tracking-wider uppercase">
                Step 2 of 3
              </span>
            </div>
            <span className="text-[11px] text-[#43474d] font-semibold">Payment & Review (66%)</span>
          </div>
          <div className="w-full h-1.5 bg-[#e5eeff] rounded-full overflow-hidden flex">
            <div
              className="h-full bg-[#fd651e] rounded-full transition-all duration-500 ease-out"
              style={{ width: '66%' }}
            ></div>
          </div>
        </div>

        {/* Booking Summary Card */}
        <div className="w-full bg-[#ffffff] rounded-xl p-4 shadow-sm border border-[#e2e8f0]/80 mb-4">
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="relative shrink-0">
                <img
                  className="w-[52px] h-[52px] rounded-full object-cover shadow-xs ring-2 ring-[#dce9ff]"
                  src={expert.avatarUrl}
                  alt={expert.name}
                />
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#ffffff] flex items-center justify-center shadow-xs">
                  <span className="material-symbols-outlined text-[14px] text-[#49607c]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    verified
                  </span>
                </div>
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-[16px] font-bold text-[#0b1c30] truncate">{expert.name}</h2>
                <p className="text-[12px] text-[#43474d] truncate">{expert.institution}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onEditBooking}
              className="shrink-0 px-2.5 py-1 rounded-full bg-[#e5eeff] hover:bg-[#dce9ff] transition-colors text-[#001428] text-[11px] font-bold flex items-center gap-1"
            >
              <span>Edit</span>
              <span className="material-symbols-outlined text-[13px]">edit</span>
            </button>
          </div>

          {/* Details Grid */}
          <div className="bg-[#eff4ff] rounded-lg p-2.5 flex flex-col gap-2 border border-[#d1e4ff]/50">
            <div className="flex items-center gap-2.5 text-[#0b1c30]">
              <div className="w-7 h-7 rounded-md bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
                <span className="material-symbols-outlined text-[18px]">
                  {bookingDetails.format === 'video' ? 'videocam' : 'assignment'}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] text-[#43474d]">Session Format</p>
                <p className="text-[13px] font-bold text-[#0b1c30] truncate">
                  {bookingDetails.formatTitle}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 text-[#0b1c30]">
              <div className="w-7 h-7 rounded-md bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
                <span className="material-symbols-outlined text-[18px]">calendar_today</span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] text-[#43474d]">Scheduled Time</p>
                <p className="text-[13px] font-bold text-[#0b1c30] truncate">
                  {bookingDetails.date}, 2024 • {bookingDetails.time} EDT
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 text-[#0b1c30]">
              <div className="w-7 h-7 rounded-md bg-[#ffdbce] flex items-center justify-center shrink-0 text-[#a73a00]">
                <span className="material-symbols-outlined text-[18px]">link</span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] text-[#a73a00] font-bold">Virtual Chamber</p>
                <p className="text-[12px] text-[#0b1c30] truncate">
                  Encrypted Mentora Room (Issued on payment)
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Price Breakdown & Subsidies */}
        <div className="w-full bg-[#ffffff] rounded-xl p-4 shadow-sm border border-[#e2e8f0]/80 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[12px] uppercase tracking-wider text-[#43474d] font-bold">
              Session Cost Breakdown
            </h3>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#e5eeff] text-[#49607c] font-bold">
              Academic Tier
            </span>
          </div>

          <div className="space-y-2.5 pb-2 border-b border-[#e2e8f0]/80">
            <div className="flex items-center justify-between text-[14px]">
              <div className="flex items-center gap-1.5 text-[#0b1c30]">
                <span>45-min Academic Advisory</span>
                <span className="material-symbols-outlined text-[15px] text-[#c3c6ce]" title="Faculty direct booking rate">
                  help_outline
                </span>
              </div>
              <span className="font-bold text-[#0b1c30]">${advisoryCost.toFixed(2)}</span>
            </div>

            <div className="flex items-center justify-between text-[14px]">
              <div className="flex items-center gap-1.5 text-[#0b1c30]">
                <span>Mentora Platform & LaTeX Tooling</span>
                <span className="material-symbols-outlined text-[15px] text-[#c3c6ce]" title="Includes collaborative shared math canvas">
                  info
                </span>
              </div>
              <span className="font-bold text-[#0b1c30]">${platformFee.toFixed(2)}</span>
            </div>

            {expert.subsidyEligible && (
              <div className="flex items-center justify-between text-[14px]">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[#0b1c30]">Doctoral Subsidy</span>
                  <div className="inline-flex items-center gap-1 bg-[#dce9ff] px-2 py-0.5 rounded-full">
                    <span className="material-symbols-outlined text-[13px] text-[#a73a00] font-bold">
                      verified_user
                    </span>
                    <span className="text-[11px] text-[#a73a00] font-bold">Mentora Grant Applied</span>
                  </div>
                </div>
                <span className="font-bold text-[#a73a00]">-${doctoralSubsidy.toFixed(2)}</span>
              </div>
            )}

            {isVoucherApplied && (
              <div className="flex items-center justify-between text-[14px]">
                <span className="text-[#0b1c30]">Grant Voucher Discount</span>
                <span className="font-bold text-emerald-600">-${voucherDiscount.toFixed(2)}</span>
              </div>
            )}
          </div>

          <div className="pt-2 bg-[#eff4ff] rounded-lg p-2.5 mt-2 flex items-baseline justify-between border border-[#d1e4ff]/50">
            <div>
              <span className="text-[11px] uppercase tracking-wide text-[#43474d] block font-bold">
                Total Due
              </span>
              <span className="text-[11px] text-[#43474d]">Includes institutional tax exemption</span>
            </div>
            <div className="text-right">
              <span className="text-[28px] font-extrabold text-[#001428] tracking-tight">
                ${totalDue.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Payment Methods Selection */}
        <div className="w-full mb-4">
          <h3 className="text-[12px] uppercase tracking-wider text-[#43474d] font-bold mb-2 px-1">
            Payment Method
          </h3>

          <div className="space-y-2">
            {/* Option 1: Credit / Debit Card */}
            <div
              className={`bg-[#ffffff] rounded-xl overflow-hidden shadow-sm border transition-all ${
                paymentMethod === 'card' ? 'border-[#a73a00] ring-1 ring-[#a73a00]' : 'border-[#e2e8f0]'
              }`}
            >
              <div
                onClick={() => setPaymentMethod('card')}
                className="w-full flex items-center justify-between p-3.5 cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                      paymentMethod === 'card' ? 'bg-[#001428]' : 'bg-[#dce9ff]'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${paymentMethod === 'card' ? 'bg-white' : 'bg-transparent'}`}></span>
                  </div>
                  <div className="w-9 h-9 rounded-lg bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
                    <span className="material-symbols-outlined text-[20px]">credit_card</span>
                  </div>
                  <div>
                    <p className="text-[13px] font-bold text-[#0b1c30]">Credit / Debit Card</p>
                    <p className="text-[11px] text-[#43474d]">Visa, Mastercard, Amex, UnionPay</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-75">
                  <div className="w-7 h-4 rounded bg-[#dce9ff] flex items-center justify-center text-[9px] font-extrabold text-[#001428]">
                    VISA
                  </div>
                  <div className="w-7 h-4 rounded bg-[#dce9ff] flex items-center justify-center text-[9px] font-extrabold text-[#a73a00]">
                    MC
                  </div>
                </div>
              </div>

              {/* Card Options / Details Section */}
              {paymentMethod === 'card' && (
                <div className="px-3.5 pb-3.5 flex flex-col gap-2 pt-0 border-t border-[#e2e8f0]/60">
                  {/* Pre-saved Card */}
                  <div className="bg-[#eff4ff] rounded-xl p-2.5 flex items-center justify-between shadow-xs border border-[#d1e4ff]/60">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-[#0f2942] text-white flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[18px]">account_balance_wallet</span>
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-[13px] font-bold text-[#0b1c30] truncate">•••• 4242</p>
                          <span className="px-1.5 py-0.2 rounded bg-[#d3e4fe] text-[#001428] text-[10px] font-bold uppercase tracking-wider">
                            Default
                          </span>
                        </div>
                        <p className="text-[11px] text-[#43474d]">Expires 08/26 • Harvard FCU</p>
                      </div>
                    </div>
                    <div className="w-5 h-5 rounded-full bg-[#fd651e] flex items-center justify-center text-white shrink-0 shadow-xs">
                      <span className="material-symbols-outlined text-[13px] font-bold">check</span>
                    </div>
                  </div>

                  {/* Toggle new card form */}
                  <button
                    type="button"
                    onClick={() => setShowNewCardForm(!showNewCardForm)}
                    className="text-[11px] text-[#a73a00] font-bold flex items-center gap-1 hover:underline py-1"
                  >
                    <span className="material-symbols-outlined text-[15px]">
                      {showNewCardForm ? 'arrow_drop_up' : 'add_circle'}
                    </span>
                    <span>{showNewCardForm ? 'Use saved card instead' : 'Enter new card details'}</span>
                  </button>

                  {/* Form */}
                  {showNewCardForm && (
                    <div className="space-y-2 pt-1 border-t border-[#d1e4ff]/50">
                      <div>
                        <label className="text-[11px] text-[#43474d] font-bold block mb-1">Cardholder Name</label>
                        <input
                          type="text"
                          value={cardName}
                          onChange={(e) => setCardName(e.target.value)}
                          className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-[#0b1c30] border border-[#d1e4ff] focus:outline-none focus:border-[#a73a00]"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] text-[#43474d] font-bold block mb-1">Card Number</label>
                        <input
                          type="text"
                          value={cardNumber}
                          onChange={(e) => setCardNumber(e.target.value)}
                          className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] font-mono text-[#0b1c30] border border-[#d1e4ff] focus:outline-none focus:border-[#a73a00]"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[11px] text-[#43474d] font-bold block mb-1">Expiry Date</label>
                          <input
                            type="text"
                            value={cardExpiry}
                            onChange={(e) => setCardExpiry(e.target.value)}
                            className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-center text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-[#43474d] font-bold block mb-1">CVC</label>
                          <input
                            type="password"
                            value={cardCvc}
                            onChange={(e) => setCardCvc(e.target.value)}
                            className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-center text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Option 2: Institutional Bank Transfer (ACH / SEPA) */}
            <div
              className={`bg-[#ffffff] rounded-xl overflow-hidden shadow-sm border transition-all ${
                paymentMethod === 'bank' ? 'border-[#a73a00] ring-1 ring-[#a73a00]' : 'border-[#e2e8f0]'
              }`}
            >
              <div
                onClick={() => setPaymentMethod('bank')}
                className="w-full flex items-center justify-between p-3.5 cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                      paymentMethod === 'bank' ? 'bg-[#001428]' : 'bg-[#dce9ff]'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${paymentMethod === 'bank' ? 'bg-white' : 'bg-transparent'}`}></span>
                  </div>
                  <div className="w-9 h-9 rounded-lg bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
                    <span className="material-symbols-outlined text-[20px]">account_balance</span>
                  </div>
                  <div className="pr-2">
                    <div className="flex items-center gap-1.5">
                      <p className="text-[13px] font-bold text-[#0b1c30]">Institutional Bank Transfer</p>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#e5eeff] text-[#49607c] font-bold">
                        ACH / SEPA
                      </span>
                    </div>
                    <p className="text-[11px] text-[#43474d]">Direct institutional verification via Plaid or wire</p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-[#c3c6ce] text-[20px]">
                  {paymentMethod === 'bank' ? 'expand_less' : 'chevron_right'}
                </span>
              </div>

              {paymentMethod === 'bank' && (
                <div className="px-3.5 pb-3.5 pt-0 border-t border-[#e2e8f0]/60 space-y-2.5">
                  <span className="text-[11px] font-bold text-[#43474d] uppercase tracking-wider block pt-2">
                    Select Linked Institutional Account:
                  </span>

                  {verifiedBanks.map((bank) => {
                    const isSelected = selectedBankId === bank.id;
                    return (
                      <div
                        key={bank.id}
                        onClick={() => setSelectedBankId(bank.id)}
                        className={`p-2.5 rounded-xl flex items-center justify-between cursor-pointer border transition-all ${
                          isSelected
                            ? 'bg-[#eff4ff] border-[#a73a00]'
                            : 'bg-white border-[#e2e8f0] hover:bg-[#f8f9ff]'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <span className="material-symbols-outlined text-[20px] text-[#001428]">
                            verified
                          </span>
                          <div>
                            <p className="text-[12px] font-bold text-[#0b1c30]">{bank.name}</p>
                            <p className="text-[11px] text-[#74777e]">{bank.accountNumber} • Verified via Cambridge Single Sign-On</p>
                          </div>
                        </div>
                        <div
                          className={`w-5 h-5 rounded-full flex items-center justify-center text-white shrink-0 ${
                            isSelected ? 'bg-[#fd651e]' : 'bg-[#e5eeff] text-transparent'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[13px] font-bold">check</span>
                        </div>
                      </div>
                    );
                  })}

                  <div className="p-2.5 bg-[#f8f9ff] rounded-xl flex items-center justify-between border border-[#e2e8f0]">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-[18px] text-[#74777e]">add_business</span>
                      <span className="text-[11px] text-[#43474d]">Link another university account with Plaid</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => alert('Plaid Academic Portal: Connect your university .edu credentials')}
                      className="px-2.5 py-1 rounded-lg bg-[#001428] text-white text-[11px] font-bold hover:bg-[#0f2942]"
                    >
                      Connect
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Option 3: Institutional Grant Voucher */}
            <div
              className={`bg-[#ffffff] rounded-xl overflow-hidden shadow-sm border transition-all ${
                paymentMethod === 'grant' ? 'border-[#a73a00] ring-1 ring-[#a73a00]' : 'border-[#e2e8f0]'
              }`}
            >
              <div
                onClick={() => setPaymentMethod('grant')}
                className="w-full flex items-center justify-between p-3.5 cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                      paymentMethod === 'grant' ? 'bg-[#001428]' : 'bg-[#dce9ff]'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${paymentMethod === 'grant' ? 'bg-white' : 'bg-transparent'}`}></span>
                  </div>
                  <div className="w-9 h-9 rounded-lg bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
                    <span className="material-symbols-outlined text-[20px]">school</span>
                  </div>
                  <div className="pr-2">
                    <p className="text-[13px] font-bold text-[#0b1c30]">Institutional Grant Voucher</p>
                    <p className="text-[11px] text-[#43474d]">Charge to MIT, Harvard, or Partner Lab budget</p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-[#c3c6ce] text-[20px]">
                  {paymentMethod === 'grant' ? 'expand_less' : 'chevron_right'}
                </span>
              </div>

              {paymentMethod === 'grant' && (
                <div className="px-3.5 pb-3.5 pt-0 flex flex-col gap-2 border-t border-[#e2e8f0]/60">
                  <label className="text-[11px] text-[#43474d] font-bold pt-2">
                    Grant Account Number or Lab Voucher Code
                  </label>
                  <div className="flex gap-2">
                    <div className="h-10 flex-1 bg-[#eff4ff] rounded-xl px-3 flex items-center border border-[#d1e4ff]">
                      <input
                        type="text"
                        value={grantVoucherCode}
                        onChange={(e) => setGrantVoucherCode(e.target.value)}
                        placeholder="e.g. HARV-PHYS-2024-Q3"
                        className="bg-transparent w-full text-[#0b1c30] text-[12px] uppercase tracking-wider outline-none"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleApplyVoucher}
                      className="px-4 h-10 rounded-xl bg-[#001428] text-white text-[12px] font-bold active:scale-95 transition-all"
                    >
                      {isVoucherApplied ? 'Applied' : 'Apply'}
                    </button>
                  </div>
                  <p className="text-[11px] text-[#49607c] flex items-center gap-1">
                    <span className="material-symbols-outlined text-[13px]">info</span>
                    Requires authorized signing PI designation.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Security Guarantee Trust Card */}
        <div className="w-full bg-[#eff4ff] rounded-xl p-3 mb-4 flex items-center gap-3 border border-[#d1e4ff]/60">
          <div className="w-9 h-9 rounded-full bg-[#d3e4fe] flex items-center justify-center shrink-0 text-[#49607c]">
            <span className="material-symbols-outlined text-[20px]">gavel</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-bold text-[#0b1c30]">256-Bit SSL Encrypted Escrow</p>
            <p className="text-[11px] text-[#43474d]">100% Refundable up to 24 hours prior to session commencement.</p>
          </div>
        </div>
      </div>

      {/* Sticky Bottom Checkout Action Dock */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#ffffff]/95 backdrop-blur-xl shadow-[0_-4px_16px_rgba(15,41,66,0.08)] px-4 py-3 pb-safe border-t border-[#e2e8f0]">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <div className="flex flex-col shrink-0 min-w-[76px]">
            <span className="text-[10px] uppercase font-bold text-[#43474d] tracking-wider">Amount Due</span>
            <span className="text-[22px] font-extrabold text-[#0b1c30] leading-none">
              ${totalDue.toFixed(2)}
            </span>
          </div>
          <button
            type="button"
            disabled={isProcessing}
            onClick={handlePay}
            className="flex-1 h-12 py-3 px-4 rounded-xl bg-[#fd651e] hover:bg-[#a73a00] text-white text-[14px] font-bold flex items-center justify-center gap-2 shadow-md active:scale-[0.98] transition-all disabled:opacity-70"
          >
            {isProcessing ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                <span>Securing Consultation...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[19px]">lock</span>
                <span>
                  {paymentMethod === 'bank'
                    ? `Authorize $${totalDue.toFixed(2)} via Bank Transfer`
                    : `Pay $${totalDue.toFixed(2)} & Confirm Booking`}
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </main>
  );
};

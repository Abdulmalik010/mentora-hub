import React, { useState, useEffect } from 'react';
import { Expert, formatNaira } from '../data/expertsData';

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

interface NigerianBankUSSD {
  id: string;
  name: string;
  code: string;
  shortCode: string;
  logoColor: string;
}

export const PaymentScreen: React.FC<PaymentScreenProps> = ({
  expert,
  bookingDetails,
  onBack,
  onEditBooking,
  onPaymentSuccess
}) => {
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'bank' | 'ussd'>('card');
  const [showNewCardForm, setShowNewCardForm] = useState(false);
  const [cardName, setCardName] = useState('Elena Rostova');
  const [cardNumber, setCardNumber] = useState('5399 4112 8904 4242');
  const [cardExpiry, setCardExpiry] = useState('09/27');
  const [cardCvc, setCardCvc] = useState('741');
  const [cardPin, setCardPin] = useState('••••');
  const [grantVoucherCode, setGrantVoucherCode] = useState('');
  const [isVoucherApplied, setIsVoucherApplied] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [copiedAccount, setCopiedAccount] = useState(false);
  const [copiedUssd, setCopiedUssd] = useState(false);
  const [transferMinutesLeft, setTransferMinutesLeft] = useState(29);
  const [transferSecondsLeft, setTransferSecondsLeft] = useState(59);

  // USSD Bank options
  const ussdBanks: NigerianBankUSSD[] = [
    { id: 'gtb', name: 'Guaranty Trust Bank (GTB)', code: '*737#', shortCode: '*737*2*', logoColor: 'bg-[#dd4f05]' },
    { id: 'zenith', name: 'Zenith Bank', code: '*966#', shortCode: '*966*60*', logoColor: 'bg-[#d8232a]' },
    { id: 'access', name: 'Access Bank', code: '*901#', shortCode: '*901*00*', logoColor: 'bg-[#003882]' },
    { id: 'uba', name: 'United Bank for Africa (UBA)', code: '*919#', shortCode: '*919*4*', logoColor: 'bg-[#d81e05]' },
    { id: 'firstbank', name: 'First Bank of Nigeria', code: '*894#', shortCode: '*894*00*', logoColor: 'bg-[#00205b]' },
    { id: 'stanbic', name: 'Stanbic IBTC Bank', code: '*909#', shortCode: '*909*22*', logoColor: 'bg-[#0033a0]' }
  ];
  const [selectedUssdBank, setSelectedUssdBank] = useState<NigerianBankUSSD>(ussdBanks[0]);

  // Pricing Calculation in Nigerian Naira
  const advisoryCost = bookingDetails.price;
  const platformFee = bookingDetails.platformFee ?? 1000;
  const doctoralSubsidy = bookingDetails.subsidyDiscount ?? (expert.subsidyEligible ? 3000 : 0);
  const voucherDiscount = isVoucherApplied ? 2000 : 0;
  const totalDue = Math.max(0, advisoryCost + platformFee - doctoralSubsidy - voucherDiscount);

  // Transfer countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setTransferSecondsLeft((prevSec) => {
        if (prevSec > 0) return prevSec - 1;
        setTransferMinutesLeft((prevMin) => (prevMin > 0 ? prevMin - 1 : 29));
        return 59;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleApplyVoucher = () => {
    if (grantVoucherCode.trim()) {
      setIsVoucherApplied(true);
    }
  };

  const handleCopyAccount = () => {
    navigator.clipboard?.writeText('0129384721');
    setCopiedAccount(true);
    setTimeout(() => setCopiedAccount(false), 2500);
  };

  const dialString = `${selectedUssdBank.shortCode}${totalDue}*0012#`;

  const handleCopyUssd = () => {
    navigator.clipboard?.writeText(dialString);
    setCopiedUssd(true);
    setTimeout(() => setCopiedUssd(false), 2500);
  };

  const handlePay = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      const randomRef = `#MEN-${Math.floor(1000 + Math.random() * 9000)}-NG`;

      let methodDisplay = 'Debit/Credit Card (Mastercard)';
      let last4 = '4242';

      if (paymentMethod === 'bank') {
        methodDisplay = 'Bank Transfer (Wema Bank Escrow)';
        last4 = '4721';
      } else if (paymentMethod === 'ussd') {
        methodDisplay = `USSD Payment (${selectedUssdBank.name})`;
        last4 = selectedUssdBank.code.replace(/[^0-9]/g, '');
      }

      onPaymentSuccess({
        method: methodDisplay,
        cardLast4: last4,
        totalPaid: totalDue,
        bookingId: randomRef
      });
    }, 1200);
  };

  return (
    <main className="flex-1 flex flex-col relative w-full pt-6 pb-28 bg-[#f8f9ff] max-w-3xl mx-auto px-4">
      {/* Progress Header Tracker */}
      <div className="w-full pt-1 pb-4">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#fd651e] animate-pulse"></span>
            <span className="text-[11px] text-[#a73a00] font-bold tracking-wider uppercase">
              Step 2 of 3
            </span>
          </div>
          <span className="text-[12px] text-[#43474d] font-semibold">Simulated Payment Checkout (66%)</span>
        </div>
        <div className="w-full h-2 bg-[#e5eeff] rounded-full overflow-hidden flex">
          <div
            className="h-full bg-[#fd651e] rounded-full transition-all duration-500 ease-out"
            style={{ width: '66%' }}
          ></div>
        </div>
      </div>

      {/* Booking Summary Card */}
      <div className="w-full bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 mb-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="relative shrink-0">
              <img
                className="w-13 h-13 rounded-2xl object-cover shadow-xs ring-2 ring-[#dce9ff]"
                src={expert.avatarUrl}
                alt={expert.name}
              />
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#001428] flex items-center justify-center shadow-xs text-white">
                <span className="material-symbols-outlined text-[13px]">verified</span>
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-[16px] font-bold text-[#0b1c30] truncate">{expert.name}</h2>
              <p className="text-[12px] text-[#43474d] truncate">{expert.title} • {expert.institution}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onEditBooking}
            className="shrink-0 px-3 py-1 rounded-full bg-[#e5eeff] hover:bg-[#dce9ff] transition-colors text-[#001428] text-[11px] font-bold flex items-center gap-1"
          >
            <span>Edit</span>
            <span className="material-symbols-outlined text-[13px]">edit</span>
          </button>
        </div>

        {/* Details Grid */}
        <div className="bg-[#eff4ff] rounded-xl p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border border-[#d1e4ff]/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
              <span className="material-symbols-outlined text-[18px]">
                {bookingDetails.format === 'video' ? 'videocam' : 'assignment'}
              </span>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] text-[#43474d] uppercase font-bold">Session Format</p>
              <p className="text-[13px] font-bold text-[#0b1c30] truncate">{bookingDetails.formatTitle}</p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#e5eeff] flex items-center justify-center shrink-0 text-[#001428]">
              <span className="material-symbols-outlined text-[18px]">calendar_today</span>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] text-[#43474d] uppercase font-bold">Scheduled Time</p>
              <p className="text-[13px] font-bold text-[#0b1c30] truncate">
                {bookingDetails.date} • {bookingDetails.time}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Price Breakdown in Nigerian Naira */}
      <div className="w-full bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0]/80 mb-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[12px] uppercase tracking-wider text-[#43474d] font-bold">
            Tuition & Platform Fee Breakdown
          </h3>
          <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#ffdbce] text-[#370e00] font-bold">
            Academic Rate (NGN)
          </span>
        </div>

        <div className="space-y-2.5 pb-3 border-b border-[#e2e8f0]/80">
          <div className="flex items-center justify-between text-[14px]">
            <span className="text-[#0b1c30]">1:1 Faculty Advisory Session</span>
            <span className="font-bold text-[#0b1c30]">{formatNaira(advisoryCost)}</span>
          </div>

          <div className="flex items-center justify-between text-[14px]">
            <span className="text-[#0b1c30]">Mentora Platform & Interactive Chamber</span>
            <span className="font-bold text-[#0b1c30]">{formatNaira(platformFee)}</span>
          </div>

          {expert.subsidyEligible && (
            <div className="flex items-center justify-between text-[14px]">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[#0b1c30]">Doctoral Fellowship Subsidy</span>
                <span className="text-[10px] bg-[#dce9ff] text-[#001428] px-2 py-0.5 rounded-full font-bold">
                  Grant Applied
                </span>
              </div>
              <span className="font-bold text-[#a73a00]">-{formatNaira(doctoralSubsidy)}</span>
            </div>
          )}

          {isVoucherApplied && (
            <div className="flex items-center justify-between text-[14px]">
              <span className="text-[#0b1c30]">Institutional Grant Voucher</span>
              <span className="font-bold text-emerald-600">-{formatNaira(voucherDiscount)}</span>
            </div>
          )}
        </div>

        {/* Total Due Banner */}
        <div className="pt-3 flex items-baseline justify-between">
          <div>
            <span className="text-[11px] uppercase tracking-wide text-[#43474d] block font-bold">
              Total Amount Payable
            </span>
            <span className="text-[11px] text-[#74777e]">All taxes and banking fees included</span>
          </div>
          <div className="text-right">
            <span className="text-[26px] font-extrabold text-[#001428] tracking-tight">
              {formatNaira(totalDue)}
            </span>
          </div>
        </div>
      </div>

      {/* Simulated Payment Options: Card, Bank Transfer, USSD */}
      <div className="w-full mb-5">
        <div className="flex items-center justify-between mb-2 px-1">
          <h3 className="text-[12px] uppercase tracking-wider text-[#43474d] font-bold">
            Select Payment Method
          </h3>
          <span className="text-[11px] text-[#a73a00] font-semibold flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">shield</span>
            <span>Simulated Sandbox</span>
          </span>
        </div>

        {/* Tab Selector */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <button
            type="button"
            onClick={() => setPaymentMethod('card')}
            className={`py-3 px-2 rounded-xl text-[12px] font-bold flex flex-col items-center justify-center gap-1 transition-all ${
              paymentMethod === 'card'
                ? 'bg-[#001428] text-white shadow-sm ring-2 ring-[#001428]'
                : 'bg-white text-[#43474d] border border-[#e2e8f0] hover:bg-[#eff4ff]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">credit_card</span>
            <span>Card</span>
          </button>

          <button
            type="button"
            onClick={() => setPaymentMethod('bank')}
            className={`py-3 px-2 rounded-xl text-[12px] font-bold flex flex-col items-center justify-center gap-1 transition-all ${
              paymentMethod === 'bank'
                ? 'bg-[#001428] text-white shadow-sm ring-2 ring-[#001428]'
                : 'bg-white text-[#43474d] border border-[#e2e8f0] hover:bg-[#eff4ff]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">account_balance</span>
            <span>Bank Transfer</span>
          </button>

          <button
            type="button"
            onClick={() => setPaymentMethod('ussd')}
            className={`py-3 px-2 rounded-xl text-[12px] font-bold flex flex-col items-center justify-center gap-1 transition-all ${
              paymentMethod === 'ussd'
                ? 'bg-[#001428] text-white shadow-sm ring-2 ring-[#001428]'
                : 'bg-white text-[#43474d] border border-[#e2e8f0] hover:bg-[#eff4ff]'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">dialpad</span>
            <span>USSD</span>
          </button>
        </div>

        {/* Tab 1: Card Form */}
        {paymentMethod === 'card' && (
          <div className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0] space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-[#f1f5f9]">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-bold text-[#0b1c30]">Debit / Credit Card</span>
                <span className="text-[10px] bg-[#e5eeff] text-[#001428] font-bold px-2 py-0.5 rounded-full">
                  Verve • Mastercard • Visa
                </span>
              </div>
              <div className="flex items-center gap-1 text-[10px] font-extrabold text-[#74777e]">
                <span>SECURED</span>
                <span className="material-symbols-outlined text-[14px] text-emerald-600">lock</span>
              </div>
            </div>

            {/* Saved Card Preview */}
            <div className="bg-[#eff4ff] rounded-xl p-3 flex items-center justify-between border border-[#d1e4ff]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#001428] text-white flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">credit_card</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] font-bold text-[#0b1c30]">•••• 4242</p>
                    <span className="px-1.5 py-0.2 rounded bg-[#ffdbce] text-[#370e00] text-[9px] font-bold">
                      Mastercard
                    </span>
                  </div>
                  <p className="text-[11px] text-[#74777e]">Elena Rostova • Expires 09/27</p>
                </div>
              </div>
              <span className="w-5 h-5 rounded-full bg-[#001428] text-white flex items-center justify-center text-[12px]">
                ✓
              </span>
            </div>

            <button
              type="button"
              onClick={() => setShowNewCardForm(!showNewCardForm)}
              className="text-[11px] text-[#a73a00] font-bold flex items-center gap-1 hover:underline"
            >
              <span className="material-symbols-outlined text-[15px]">
                {showNewCardForm ? 'arrow_drop_up' : 'add'}
              </span>
              <span>{showNewCardForm ? 'Use saved card above' : 'Use a different card'}</span>
            </button>

            {showNewCardForm && (
              <div className="space-y-3 pt-2 border-t border-[#e2e8f0]">
                <div>
                  <label className="text-[11px] text-[#43474d] font-bold block mb-1">Cardholder Name</label>
                  <input
                    type="text"
                    value={cardName}
                    onChange={(e) => setCardName(e.target.value)}
                    className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-[#43474d] font-bold block mb-1">Card Number</label>
                  <input
                    type="text"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] font-mono text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[11px] text-[#43474d] font-bold block mb-1">Expiry</label>
                    <input
                      type="text"
                      value={cardExpiry}
                      onChange={(e) => setCardExpiry(e.target.value)}
                      className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-center text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-[#43474d] font-bold block mb-1">CVV</label>
                    <input
                      type="password"
                      maxLength={3}
                      value={cardCvc}
                      onChange={(e) => setCardCvc(e.target.value)}
                      className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-center text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-[#43474d] font-bold block mb-1">PIN</label>
                    <input
                      type="password"
                      maxLength={4}
                      value={cardPin}
                      onChange={(e) => setCardPin(e.target.value)}
                      className="w-full h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-center text-[#0b1c30] border border-[#d1e4ff] focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Bank Transfer (Simulated Dedicated Escrow Virtual Account) */}
        {paymentMethod === 'bank' && (
          <div className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0] space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#f1f5f9]">
              <div>
                <h4 className="text-[13px] font-bold text-[#0b1c30]">Direct Bank Transfer</h4>
                <p className="text-[11px] text-[#74777e]">Pay into your dedicated Nigerian virtual account</p>
              </div>
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#ffdbce] text-[#370e00] text-[11px] font-bold">
                <span className="material-symbols-outlined text-[14px]">timer</span>
                <span>{transferMinutesLeft}:{transferSecondsLeft < 10 ? `0${transferSecondsLeft}` : transferSecondsLeft}</span>
              </div>
            </div>

            {/* Virtual Account Box */}
            <div className="bg-[#f8f9ff] border-2 border-dashed border-[#001428]/30 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-[#74777e] block">Bank Name</span>
                  <span className="text-[14px] font-bold text-[#001428]">Wema Bank / Providus Bank</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                  Zero Transfer Fee
                </span>
              </div>

              <div className="bg-white rounded-xl p-3 border border-[#e2e8f0] flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-[#74777e] block">Account Number</span>
                  <span className="text-[20px] font-mono font-extrabold text-[#001428] tracking-widest">
                    0129384721
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyAccount}
                  className="px-3 py-1.5 rounded-lg bg-[#001428] text-white text-[11px] font-bold flex items-center gap-1 active:scale-95 transition-all"
                >
                  <span className="material-symbols-outlined text-[14px]">
                    {copiedAccount ? 'check' : 'content_copy'}
                  </span>
                  <span>{copiedAccount ? 'Copied' : 'Copy'}</span>
                </button>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-[#74777e] block">Beneficiary Account Name</span>
                <span className="text-[13px] font-bold text-[#0b1c30]">Mentora Escrow / {expert.name}</span>
              </div>

              <div className="pt-2 border-t border-[#e2e8f0] flex items-center justify-between text-[11px]">
                <span className="text-[#43474d]">Amount to Transfer:</span>
                <span className="font-extrabold text-[15px] text-[#a73a00]">{formatNaira(totalDue)}</span>
              </div>
            </div>

            <div className="p-2.5 bg-[#eff4ff] rounded-xl flex items-center gap-2 border border-[#d1e4ff]">
              <span className="material-symbols-outlined text-[16px] text-[#001428]">verified_user</span>
              <p className="text-[11px] text-[#43474d]">
                Funds are held in secure escrow and released to the scholar only after successful colloquium completion.
              </p>
            </div>
          </div>
        )}

        {/* Tab 3: USSD Payment */}
        {paymentMethod === 'ussd' && (
          <div className="bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0] space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#f1f5f9]">
              <div>
                <h4 className="text-[13px] font-bold text-[#0b1c30]">USSD Quick Dial</h4>
                <p className="text-[11px] text-[#74777e]">Dial code directly on any phone without internet</p>
              </div>
              <span className="text-[11px] font-bold text-[#a73a00]">Instant Confirmation</span>
            </div>

            {/* Select Bank for USSD */}
            <div>
              <label className="text-[11px] text-[#43474d] font-bold block mb-1.5">Select Your Bank:</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {ussdBanks.map((b) => {
                  const isSelected = selectedUssdBank.id === b.id;
                  return (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => setSelectedUssdBank(b)}
                      className={`p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${
                        isSelected
                          ? 'border-[#001428] bg-[#eff4ff] ring-1 ring-[#001428]'
                          : 'border-[#e2e8f0] bg-white hover:bg-[#f8f9ff]'
                      }`}
                    >
                      <span className="text-[12px] font-bold text-[#0b1c30] truncate">{b.name}</span>
                      <span className="text-[11px] font-mono font-bold text-[#a73a00] mt-1">{b.code}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Dial Code Display Box */}
            <div className="bg-[#f8f9ff] border border-[#d1e4ff] rounded-2xl p-3.5 space-y-2 text-center">
              <span className="text-[11px] font-bold uppercase text-[#74777e] tracking-wider block">
                Dial this code on your phone:
              </span>
              <div className="inline-flex items-center gap-2 bg-white px-4 py-2 rounded-xl border border-[#001428]/20 shadow-xs">
                <span className="text-[17px] sm:text-[19px] font-mono font-extrabold text-[#001428] tracking-wider">
                  {dialString}
                </span>
                <button
                  type="button"
                  onClick={handleCopyUssd}
                  className="p-1 rounded-lg hover:bg-[#e5eeff] text-[#001428] transition-colors"
                  title="Copy code"
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {copiedUssd ? 'check' : 'content_copy'}
                  </span>
                </button>
              </div>
              <p className="text-[11px] text-[#43474d]">
                Follow the on-screen prompt on your phone and enter your 4-digit bank USSD PIN to confirm.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Grant Voucher Code input */}
      <div className="w-full bg-[#ffffff] rounded-2xl p-4 shadow-sm border border-[#e2e8f0] mb-5">
        <label className="text-[11px] text-[#43474d] font-bold uppercase tracking-wider block mb-1.5">
          Have an Academic Voucher / Institutional Code?
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={grantVoucherCode}
            onChange={(e) => setGrantVoucherCode(e.target.value)}
            placeholder="e.g. TETFund-2024 / NUC-SCHOLAR"
            className="flex-1 h-10 bg-[#eff4ff] rounded-xl px-3 text-[13px] text-[#0b1c30] uppercase tracking-wider border border-[#d1e4ff] focus:outline-none"
          />
          <button
            type="button"
            onClick={handleApplyVoucher}
            className="px-4 h-10 rounded-xl bg-[#001428] text-white text-[12px] font-bold active:scale-95 transition-all"
          >
            {isVoucherApplied ? 'Applied (-₦2,000)' : 'Apply'}
          </button>
        </div>
      </div>

      {/* Trust & Guarantee */}
      <div className="w-full bg-[#eff4ff] rounded-2xl p-3 mb-4 flex items-center gap-3 border border-[#d1e4ff]/60">
        <div className="w-9 h-9 rounded-full bg-[#d3e4fe] flex items-center justify-center shrink-0 text-[#001428]">
          <span className="material-symbols-outlined text-[20px]">verified_user</span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-bold text-[#0b1c30]">Full Scholar Satisfaction Guarantee</p>
          <p className="text-[11px] text-[#43474d]">
            Simulated payment. Reschedule or cancel up to 2 hours before the session with instant refund.
          </p>
        </div>
      </div>

      {/* Sticky Bottom Checkout Dock */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#ffffff]/95 backdrop-blur-xl shadow-[0_-4px_16px_rgba(15,41,66,0.08)] px-4 py-3 border-t border-[#e2e8f0]">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="flex flex-col shrink-0 min-w-[90px]">
            <span className="text-[10px] uppercase font-bold text-[#43474d] tracking-wider">Amount Due</span>
            <span className="text-[20px] sm:text-[22px] font-extrabold text-[#0b1c30] leading-none">
              {formatNaira(totalDue)}
            </span>
          </div>

          <button
            type="button"
            disabled={isProcessing}
            onClick={handlePay}
            className="flex-1 h-12 py-3 px-4 rounded-xl bg-[#001428] hover:bg-[#0f2942] text-white text-[14px] font-bold flex items-center justify-center gap-2 shadow-md active:scale-[0.98] transition-all disabled:opacity-70"
          >
            {isProcessing ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                <span>Confirming {paymentMethod === 'bank' ? 'Transfer' : paymentMethod === 'ussd' ? 'USSD Session' : 'Payment'}...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[19px]">lock</span>
                <span>
                  {paymentMethod === 'card' && `Pay ${formatNaira(totalDue)} with Card`}
                  {paymentMethod === 'bank' && `I Have Transferred ${formatNaira(totalDue)}`}
                  {paymentMethod === 'ussd' && `Simulate Dial & Pay ${formatNaira(totalDue)}`}
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </main>
  );
};

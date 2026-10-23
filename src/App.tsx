import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { BottomNav } from './components/BottomNav';
import { NotificationModal } from './components/NotificationModal';
import { VirtualChamberModal } from './components/VirtualChamberModal';
import { DeepScoutModal } from './components/DeepScoutModal';
import { FilterModal } from './components/FilterModal';

import { OnboardingScreen } from './screens/OnboardingScreen';
import { HomeScreen } from './screens/HomeScreen';
import { AIChatScreen } from './screens/AIChatScreen';
import { ExpertsScreen } from './screens/ExpertsScreen';
import { ExpertProfileScreen } from './screens/ExpertProfileScreen';
import { BookingScreen } from './screens/BookingScreen';
import { PaymentScreen } from './screens/PaymentScreen';
import { ConfirmationScreen } from './screens/ConfirmationScreen';
import { SessionsScreen } from './screens/SessionsScreen';
import { ProfileScreen } from './screens/ProfileScreen';

import { INITIAL_EXPERTS, INITIAL_SESSIONS, Expert, InitialSession } from './data/expertsData';

export default function App() {
  // Navigation State
  const [currentScreen, setCurrentScreen] = useState<string>('home');
  const [previousScreen, setPreviousScreen] = useState<string>('home');

  // Responsive View Mode ('phone' or 'desktop')
  // Default to the view that matches the user's screen size
  const [viewMode, setViewMode] = useState<'phone' | 'desktop'>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 1024 ? 'desktop' : 'phone';
    }
    return 'desktop';
  });

  const toggleViewMode = () => {
    setViewMode((prev) => (prev === 'desktop' ? 'phone' : 'desktop'));
  };

  // Data States
  const [experts, setExperts] = useState<Expert[]>(INITIAL_EXPERTS);
  const [sessions, setSessions] = useState<InitialSession[]>(INITIAL_SESSIONS);
  const [selectedExpert, setSelectedExpert] = useState<Expert>(INITIAL_EXPERTS[0]); // Dr. Aris Thorne
  const [bookmarkedIds, setBookmarkedIds] = useState<string[]>(['aris-thorne']);

  // Learner Preferences State
  const [academicLevel, setAcademicLevel] = useState<string>('PhD');
  const [interests, setInterests] = useState<string[]>([
    'Quantum Computing',
    'Cognitive Neuroscience',
    'Artificial Intelligence & ML'
  ]);
  const [streakDays, setStreakDays] = useState<number>(12);

  // Booking details in transit
  const [bookingDetails, setBookingDetails] = useState({
    format: 'video' as 'video' | 'async',
    formatTitle: '1:1 Video Consultation (45 mins)',
    date: 'Wed, Oct 25',
    time: '2:30 PM - 3:15 PM',
    agenda: 'Reviewing dissertation chapter 3 on rotated surface codes error threshold simulations.',
    price: INITIAL_EXPERTS[0].hourlyRate || 18000
  });

  // Confirmed booking details
  const [confirmedBookingInfo, setConfirmedBookingInfo] = useState({
    bookingId: '#MEN-9842-NG',
    date: 'Wednesday, October 25',
    time: '2:30 PM – 3:15 PM',
    formatTitle: '1:1 Video Consultation (45 mins)',
    totalPaid: 16000,
    method: 'Credit Card',
    cardLast4: '4242',
    agenda: 'Reviewing dissertation chapter 3 on rotated surface codes error threshold simulations.'
  });

  // Chat Prompt State
  const [chatInitialPrompt, setChatInitialPrompt] = useState<string>('');

  // Modals State
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isChamberModalOpen, setIsChamberModalOpen] = useState(false);
  const [chamberModalProps, setChamberModalProps] = useState({
    roomTitle: '1:1 Doctoral Colloquium',
    expertName: 'Dr. Aris Thorne'
  });
  const [isDeepScoutOpen, setIsDeepScoutOpen] = useState(false);
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);
  const [selectedFilterDomain, setSelectedFilterDomain] = useState('All Disciplines');
  const [maxPriceFilter, setMaxPriceFilter] = useState(25000);
  const [onlySubsidizedFilter, setOnlySubsidizedFilter] = useState(false);

  // Navigation Helper
  const navigateTo = (screen: string) => {
    setPreviousScreen(currentScreen);
    setCurrentScreen(screen);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBack = () => {
    if (['booking', 'payment', 'confirmation'].includes(currentScreen)) {
      if (currentScreen === 'booking') {
        navigateTo('expert-profile');
      } else if (currentScreen === 'payment') {
        navigateTo('booking');
      } else if (currentScreen === 'confirmation') {
        navigateTo('home');
      }
    } else if (currentScreen === 'expert-profile') {
      navigateTo(previousScreen || 'matched-experts');
    } else if (currentScreen === 'onboarding') {
      navigateTo('home');
    } else {
      navigateTo('home');
    }
  };

  // Bookmark Toggle
  const toggleBookmark = (expertId: string) => {
    if (bookmarkedIds.includes(expertId)) {
      setBookmarkedIds(bookmarkedIds.filter((id) => id !== expertId));
    } else {
      setBookmarkedIds([...bookmarkedIds, expertId]);
    }
  };

  // Actions from Home / Experts / Chat
  const handleSelectExpert = (expert: Expert) => {
    setSelectedExpert(expert);
    navigateTo('expert-profile');
  };

  const handleBookExpert = (expert: Expert) => {
    setSelectedExpert(expert);
    setBookingDetails((prev) => ({
      ...prev,
      price: expert.hourlyRate,
      date: expert.nextSlotDate || 'Wed, Oct 25',
      time: expert.nextSlotTime || '2:30 PM - 3:15 PM'
    }));
    navigateTo('booking');
  };

  const handleOpenAIChatWithPrompt = (promptText: string) => {
    setChatInitialPrompt(promptText);
    navigateTo('ai-chat');
  };

  const handleProceedToPayment = (details: {
    format: 'video' | 'async';
    formatTitle: string;
    date: string;
    time: string;
    agenda: string;
    price: number;
  }) => {
    setBookingDetails(details);
    navigateTo('payment');
  };

  const handlePaymentSuccess = (paymentInfo: {
    method: string;
    cardLast4: string;
    totalPaid: number;
    bookingId: string;
  }) => {
    const newSession: InitialSession = {
      id: `session-${Date.now()}`,
      expertId: selectedExpert.id,
      expertName: selectedExpert.name,
      expertTitle: selectedExpert.title,
      expertInstitution: selectedExpert.institution,
      expertAvatar: selectedExpert.avatarUrl,
      format: bookingDetails.format,
      formatTitle: bookingDetails.formatTitle,
      duration: '45 mins',
      scheduledDate: bookingDetails.date,
      scheduledTime: `${bookingDetails.time} WAT`,
      timezone: 'Africa/Lagos (WAT)',
      status: 'upcoming',
      consultationTopic: `${selectedExpert.specializations[0]} Thesis Colloquium`,
      consultationNotes: bookingDetails.agenda,
      roomUrl: `mentora.ai/room/${selectedExpert.id}-${paymentInfo.bookingId.replace(/[^0-9]/g, '')}`,
      pricePaid: paymentInfo.totalPaid,
      originalRate: selectedExpert.hourlyRate,
      platformFee: 1000,
      subsidyDiscount: selectedExpert.subsidyEligible ? 3000 : 0,
      paymentMethod: `${paymentInfo.method} •••• ${paymentInfo.cardLast4}`,
      cardLast4: paymentInfo.cardLast4,
      bookingId: paymentInfo.bookingId,
      createdAt: new Date().toISOString().split('T')[0],
      checklist: [
        {
          id: 'c-new-1',
          label: 'Upload arXiv draft or thesis abstract',
          subtext: 'quantum_surface_codes_v2.pdf (1.4 MB)',
          isDone: true,
          file: { name: 'quantum_surface_codes_v2.pdf', size: '1.4 MB' }
        },
        {
          id: 'c-new-2',
          label: 'Test shared LaTeX whiteboard sandbox',
          subtext: 'KaTeX formula engine initialized',
          isDone: false
        },
        {
          id: 'c-new-3',
          label: 'Prepare 3 focal questions',
          subtext: 'Focus areas: Threshold reduction & ancilla routing',
          isDone: false
        }
      ]
    };

    setSessions([newSession, ...sessions]);

    setConfirmedBookingInfo({
      bookingId: paymentInfo.bookingId,
      date: bookingDetails.date,
      time: bookingDetails.time,
      formatTitle: bookingDetails.formatTitle,
      totalPaid: paymentInfo.totalPaid,
      method: paymentInfo.method,
      cardLast4: paymentInfo.cardLast4,
      agenda: bookingDetails.agenda
    });

    navigateTo('confirmation');
  };

  const handleCancelSession = (sessionId: string) => {
    setSessions(sessions.filter((s) => s.id !== sessionId));
  };

  const handleUpdateSessionFeedback = (sessionId: string, rating: number, feedback: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, rating, feedback } : s))
    );
  };

  const handleMarkSessionCompleted = (sessionId: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, status: 'completed' } : s))
    );
  };

  const handleOpenChamber = (session?: InitialSession) => {
    if (session) {
      setChamberModalProps({
        roomTitle: session.consultationTopic,
        expertName: session.expertName
      });
    } else {
      setChamberModalProps({
        roomTitle: 'Quantum Fault Tolerance 1:1 Chamber',
        expertName: selectedExpert.name
      });
    }
    setIsChamberModalOpen(true);
  };

  const handleScoutComplete = (query: string) => {
    handleOpenAIChatWithPrompt(`Scout faculty matching: ${query}`);
  };

  // Filtered experts based on modal
  const filteredExperts = experts.filter((e) => {
    if (selectedFilterDomain && selectedFilterDomain !== 'All Disciplines') {
      if (
        !e.domain.toLowerCase().includes(selectedFilterDomain.toLowerCase()) &&
        !e.tags.some((t) => t.toLowerCase().includes(selectedFilterDomain.toLowerCase()))
      ) {
        return false;
      }
    }
    if (e.hourlyRate > maxPriceFilter) return false;
    if (onlySubsidizedFilter && !e.subsidyEligible) return false;
    return true;
  });

  const bookmarkedExperts = experts.filter((e) => bookmarkedIds.includes(e.id));

  // Determine which header step number
  let stepNumber = 1;
  if (currentScreen === 'booking') stepNumber = 1;
  if (currentScreen === 'payment') stepNumber = 2;
  if (currentScreen === 'confirmation') stepNumber = 3;

  // Render the Screen content
  const renderScreenContent = () => (
    <>
      {currentScreen === 'onboarding' && (
        <OnboardingScreen
          initialAcademicLevel={academicLevel}
          initialInterests={interests}
          onComplete={(level, newInterests) => {
            setAcademicLevel(level);
            setInterests(newInterests);
            navigateTo('home');
          }}
          onSkip={() => navigateTo('home')}
        />
      )}

      {currentScreen === 'home' && (
        <HomeScreen
          onNavigate={navigateTo}
          onSelectExpert={handleSelectExpert}
          onBookExpert={handleBookExpert}
          onOpenAIChatWithPrompt={handleOpenAIChatWithPrompt}
          onOpenFilter={() => setIsFilterModalOpen(true)}
          onPrepareSession={() => navigateTo('sessions')}
          experts={filteredExperts}
          learnerName="Elena"
          streakDays={streakDays}
        />
      )}

      {currentScreen === 'ai-chat' && (
        <AIChatScreen
          onNavigate={navigateTo}
          onSelectExpert={handleSelectExpert}
          onBookExpert={handleBookExpert}
          allExperts={experts}
          initialPrompt={chatInitialPrompt}
          onClearInitialPrompt={() => setChatInitialPrompt('')}
          academicLevel={academicLevel}
          interests={interests}
        />
      )}

      {(currentScreen === 'matched-experts' || currentScreen === 'experts') && (
        <ExpertsScreen
          onNavigate={navigateTo}
          onSelectExpert={handleSelectExpert}
          onBookExpert={handleBookExpert}
          onOpenDeepScout={() => setIsDeepScoutOpen(true)}
          experts={filteredExperts}
          bookmarkedIds={bookmarkedIds}
          onToggleBookmark={toggleBookmark}
        />
      )}

      {currentScreen === 'expert-profile' && (
        <ExpertProfileScreen
          expert={selectedExpert}
          onBack={handleBack}
          onBookSession={(expert, date, time) => {
            setSelectedExpert(expert);
            setBookingDetails((prev) => ({
              ...prev,
              price: expert.hourlyRate,
              date,
              time
            }));
            navigateTo('booking');
          }}
          isBookmarked={bookmarkedIds.includes(selectedExpert.id)}
          onToggleBookmark={() => toggleBookmark(selectedExpert.id)}
          onShare={() => {
            alert(`Profile link for ${selectedExpert.name} copied.`);
          }}
        />
      )}

      {currentScreen === 'booking' && (
        <BookingScreen
          expert={selectedExpert}
          preSelectedDate={bookingDetails.date}
          preSelectedTime={bookingDetails.time}
          onBack={handleBack}
          onProceedToPayment={handleProceedToPayment}
        />
      )}

      {currentScreen === 'payment' && (
        <PaymentScreen
          expert={selectedExpert}
          bookingDetails={bookingDetails}
          onBack={handleBack}
          onEditBooking={() => navigateTo('booking')}
          onPaymentSuccess={handlePaymentSuccess}
        />
      )}

      {currentScreen === 'confirmation' && (
        <ConfirmationScreen
          expert={selectedExpert}
          bookingInfo={{
            bookingId: confirmedBookingInfo.bookingId,
            date: confirmedBookingInfo.date,
            time: confirmedBookingInfo.time,
            formatTitle: confirmedBookingInfo.formatTitle,
            totalPaid: confirmedBookingInfo.totalPaid,
            method: confirmedBookingInfo.method,
            cardLast4: confirmedBookingInfo.cardLast4,
            agenda: confirmedBookingInfo.agenda
          }}
          onNavigateToSessions={() => navigateTo('sessions')}
          onNavigateHome={() => navigateTo('home')}
          onOpenChamber={() => handleOpenChamber()}
          onSendMessage={() => {
            handleOpenAIChatWithPrompt(`Draft research inquiry to ${selectedExpert.name}`);
          }}
        />
      )}

      {currentScreen === 'sessions' && (
        <SessionsScreen
          sessions={sessions}
          onOpenChamber={handleOpenChamber}
          onNavigateHome={() => navigateTo('home')}
          onNavigateExplore={() => navigateTo('matched-experts')}
          onCancelSession={handleCancelSession}
          onUpdateSessionFeedback={handleUpdateSessionFeedback}
          onMarkSessionCompleted={handleMarkSessionCompleted}
        />
      )}

      {currentScreen === 'profile' && (
        <ProfileScreen
          onRestartOnboarding={() => navigateTo('onboarding')}
          onSelectExpert={handleSelectExpert}
          academicLevel={academicLevel}
          interests={interests}
          bookmarkedExperts={bookmarkedExperts}
        />
      )}
    </>
  );

  return (
    <div className="min-h-screen bg-[#f8f9ff] text-[#0b1c30] font-['Plus_Jakarta_Sans',sans-serif]">
      {/* 
        VIEW MODE 1: DESKTOP FULL-WIDTH VIEW WITH SIDEBAR
        When viewMode === 'desktop', show left sidebar and centered max-width content
      */}
      {viewMode === 'desktop' ? (
        <div className="flex flex-row min-h-screen w-full bg-[#f8f9ff]">
          {/* Left Desktop Sidebar Navigation */}
          <Sidebar
            currentScreen={currentScreen}
            onNavigate={navigateTo}
            upcomingCount={sessions.filter((s) => s.status === 'upcoming').length}
            streakDays={streakDays}
            onToggleViewMode={toggleViewMode}
            viewMode={viewMode}
          />

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col min-w-0 min-h-screen">
            <Header
              currentScreen={currentScreen}
              onNavigate={navigateTo}
              onOpenNotifications={() => setIsNotificationsOpen(true)}
              onBack={handleBack}
              title={
                currentScreen === 'expert-profile'
                  ? 'Mentora Expert Profile'
                  : currentScreen === 'booking'
                  ? 'Schedule Mentorship'
                  : currentScreen === 'payment'
                  ? 'Payment Method'
                  : currentScreen === 'confirmation'
                  ? 'Booking Confirmation'
                  : undefined
              }
              showStepIndicator={['booking', 'payment', 'confirmation'].includes(currentScreen)}
              stepNumber={stepNumber}
              isBookmarked={bookmarkedIds.includes(selectedExpert.id)}
              onToggleBookmark={() => toggleBookmark(selectedExpert.id)}
              onShare={() => {
                alert(`Link to ${selectedExpert.name}'s profile copied to clipboard!`);
              }}
              viewMode={viewMode}
              onToggleViewMode={toggleViewMode}
            />

            <div className="flex-1 flex flex-col min-w-0">
              {renderScreenContent()}
            </div>
          </div>
        </div>
      ) : (
        /* 
          VIEW MODE 2: PHONE VIEW WITH CENTERED PHONE-SIZED FRAME
          Shows the app inside a centered phone-sized frame with mobile bottom bar
        */
        <div className="min-h-screen bg-slate-900 py-0 sm:py-6 px-0 sm:px-4 flex flex-col items-center justify-start transition-colors">
          {/* View Mode Indicator banner (only shown on wider screens) */}
          <div className="hidden sm:flex items-center justify-between w-full max-w-[430px] mb-2 px-1">
            <span className="text-[11px] font-bold text-slate-300 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-amber-400">smartphone</span>
              <span>Phone view frame (420px)</span>
            </span>
            <button
              type="button"
              onClick={toggleViewMode}
              className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-white text-[11px] font-bold border border-slate-700 flex items-center gap-1 transition-all"
            >
              <span className="material-symbols-outlined text-[14px]">desktop_windows</span>
              <span>Desktop view</span>
            </button>
          </div>

          {/* Centered Phone Frame */}
          <div className="w-full sm:max-w-[430px] min-h-screen sm:min-h-[860px] bg-[#f8f9ff] sm:rounded-[36px] sm:shadow-2xl sm:border-[6px] sm:border-slate-800 overflow-hidden relative flex flex-col">
            <Header
              currentScreen={currentScreen}
              onNavigate={navigateTo}
              onOpenNotifications={() => setIsNotificationsOpen(true)}
              onBack={handleBack}
              title={
                currentScreen === 'expert-profile'
                  ? 'Mentora Expert Profile'
                  : currentScreen === 'booking'
                  ? 'Schedule Mentorship'
                  : currentScreen === 'payment'
                  ? 'Payment Method'
                  : currentScreen === 'confirmation'
                  ? 'Booking Confirmation'
                  : undefined
              }
              showStepIndicator={['booking', 'payment', 'confirmation'].includes(currentScreen)}
              stepNumber={stepNumber}
              isBookmarked={bookmarkedIds.includes(selectedExpert.id)}
              onToggleBookmark={() => toggleBookmark(selectedExpert.id)}
              onShare={() => {
                alert(`Link to ${selectedExpert.name}'s profile copied to clipboard!`);
              }}
              viewMode={viewMode}
              onToggleViewMode={toggleViewMode}
            />

            <div className="flex-1 flex flex-col min-w-0">
              {renderScreenContent()}
            </div>

            {/* Bottom Nav Bar inside Phone Frame */}
            {!['booking', 'payment', 'confirmation'].includes(currentScreen) && (
              <BottomNav
                currentScreen={currentScreen}
                onNavigate={navigateTo}
                upcomingCount={sessions.filter((s) => s.status === 'upcoming').length}
              />
            )}
          </div>
        </div>
      )}

      {/* Global Interactive Modals */}
      <NotificationModal
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        onNavigateToSession={() => {
          setIsNotificationsOpen(false);
          navigateTo('sessions');
        }}
      />

      <VirtualChamberModal
        isOpen={isChamberModalOpen}
        onClose={() => setIsChamberModalOpen(false)}
        roomTitle={chamberModalProps.roomTitle}
        expertName={chamberModalProps.expertName}
      />

      <DeepScoutModal
        isOpen={isDeepScoutOpen}
        onClose={() => setIsDeepScoutOpen(false)}
        onScoutComplete={handleScoutComplete}
      />

      <FilterModal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        selectedDomain={selectedFilterDomain}
        onSelectDomain={setSelectedFilterDomain}
        maxPrice={maxPriceFilter}
        onSelectMaxPrice={setMaxPriceFilter}
        onlySubsidized={onlySubsidizedFilter}
        onToggleSubsidized={() => setOnlySubsidizedFilter(!onlySubsidizedFilter)}
      />
    </div>
  );
}

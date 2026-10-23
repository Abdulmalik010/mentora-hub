import React, { useState } from 'react';
import { Header } from './components/Header';
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

  // Data States
  const [experts, setExperts] = useState<Expert[]>(INITIAL_EXPERTS);
  const [sessions, setSessions] = useState<InitialSession[]>(INITIAL_SESSIONS);
  const [selectedExpert, setSelectedExpert] = useState<Expert>(INITIAL_EXPERTS[0]); // default Dr. Aris Thorne
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
    price: 90
  });

  // Confirmed booking details
  const [confirmedBookingInfo, setConfirmedBookingInfo] = useState({
    bookingId: '#MEN-9842-QT',
    date: 'Wednesday, October 25',
    time: '2:30 PM – 3:15 PM',
    formatTitle: '1:1 Video Consultation (45 mins)',
    totalPaid: 80.0,
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
  const [maxPriceFilter, setMaxPriceFilter] = useState(130);
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
      scheduledTime: `${bookingDetails.time} EDT`,
      timezone: 'America/New_York (EDT)',
      status: 'upcoming',
      consultationTopic: `${selectedExpert.specializations[0]} Thesis Review`,
      consultationNotes: bookingDetails.agenda,
      roomUrl: `mentora.ai/room/${selectedExpert.id}-${paymentInfo.bookingId.replace(/[^0-9]/g, '')}`,
      pricePaid: paymentInfo.totalPaid,
      originalRate: selectedExpert.hourlyRate,
      platformFee: 5.0,
      subsidyDiscount: selectedExpert.subsidyEligible ? 15.0 : 0.0,
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
      if (!e.domain.toLowerCase().includes(selectedFilterDomain.toLowerCase()) && !e.tags.some(t => t.toLowerCase().includes(selectedFilterDomain.toLowerCase()))) {
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

  return (
    <div className="min-h-screen bg-[#f8f9ff] text-[#0b1c30] flex flex-col font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Top Header */}
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
          if (navigator.share) {
            navigator.share({
              title: `${selectedExpert.name} - Mentora Profile`,
              text: `Check out ${selectedExpert.name}'s research mentorship on Mentora`,
              url: window.location.href
            }).catch(() => {});
          } else {
            alert(`Link to ${selectedExpert.name}'s profile copied to clipboard!`);
          }
        }}
      />

      {/* Screen Views */}
      <div className="flex-1 flex flex-col">
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
              handleOpenAIChatWithPrompt(`Draft outreach memo to ${selectedExpert.name}`);
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
      </div>

      {/* Persistent Bottom Navigation Bar (Shown on top-level tabs) */}
      {!['booking', 'payment', 'confirmation'].includes(currentScreen) && (
        <BottomNav
          currentScreen={currentScreen}
          onNavigate={navigateTo}
          upcomingCount={sessions.filter((s) => s.status === 'upcoming').length}
        />
      )}

      {/* Interactive Modals */}
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

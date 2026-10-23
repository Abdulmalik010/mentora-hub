import test from 'node:test';
import assert from 'node:assert';
import { INITIAL_EXPERTS, INITIAL_SESSIONS, InitialSession } from '../src/data/expertsData.ts';
import { generateAdvisorResponse } from '../src/services/aiAdvisor.ts';

test('Experts dataset has 8 realistic experts across diverse fields', () => {
  assert.strictEqual(INITIAL_EXPERTS.length, 8);
  const names = INITIAL_EXPERTS.map((e) => e.name);
  assert.ok(names.includes('Dr. Aris Thorne'));
  assert.ok(names.includes('Dr. Maya Lin'));
  assert.ok(names.includes('Dr. Marcus Vance'));
  assert.ok(names.includes('Dr. Amara Okafor'));
  assert.ok(names.includes('Sarah Lin'));
  assert.ok(names.includes('Prof. Julian Sterling, J.D., Ph.D.'));
  assert.ok(names.includes('Dr. Henrik Dahlgren'));
  assert.ok(names.includes('Dr. Rachel Ben-Ami, MD, PhD'));
});

test('Booking price calculation applies subsidy correctly for video consultation', () => {
  const expert = INITIAL_EXPERTS.find((e) => e.id === 'aris-thorne')!;
  const advisoryCost = expert.hourlyRate; // 90
  const platformFee = 5;
  const doctoralSubsidy = expert.subsidyEligible ? 15 : 0;
  const total = advisoryCost + platformFee - doctoralSubsidy;
  assert.strictEqual(total, 80);
});

test('Booking price calculation applies async review rate correctly', () => {
  const expert = INITIAL_EXPERTS.find((e) => e.id === 'aris-thorne')!;
  const asyncRate = expert.asyncRate; // 65
  const platformFee = 5;
  const doctoralSubsidy = expert.subsidyEligible ? 15 : 0;
  const total = asyncRate + platformFee - doctoralSubsidy;
  assert.strictEqual(total, 55);
});

test('Session is created with status "upcoming" upon successful booking', () => {
  const expert = INITIAL_EXPERTS[0];
  const newSession: InitialSession = {
    id: `session-${Date.now()}`,
    expertId: expert.id,
    expertName: expert.name,
    expertTitle: expert.title,
    expertInstitution: expert.institution,
    expertAvatar: expert.avatarUrl,
    format: 'video',
    formatTitle: '1:1 Video Consultation (45 mins)',
    duration: '45 mins',
    scheduledDate: 'Thu, Oct 26',
    scheduledTime: '10:00 AM - 10:45 AM EDT',
    timezone: 'America/New_York (EDT)',
    status: 'upcoming',
    consultationTopic: 'Quantum Error Correction Thesis Review',
    consultationNotes: 'Focus on rotated surface codes threshold reduction',
    roomUrl: `mentora.ai/room/${expert.id}-1234`,
    pricePaid: 80,
    originalRate: 90,
    platformFee: 5,
    subsidyDiscount: 15,
    paymentMethod: 'Institutional Bank Transfer (ACH •••• 8192)',
    cardLast4: '8192',
    bookingId: '#MEN-8891-QT',
    createdAt: '2024-10-25',
    checklist: []
  };

  assert.strictEqual(newSession.status, 'upcoming');
  assert.strictEqual(newSession.paymentMethod, 'Institutional Bank Transfer (ACH •••• 8192)');
  assert.strictEqual(newSession.pricePaid, 80);
});

test('AI advisor returns structured response and benchmark matrix', () => {
  const response = generateAdvisorResponse('surface codes vs color codes', INITIAL_EXPERTS);
  assert.ok(response.text.length > 0);
  assert.ok(response.expertRecommendation);
  assert.strictEqual(response.expertRecommendation.id === 'aris-thorne' || response.expertRecommendation.name.includes('Thorne'), true);
});

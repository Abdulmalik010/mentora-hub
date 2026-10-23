export interface Review {
  id: string;
  author: string;
  role: string;
  rating: number;
  text: string;
}

export interface Slot {
  time: string;
  period: 'morning' | 'afternoon';
  isAvailable: boolean;
  isBestFit?: boolean;
}

export interface DayAvailability {
  dateKey: string;
  dayName: string;
  dateNum: string;
  monthName: string;
  slotsCount: string;
  slots: Slot[];
}

export interface Expert {
  id: string;
  name: string;
  title: string;
  institution: string;
  affiliationShort: string;
  department: string;
  domain: string;
  avatarUrl: string;
  isVerified: boolean;
  rating: number;
  reviewCount: number;
  papersCited: number;
  mentoringHours: number;
  scholarsGuided: number;
  yearsExperience: number;
  hourlyRate: number; // in Naira (₦5,000 - ₦25,000)
  asyncRate: number; // in Naira
  nextSlotText: string;
  nextSlotTime: string;
  nextSlotDate: string;
  matchScore: number;
  matchLabel: string;
  badgeVariant?: 'top' | 'fellow' | 'visiting';
  subsidyEligible: boolean;
  subsidyLabel: string;
  tags: string[];
  specializations: string[];
  degrees: string[];
  bio: string;
  reviews: Review[];
  days: DayAvailability[];
}

export interface InitialSession {
  id: string;
  expertId: string;
  expertName: string;
  expertTitle: string;
  expertInstitution: string;
  expertAvatar: string;
  format: 'video' | 'async';
  formatTitle: string;
  duration: string;
  scheduledDate: string;
  scheduledTime: string;
  timezone: string;
  status: 'upcoming' | 'completed' | 'cancelled';
  consultationTopic: string;
  consultationNotes: string;
  roomUrl: string;
  pricePaid: number;
  originalRate: number;
  platformFee: number;
  subsidyDiscount: number;
  paymentMethod: string;
  cardLast4?: string;
  bookingId: string;
  createdAt: string;
  checklist: {
    id: string;
    label: string;
    subtext?: string;
    isDone: boolean;
    file?: { name: string; size: string };
  }[];
  rating?: number;
  feedback?: string;
}

export function formatNaira(amount: number): string {
  try {
    const formatted = new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
    return formatted.replace('NGN', '₦').trim();
  } catch {
    return `₦${amount.toLocaleString('en-NG')}`;
  }
}

export const INITIAL_EXPERTS: Expert[] = [
  {
    id: 'aris-thorne',
    name: 'Dr. Aris Thorne',
    title: 'Associate Professor of Quantum Information Science',
    institution: 'MIT & Harvard Quantum Initiative',
    affiliationShort: 'MIT QIC Lab • Harvard Fellow',
    department: 'Director, Quantum Fault-Tolerance Group @ MIT',
    domain: 'Quantum Computing',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAQvXUeV2LR8eOr1nfW_ZP3dJbQWT1d-wN8b61rvam5cMHlI4IoK_EEIkgq91cOKU4S2vvOGq0RWoq0c5o8-zRJiKdlsbEpnN7x_3w1iP3Q5iR6RQMBhSYnoo-JT_tNjtUAWaGmTDz0SkCelB5sqBSTtT8Bmov5_SrmicEoA1SHHhGFHWEm40ArRznJkN3e42CBvMqiuDwLMF85YQhYYH5_MOIvSXXvL-iBQYnm2iEjh6GWxbgOi94j',
    isVerified: true,
    rating: 4.98,
    reviewCount: 124,
    papersCited: 142,
    mentoringHours: 940,
    scholarsGuided: 310,
    yearsExperience: 14,
    hourlyRate: 18000,
    asyncRate: 12000,
    nextSlotText: 'Tomorrow, 2:30 PM EST',
    nextSlotTime: '2:30 PM - 3:15 PM',
    nextSlotDate: 'Wed, Oct 25',
    matchScore: 98,
    matchLabel: '98% Match • Top Faculty',
    badgeVariant: 'top',
    subsidyEligible: true,
    subsidyLabel: 'Eligible for Doctoral Subsidy (Mentora Grant)',
    tags: ['Quantum Error Correction', 'Surface Codes', 'Fault Tolerance', 'Superconducting Qubits'],
    specializations: [
      'Surface Codes',
      'Fault-Tolerant Architectures',
      'Transversal Clifford Gates',
      'PhD Thesis Defense Prep',
      'Grant & Fellowship Reviews',
      'arXiv Pre-print Critique'
    ],
    degrees: ['Ph.D. Physics (Caltech)', 'M.S. Applied Math (Princeton)'],
    bio: 'Dr. Thorne’s research focuses on quantum error correction architectures, specializing in threshold reduction for rotated surface codes and topological lattice surgery. He regularly advises doctoral candidates, postdocs, and R&D engineers on thesis formulation, arXiv preprint peer audits, and scalable Hamiltonian simulations.',
    reviews: [
      {
        id: 'r1',
        author: 'Elena Rostova',
        role: 'PhD Candidate, Cambridge',
        rating: 5,
        text: '“Dr. Thorne pinpointed the flaw in my non-Clifford state distillation protocol within 20 minutes. Invaluable guidance for my doctoral proposal defense!”'
      },
      {
        id: 'r2',
        author: 'Marcus Chen',
        role: 'Quantum Hardware Engineer',
        rating: 5,
        text: '“Incredible depth on rotated surface codes. Saved us weeks of computational simulation time.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-25',
        dayName: 'Wed',
        dateNum: '25',
        monthName: 'Oct',
        slotsCount: '4 slots',
        slots: [
          { time: '10:00 - 10:45 AM', period: 'morning', isAvailable: false },
          { time: '11:30 - 12:15 PM', period: 'morning', isAvailable: true },
          { time: '2:30 PM - 3:15 PM', period: 'afternoon', isAvailable: true, isBestFit: true },
          { time: '4:00 - 4:45 PM', period: 'afternoon', isAvailable: true },
          { time: '5:30 - 6:15 PM', period: 'afternoon', isAvailable: true }
        ]
      },
      {
        dateKey: '2024-10-26',
        dayName: 'Thu',
        dateNum: '26',
        monthName: 'Oct',
        slotsCount: '2 slots',
        slots: [
          { time: '1:00 PM - 1:45 PM', period: 'afternoon', isAvailable: true },
          { time: '3:30 PM - 4:15 PM', period: 'afternoon', isAvailable: true }
        ]
      },
      {
        dateKey: '2024-10-27',
        dayName: 'Fri',
        dateNum: '27',
        monthName: 'Oct',
        slotsCount: '3 slots',
        slots: [
          { time: '10:30 - 11:15 AM', period: 'morning', isAvailable: true },
          { time: '2:00 PM - 2:45 PM', period: 'afternoon', isAvailable: true },
          { time: '4:30 PM - 5:15 PM', period: 'afternoon', isAvailable: true }
        ]
      },
      {
        dateKey: '2024-10-30',
        dayName: 'Mon',
        dateNum: '30',
        monthName: 'Oct',
        slotsCount: '5 slots',
        slots: [
          { time: '9:00 - 9:45 AM', period: 'morning', isAvailable: true },
          { time: '11:00 - 11:45 AM', period: 'morning', isAvailable: true },
          { time: '1:30 PM - 2:15 PM', period: 'afternoon', isAvailable: true },
          { time: '3:00 PM - 3:45 PM', period: 'afternoon', isAvailable: true }
        ]
      },
      {
        dateKey: '2024-10-31',
        dayName: 'Tue',
        dateNum: '31',
        monthName: 'Oct',
        slotsCount: '1 slot',
        slots: [
          { time: '2:00 PM - 2:45 PM', period: 'afternoon', isAvailable: true }
        ]
      }
    ]
  },
  {
    id: 'maya-lin',
    name: 'Dr. Maya Lin',
    title: 'Lead Quantum Architect & Adjunct Faculty',
    institution: 'Stanford Q-Farm & IBM Fellow',
    affiliationShort: 'Stanford & IBM Research',
    department: 'Department of Applied Physics, Stanford University',
    domain: 'Quantum Computing',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAMAiJynLBpQwZSx__MxXrMhhAIoyVLdo6ivXMbAoUCeGzPDt9JrO7ivf_1kXu51Ggh5jLVgoBWrmp0UtMTV6a_D8oS5HpxoJJQGZv0UQx-g65zddfSC_LRt2JpZwcmPzcUWS_b32-2jmS74dPTptsEGYWHMeiqptCIU1t487OwWRTN4xI_4Q_r1s15QxYWb27qfJnqeMEaVM8c8GAJ1tjGuYfHyHObex8W4nIXkRlAV6E181ncYT0G',
    isVerified: true,
    rating: 4.95,
    reviewCount: 88,
    papersCited: 65,
    mentoringHours: 410,
    scholarsGuided: 180,
    yearsExperience: 9,
    hourlyRate: 22000,
    asyncRate: 15000,
    nextSlotText: 'Thursday, 10:00 AM PST',
    nextSlotTime: '10:00 AM - 10:45 AM',
    nextSlotDate: 'Thu, Oct 26',
    matchScore: 95,
    matchLabel: '95% Match • Industry Fellow',
    badgeVariant: 'fellow',
    subsidyEligible: true,
    subsidyLabel: 'Subsidized via Industry Co-Sponsor',
    tags: ['Topological Computing', 'Lattice Surgery', 'Qubit Compilers', 'Cryo-CMOS'],
    specializations: [
      'Topological Braiding Protocols',
      'Quantum Compiler Optimization',
      'Lattice Surgery Routing',
      'Hardware-Software Co-Design'
    ],
    degrees: ['Ph.D. Electrical Engineering (Stanford)', 'B.S. Physics (UC Berkeley)'],
    bio: 'Lead quantum computer architecture researcher bridging theoretical topological models with physical superconducting and trapped-ion foundry realities.',
    reviews: [
      {
        id: 'r3',
        author: 'Julian Weismann',
        role: 'ETH Zürich Postdoc',
        rating: 5,
        text: '“Dr. Lin gave razor-sharp advice on compiler scheduling for non-local gates. Essential for our Nature Physics submission.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-26',
        dayName: 'Thu',
        dateNum: '26',
        monthName: 'Oct',
        slotsCount: '3 slots',
        slots: [
          { time: '10:00 AM - 10:45 AM', period: 'morning', isAvailable: true, isBestFit: true },
          { time: '2:00 PM - 2:45 PM', period: 'afternoon', isAvailable: true }
        ]
      }
    ]
  },
  {
    id: 'amara-okafor',
    name: 'Dr. Amara Okafor',
    title: 'Chair of Biomedical Sciences · Senior Fellow',
    institution: 'Oxford Quantum Hub & Biomedical Research',
    affiliationShort: 'Oxford Institute of Molecular Medicine',
    department: 'Chair of Genomic Diagnostics, University of Oxford',
    domain: 'Medicine & Bioengineering',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBOO2NjZ1r_fDi_YQeTGxpQ0jpS8OTnrj19zTGTx312SRTCTp5dbGfjEB1DDWcaI2EoG7lFaiiRXyZwXWojvm36EM-FJMpp8uzH6wZyF7DlPDXKcsbySgK3LD5fODi-0iDgEwgnpK0gBPJHpse32xqDfiWGmn1mUEOMzzxes8xWcW2fuMqC-VHHg0xFDEPenEyTslKOMWgk5qRFk45kQwW5ZF1REiK6I-xqiqks3DWh_A17i5CnCDja',
    isVerified: true,
    rating: 4.95,
    reviewCount: 210,
    papersCited: 84,
    mentoringHours: 580,
    scholarsGuided: 240,
    yearsExperience: 12,
    hourlyRate: 7500,
    asyncRate: 5000,
    nextSlotText: 'Friday, 4:00 PM GMT',
    nextSlotTime: '4:00 PM - 4:45 PM',
    nextSlotDate: 'Fri, Oct 27',
    matchScore: 92,
    matchLabel: '92% Match • Visiting Scholar',
    badgeVariant: 'visiting',
    subsidyEligible: true,
    subsidyLabel: 'Wellcome Trust Subsidized Rate',
    tags: ['Genomic Therapeutics', 'Oxford Fellowships', 'Cryogenic Control', 'Bioengineering'],
    specializations: [
      'CRISPR Cas12/13 Mechanisms',
      'Oxford Doctoral Fellowship Defense',
      'Single-Cell RNA Sequencing Audits',
      'Translational Oncology Proposals'
    ],
    degrees: ['D.Phil. Molecular Medicine (Oxford)', 'M.B.Ch.B. (Imperial College London)'],
    bio: 'Poised researcher heading international collaborative programs on synthetic biology and gene circuit engineering. Has mentored over 20 Rhodes and Gates Cambridge scholars.',
    reviews: [
      {
        id: 'r4',
        author: 'Nadia Solis',
        role: 'MD-PhD Candidate, Johns Hopkins',
        rating: 5,
        text: '“Her structural critique of our therapeutic target delivery paper completely changed how we framed our hypothesis.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-27',
        dayName: 'Fri',
        dateNum: '27',
        monthName: 'Oct',
        slotsCount: '2 slots',
        slots: [
          { time: '11:00 AM - 11:45 AM', period: 'morning', isAvailable: true },
          { time: '4:00 PM - 4:45 PM', period: 'afternoon', isAvailable: true, isBestFit: true }
        ]
      }
    ]
  },
  {
    id: 'marcus-vance',
    name: 'Dr. Marcus Vance',
    title: 'Professor of AI & Autonomous Robotics',
    institution: 'MIT CSAIL & Robotics Directorate',
    affiliationShort: 'MIT Autonomous Systems Lab',
    department: 'Department of Electrical Engineering & Computer Science',
    domain: 'Data Science & AI',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDbkBvX2xDC5QVclyndADZ5fjTvS3dMPCmW7jgNzAIzkimikBZw2Mitj0yvxgp-Aw7jxA76VzwuZfzZr_J1_y0V_QQ6mO5PLvdHmP1BOOzY5v_4jL9Si2z38_0jW_IgP7KiixxVx63sY5eiQ9TQi8HmkaqBpC3Lw9Dc0-3zr5LbCdTWEc6yIbm_r71zNXkmuYAyOTIRlGQtW34Iq_U0A1MGAY0MWZhVenWCG1pPtFsWBWRgUjCQFPWl',
    isVerified: true,
    rating: 4.90,
    reviewCount: 140,
    papersCited: 118,
    mentoringHours: 520,
    scholarsGuided: 195,
    yearsExperience: 16,
    hourlyRate: 15000,
    asyncRate: 10000,
    nextSlotText: 'Tomorrow at 3:00 PM EST',
    nextSlotTime: '3:00 PM - 3:45 PM',
    nextSlotDate: 'Wed, Oct 25',
    matchScore: 96,
    matchLabel: '96% Match • Office Hours Today',
    badgeVariant: 'top',
    subsidyEligible: true,
    subsidyLabel: 'NSF / Mentora Doctoral Grant Eligible',
    tags: ['Autonomous Systems', 'Neural Kinematics', 'Reinforcement Learning', 'SLAM'],
    specializations: [
      'Neural Kinematics & Motion Planning',
      'Embodied Foundation Models',
      'DARPA Challenge Defense',
      'Hardware-in-the-Loop Simulators'
    ],
    degrees: ['Ph.D. Robotics (Carnegie Mellon)', 'B.S. Mechatronics (ETH Zürich)'],
    bio: 'Distinguished pioneer in adaptive neural controllers and embodied reinforcement learning for legged and humanoid platforms. Regular advisor to DARPA challenge finalists.',
    reviews: [
      {
        id: 'r5',
        author: 'Liam Vance-Perez',
        role: 'Robotics Engineer, Boston Dynamics',
        rating: 5,
        text: '“Dr. Vance broke down our non-linear trajectory stabilization equation in 15 minutes. Unrivaled academic and practical grasp.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-25',
        dayName: 'Wed',
        dateNum: '25',
        monthName: 'Oct',
        slotsCount: '3 slots',
        slots: [
          { time: '11:00 AM - 11:45 AM', period: 'morning', isAvailable: true },
          { time: '3:00 PM - 3:45 PM', period: 'afternoon', isAvailable: true, isBestFit: true }
        ]
      }
    ]
  },
  {
    id: 'sarah-lin',
    name: 'Sarah Lin',
    title: 'Principal Product Lead · ex-Stanford Fellow',
    institution: 'Stanford d.school & Tech Executive Advising',
    affiliationShort: 'Silicon Valley & Stanford Fellow',
    department: 'Center for Executive Product Leadership',
    domain: 'Business & Tech Strategy',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDUSXjCb8tDmWCORrQr8vbfACLC5H_uxn_zKtJfY3tUoyFGhsekpnoRZfdJezSitU-dCc8GaRsnCc5QlYhMbJti6hIODz01sZkI7Dd-P41dmDUwK2Hlll44AQ7bn5LJ85fRgithnf_AwLlsV3uSq9C2ceI1JT4FPHK2lNwvej2xSlNGV4Ljzcvmxxvw9GOoOFd92bGIquF6D2MSPeJDgvVab3VaYJE3FwGBnuYDbWN9eczAdTq1maHg',
    isVerified: true,
    rating: 5.0,
    reviewCount: 95,
    papersCited: 42,
    mentoringHours: 600,
    scholarsGuided: 210,
    yearsExperience: 11,
    hourlyRate: 5000,
    asyncRate: 3500,
    nextSlotText: 'Available Thu, 1:00 PM PST',
    nextSlotTime: '1:00 PM - 1:45 PM',
    nextSlotDate: 'Thu, Oct 26',
    matchScore: 94,
    matchLabel: '94% Match • Executive Mentor',
    badgeVariant: 'fellow',
    subsidyEligible: false,
    subsidyLabel: 'Corporate / Startup Sponsorship Supported',
    tags: ['Career Pivot', 'Tech Thesis Defense', 'Product Strategy', 'Venture Pitching'],
    specializations: [
      'Academic-to-Industry Leadership Pivot',
      'Deep Tech Go-to-Market Formulations',
      'Series A Technical Pitch Decks',
      'AI Product Roadmapping'
    ],
    degrees: ['M.B.A. (Stanford GSB)', 'B.S. Symbolic Systems (Stanford)'],
    bio: 'Former senior director at tier-one tech venture labs and adjunct product strategist. Mentors doctoral graduates transitioning into high-growth enterprise product leadership.',
    reviews: [
      {
        id: 'r6',
        author: 'Tara Sundaram',
        role: 'Founder, Cognitive AI',
        rating: 5,
        text: '“Sarah helped me translate 4 years of cognitive neuroscience research into a compelling venture thesis and seed deck.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-26',
        dayName: 'Thu',
        dateNum: '26',
        monthName: 'Oct',
        slotsCount: '2 slots',
        slots: [
          { time: '1:00 PM - 1:45 PM', period: 'afternoon', isAvailable: true, isBestFit: true },
          { time: '4:00 PM - 4:45 PM', period: 'afternoon', isAvailable: true }
        ]
      }
    ]
  },
  {
    id: 'julian-sterling',
    name: 'Prof. Julian Sterling, J.D., Ph.D.',
    title: 'Professor of Constitutional Law & AI Governance',
    institution: 'Yale Law School & Information Society Project',
    affiliationShort: 'Yale Law School Faculty',
    department: 'Center for Algorithmic Jurisprudence',
    domain: 'Constitutional Law',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDUMOAm1cLfbR5AZLD4Y3XtORnsxMxO1rgIQHVqZOKAuynaJS7SqMFYKrPiCCLyN7mNwWGqzRlDOl6RtYyK16W5u4uSaEBEzPjv8M3hN0TAksxifUZqvqHojOf2Bd_hX8UIm3EjAuJ3DzVgGwk2Ss70MawMp4hqxEzE3YjnIXBH4twlWA8BM-1Rumu0cftRjA65ymjnLSFCNeFVm8kwqtUcsbE4iblitpiT4CFELjDQEGKNGV50_UyH',
    isVerified: true,
    rating: 4.96,
    reviewCount: 110,
    papersCited: 96,
    mentoringHours: 380,
    scholarsGuided: 160,
    yearsExperience: 18,
    hourlyRate: 25000,
    asyncRate: 17500,
    nextSlotText: 'Friday, 11:30 AM EST',
    nextSlotTime: '11:30 AM - 12:15 PM',
    nextSlotDate: 'Fri, Oct 27',
    matchScore: 91,
    matchLabel: '91% Match • Law & Policy Scholar',
    badgeVariant: 'visiting',
    subsidyEligible: true,
    subsidyLabel: 'Yale ISP Student Subsidy Available',
    tags: ['AI Governance', 'Constitutional Law', 'IP & Tech Patent', 'Moot Court'],
    specializations: [
      'Generative AI Copyright & Fair Use',
      'Supreme Court Moot Argument Defense',
      'Antitrust & Digital Platform Regulation',
      'Law Review Scholarly Editing'
    ],
    degrees: ['J.D. (Yale Law School)', 'Ph.D. Political Philosophy (Oxford)'],
    bio: 'Leading scholar on algorithmic accountability, constitutional property rights in training data, and appellate advocacy before federal circuits.',
    reviews: [
      {
        id: 'r7',
        author: 'Courtney Vance',
        role: 'Law Clerk, US 2nd Circuit',
        rating: 5,
        text: '“His mock moot questioning was twice as fierce as the real bench. Passed our appellate defense with flying colors.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-27',
        dayName: 'Fri',
        dateNum: '27',
        monthName: 'Oct',
        slotsCount: '2 slots',
        slots: [
          { time: '11:30 AM - 12:15 PM', period: 'morning', isAvailable: true, isBestFit: true },
          { time: '3:00 PM - 3:45 PM', period: 'afternoon', isAvailable: true }
        ]
      }
    ]
  },
  {
    id: 'henrik-dahlgren',
    name: 'Dr. Henrik Dahlgren',
    title: 'Chair of Behavioral Data Science & Econometrics',
    institution: 'London School of Economics (LSE) & Turing Institute',
    affiliationShort: 'LSE & Alan Turing Institute',
    department: 'Department of Economics & Data Science',
    domain: 'Behavioral Economics',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAYXQaOdGLSwD6CvUNKCjlVP6EVOzEVVMfX0GftIAGJPfNjaBe_-O2aoCbrEu3AzKuVCAVIKcmIH5sM8MjjsmekScLv5BVWCEJbWd3Xtt112lhW8CxVzNDKBOpv0tnne7YBkidxmsx24Uf9udv7X1T3D7-w3879hrb_lHwJ7mHqd9XdkHks4QLoTw02A_fSQFdnTE9fBRPB0kiPnX15ybSPyueisoZ3_GIEcqRfk1LX57-0eahJo-Mq',
    isVerified: true,
    rating: 4.93,
    reviewCount: 75,
    papersCited: 78,
    mentoringHours: 340,
    scholarsGuided: 130,
    yearsExperience: 13,
    hourlyRate: 10000,
    asyncRate: 7000,
    nextSlotText: 'Monday, 2:00 PM GMT',
    nextSlotTime: '2:00 PM - 2:45 PM',
    nextSlotDate: 'Mon, Oct 30',
    matchScore: 93,
    matchLabel: '93% Match • Senior Fellow',
    badgeVariant: 'fellow',
    subsidyEligible: true,
    subsidyLabel: 'ESRC Subsidized Research Tier',
    tags: ['Causal Inference', 'Behavioral Economics', 'Econometrics', 'Market Design'],
    specializations: [
      'Quasi-Experimental Difference-in-Differences',
      'Instrumental Variable Strategy Review',
      'Behavioral Market Game Simulations',
      'NBER Working Paper Audit'
    ],
    degrees: ['Ph.D. Economics (Stockholm School of Economics)', 'M.Phil. Economics (Oxford)'],
    bio: 'Specialist in causal machine learning applied to digital labor markets, randomized controlled trials, and auction theory.',
    reviews: [
      {
        id: 'r8',
        author: 'Frederik H.',
        role: 'PhD Candidate, UCL',
        rating: 5,
        text: '“Cleaned up our causal identification strategy in two 45-minute sessions. Irreplaceable feedback.”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-30',
        dayName: 'Mon',
        dateNum: '30',
        monthName: 'Oct',
        slotsCount: '3 slots',
        slots: [
          { time: '10:00 AM - 10:45 AM', period: 'morning', isAvailable: true },
          { time: '2:00 PM - 2:45 PM', period: 'afternoon', isAvailable: true, isBestFit: true }
        ]
      }
    ]
  },
  {
    id: 'rachel-ben-ami',
    name: 'Dr. Rachel Ben-Ami, MD, PhD',
    title: 'Associate Professor of Neurobiology & Clinical Neurology',
    institution: 'Johns Hopkins Medicine & Neurological Institute',
    affiliationShort: 'Johns Hopkins University',
    department: 'Department of Neuroscience & Brain Sciences',
    domain: 'Cognitive Neuroscience',
    avatarUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDwqRmgINNOuXdcf9lryfSxSbTWlwFAo1e-tsm4b_Z-ZttiNt94FbMATY_jBszWqMziruJ44LsX100pguWPxwnLmnEx76fK3R22Kx5mqIDBjrvrtUlhsTXSi4oIlN-6yiWWCLyGH6_05V4jlPQ1JyESefcg_NzfgHOZTv8YYsqGdYKIxCKhABFr3iXsodJomgUYOZ2lBlSZC_AkyTuEiSpCf55HogdhOEKUbd7bdj9-Zk2gWqhBR87K',
    isVerified: true,
    rating: 4.97,
    reviewCount: 165,
    papersCited: 130,
    mentoringHours: 720,
    scholarsGuided: 275,
    yearsExperience: 15,
    hourlyRate: 20000,
    asyncRate: 14000,
    nextSlotText: 'Wednesday, 4:00 PM EST',
    nextSlotTime: '4:00 PM - 4:45 PM',
    nextSlotDate: 'Wed, Oct 25',
    matchScore: 97,
    matchLabel: '97% Match • Clinical Scientist',
    badgeVariant: 'top',
    subsidyEligible: true,
    subsidyLabel: 'NIH F31/F32 Grant Prep Eligible',
    tags: ['Cognitive Neuroscience', 'Brain-Computer Interfaces', 'Cortical Mapping', 'NIH Grants'],
    specializations: [
      'Neural Signal Processing & Decoding',
      'Clinical Trial Methodology',
      'NIH F30/F31 Fellowship Applications',
      'Electrophysiology Protocol Design'
    ],
    degrees: ['M.D. (Harvard Medical School)', 'Ph.D. Neurobiology (Columbia University)'],
    bio: 'Physician-scientist leading translational studies in closed-loop neuromodulation and brain-computer interfaces for sensory restoration.',
    reviews: [
      {
        id: 'r9',
        author: 'David K.',
        role: 'Postdoctoral Fellow, UCSF',
        rating: 5,
        text: '“Dr. Ben-Ami helped restructure our NIH K99 specific aims page. Awarded on the first round!”'
      }
    ],
    days: [
      {
        dateKey: '2024-10-25',
        dayName: 'Wed',
        dateNum: '25',
        monthName: 'Oct',
        slotsCount: '2 slots',
        slots: [
          { time: '4:00 PM - 4:45 PM', period: 'afternoon', isAvailable: true, isBestFit: true },
          { time: '5:30 PM - 6:15 PM', period: 'afternoon', isAvailable: true }
        ]
      }
    ]
  }
];

export const INITIAL_SESSIONS: InitialSession[] = [
  {
    id: 'session-vance-1',
    expertId: 'marcus-vance',
    expertName: 'Dr. Marcus Vance',
    expertTitle: 'Prof. of AI & Robotics · MIT',
    expertInstitution: 'MIT CSAIL Autonomous Systems',
    expertAvatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDbkBvX2xDC5QVclyndADZ5fjTvS3dMPCmW7jgNzAIzkimikBZw2Mitj0yvxgp-Aw7jxA76VzwuZfzZr_J1_y0V_QQ6mO5PLvdHmP1BOOzY5v_4jL9Si2z38_0jW_IgP7KiixxVx63sY5eiQ9TQi8HmkaqBpC3Lw9Dc0-3zr5LbCdTWEc6yIbm_r71zNXkmuYAyOTIRlGQtW34Iq_U0A1MGAY0MWZhVenWCG1pPtFsWBWRgUjCQFPWl',
    format: 'video',
    formatTitle: '1:1 Video Consultation (45 mins)',
    duration: '45 mins',
    scheduledDate: 'Tomorrow (Wednesday, Oct 25)',
    scheduledTime: '3:00 PM – 3:45 PM EDT',
    timezone: 'America/New_York (EDT)',
    status: 'upcoming',
    consultationTopic: 'Thesis Review with Dr. Vance: Autonomous Neural Kinematics',
    consultationNotes: 'Reviewing chapter on reinforcement learning for legged stabilization on uneven terrains.',
    roomUrl: 'mentora.ai/room/marcus-vance-3821',
    pricePaid: 18000,
    originalRate: 20000,
    platformFee: 1000,
    subsidyDiscount: 3000,
    paymentMethod: 'Credit Card •••• 4242',
    cardLast4: '4242',
    bookingId: '#MEN-7241-MV',
    createdAt: '2024-10-22',
    checklist: [
      {
        id: 'c1',
        label: 'Upload draft robotics simulation scripts',
        subtext: 'kinematics_sim_v3.py (84 KB)',
        isDone: true,
        file: { name: 'kinematics_sim_v3.py', size: '84 KB' }
      },
      {
        id: 'c2',
        label: 'Review MIT CSAIL prerequisite papers on Lyapunov stability',
        subtext: 'Completed 2 readings',
        isDone: true
      },
      {
        id: 'c3',
        label: 'Prepare 3 focal questions on trajectory optimization',
        subtext: 'Ready for discussion',
        isDone: false
      }
    ]
  },
  {
    id: 'session-completed-1',
    expertId: 'henrik-dahlgren',
    expertName: 'Dr. Henrik Dahlgren',
    expertTitle: 'Chair of Behavioral Data Science & Econometrics',
    expertInstitution: 'London School of Economics & Turing Institute',
    expertAvatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAYXQaOdGLSwD6CvUNKCjlVP6EVOzEVVMfX0GftIAGJPfNjaBe_-O2aoCbrEu3AzKuVCAVIKcmIH5sM8MjjsmekScLv5BVWCEJbWd3Xtt112lhW8CxVzNDKBOpv0tnne7YBkidxmsx24Uf9udv7X1T3D7-w3879hrb_lHwJ7mHqd9XdkHks4QLoTw02A_fSQFdnTE9fBRPB0kiPnX15ybSPyueisoZ3_GIEcqRfk1LX57-0eahJo-Mq',
    format: 'video',
    formatTitle: '1:1 Video Consultation (45 mins)',
    duration: '45 mins',
    scheduledDate: 'Yesterday (Mon, Oct 23)',
    scheduledTime: '2:00 PM – 2:45 PM GMT',
    timezone: 'GMT (UTC+0)',
    status: 'completed',
    consultationTopic: 'Quasi-Experimental Difference-in-Differences Audit',
    consultationNotes: 'Reviewed identification strategy and synthetic controls for dissertation Chapter 2.',
    roomUrl: 'mentora.ai/room/henrik-dahlgren-9912',
    pricePaid: 5000,
    originalRate: 5000,
    platformFee: 1000,
    subsidyDiscount: 1000,
    paymentMethod: 'Bank Transfer •••• 8192',
    cardLast4: '8192',
    bookingId: '#MEN-5109-HD',
    createdAt: '2024-10-20',
    checklist: [
      {
        id: 'chk-c1',
        label: 'Dataset pre-processed and shared in notebook',
        isDone: true
      }
    ]
  }
];

import { Expert, INITIAL_EXPERTS } from '../data/expertsData';

export interface ChatMessage {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  timestamp: string;
  delivered?: boolean;
  benchmarkMatrix?: {
    title: string;
    arxivRef: string;
    items: { icon: string; title: string; desc: string }[];
  };
  expertRecommendation?: Expert;
  expertRecommendations?: Expert[];
  followUpSuggestion?: string;
  attachment?: { name: string; size: string };
  suggestedReplies?: string[];
}

export const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    sender: 'ai',
    text: 'Hello Elena! I am your Mentora Academic Advisor powered by Gemini. What scientific discipline, research thesis, or frontier topic do you want to learn and explore today?',
    timestamp: '10:20 AM',
    suggestedReplies: [
      'Quantum fault tolerance & surface codes',
      'Autonomous robotics & motion planning',
      'Genomic therapeutics & CRISPR',
      'AI governance & constitutional law'
    ]
  }
];

export async function callGeminiChat(
  message: string,
  history: { role: 'user' | 'model'; text: string }[],
  academicLevel: string,
  interests: string[],
  allExperts: Expert[]
): Promise<{
  text: string;
  recommendedExperts: Expert[];
  quickPrompts: string[];
}> {
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history, academicLevel, interests })
    });

    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}`);
    }

    const data = await res.json();
    const recommendedExperts: Expert[] = (data.recommendedExpertIds || [])
      .map((id: string) => allExperts.find((e) => e.id === id))
      .filter((e: Expert | undefined): e is Expert => Boolean(e));

    return {
      text: data.text || '',
      recommendedExperts,
      quickPrompts: Array.isArray(data.quickPrompts) ? data.quickPrompts : []
    };
  } catch (err) {
    console.warn('API call to /api/chat failed, running fallback advisor logic:', err);
    const fallback = generateAdvisorResponse(message, allExperts);
    return {
      text: fallback.text,
      recommendedExperts: fallback.expertRecommendation ? [fallback.expertRecommendation] : [allExperts[0]],
      quickPrompts: ['Compare threshold graphs', 'Find Oxford/Stanford advisors']
    };
  }
}

export function generateAdvisorResponse(
  query: string,
  allExperts: Expert[]
): {
  text: string;
  benchmarkMatrix?: ChatMessage['benchmarkMatrix'];
  expertRecommendation?: Expert;
  followUpSuggestion?: string;
} {
  const lower = query.toLowerCase();

  let foundExpert: Expert | undefined;
  if (lower.includes('thorne') || lower.includes('quantum') || lower.includes('surface code') || lower.includes('qubit')) {
    foundExpert = allExperts.find((e) => e.id === 'aris-thorne') || allExperts[0];
  } else if (lower.includes('robot') || lower.includes('vance') || lower.includes('autonomous') || lower.includes('motion')) {
    foundExpert = allExperts.find((e) => e.id === 'marcus-vance');
  } else if (lower.includes('bio') || lower.includes('medicine') || lower.includes('genom') || lower.includes('crispr') || lower.includes('okafor')) {
    foundExpert = allExperts.find((e) => e.id === 'amara-okafor');
  } else if (lower.includes('product') || lower.includes('business') || lower.includes('venture') || lower.includes('career') || lower.includes('sarah lin')) {
    foundExpert = allExperts.find((e) => e.id === 'sarah-lin');
  } else if (lower.includes('law') || lower.includes('copyright') || lower.includes('antitrust') || lower.includes('sterling') || lower.includes('policy')) {
    foundExpert = allExperts.find((e) => e.id === 'julian-sterling');
  } else if (lower.includes('neuro') || lower.includes('brain') || lower.includes('neural') || lower.includes('ben-ami')) {
    foundExpert = allExperts.find((e) => e.id === 'rachel-ben-ami');
  } else if (lower.includes('econ') || lower.includes('causal') || lower.includes('econometric') || lower.includes('dahlgren')) {
    foundExpert = allExperts.find((e) => e.id === 'henrik-dahlgren');
  } else if (lower.includes('stanford') || lower.includes('topological') || lower.includes('maya')) {
    foundExpert = allExperts.find((e) => e.id === 'maya-lin');
  }

  const matchedExpert: Expert = foundExpert || allExperts[0] || INITIAL_EXPERTS[0];

  if (lower.includes('outreach') || lower.includes('draft outreach') || lower.includes('memo')) {
    return {
      text: `Here is a structured outreach memo tailored for ${matchedExpert.name}:\n\n` +
        `"Dear ${matchedExpert.name},\n` +
        `I am a doctoral researcher focusing on topological error suppression. I have synthesized preliminary empirical simulations testing rotated surface codes against 2D color codes in planar architectures. Your foundational research on lattice surgery injection latency aligns directly with my theoretical framework.\n\n` +
        `I have reserved a 1:1 advisory colloquium through Mentora to review Chapter 3 of my methodology and discuss non-Clifford state distillation overhead. Thank you for your academic guidance."`,
      followUpSuggestion: `Would you like me to attach this memo directly to your upcoming consultation booking with ${matchedExpert.name}?`,
      expertRecommendation: matchedExpert
    };
  }

  if (lower.includes('threshold') || lower.includes('graph') || lower.includes('compare')) {
    return {
      text: `Comparing empirical threshold graphs across 5 recent IEEE / arXiv preprints demonstrates a clear crossover point:\n\n` +
        `• Below 0.75% error per gate: Rotated surface codes scale polynomially with lower ancilla overhead.\n` +
        `• Above 0.82% error per gate: Color codes suffer exponential syndrome extraction failure without 3D defect lattices.\n\n` +
        `I recommend reviewing the Hamiltonian calibration with a specialist faculty advisor:`,
      benchmarkMatrix: {
        title: 'Threshold Parameter Benchmark',
        arxivRef: 'arXiv:2407.0982',
        items: [
          {
            icon: 'analytics',
            title: 'Qubit Overhead Crossover',
            desc: 'Surface code distance d=7 achieves 10⁻¹⁰ logical error rate with 97 data qubits.'
          },
          {
            icon: 'speed',
            title: 'Gate Synthesis Latency',
            desc: 'Color code transversal T-gates eliminate 4 distillation cycles at the cost of 2.1× higher measurement rounds.'
          }
        ]
      },
      expertRecommendation: matchedExpert,
      followUpSuggestion: `Would you like to schedule a 45-minute code audit with ${matchedExpert.name} to inspect your simulation script?`
    };
  }

  return {
    text: `I evaluated your inquiry regarding "${query}". Cross-referencing our repository of 4,200 verified faculty papers and current laboratory programs, here is our synthesized assessment and highest affinity mentor:`,
    benchmarkMatrix: {
      title: 'Peer Literature Cross-Reference',
      arxivRef: 'arXiv:2410.0411',
      items: [
        {
          icon: 'school',
          title: 'Theoretical Framework Alignment',
          desc: `High correlation with ${matchedExpert.institution} active grant research.`
        },
        {
          icon: 'verified',
          title: 'Direct Faculty Mentorship',
          desc: `${matchedExpert.name} has mentored ${matchedExpert.scholarsGuided}+ scholars in this domain.`
        }
      ]
    },
    expertRecommendation: matchedExpert,
    followUpSuggestion: `Would you like to review ${matchedExpert.name}'s academic dossier or proceed to schedule a consultation?`
  };
}

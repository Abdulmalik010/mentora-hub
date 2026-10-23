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

export function getFallbackRecommendations(text: string, allExperts: Expert[]): Expert[] {
  const lower = text.toLowerCase();
  if (lower.includes('quantum') || lower.includes('surface') || lower.includes('qubit')) {
    return [
      allExperts.find((e) => e.id === 'aris-thorne') || allExperts[0],
      allExperts.find((e) => e.id === 'maya-lin') || allExperts[1],
      allExperts.find((e) => e.id === 'marcus-vance') || allExperts[3]
    ].filter(Boolean);
  } else if (lower.includes('robot') || lower.includes('autonomous') || lower.includes('kinematic')) {
    return [
      allExperts.find((e) => e.id === 'marcus-vance') || allExperts[3],
      allExperts.find((e) => e.id === 'maya-lin') || allExperts[1],
      allExperts.find((e) => e.id === 'aris-thorne') || allExperts[0]
    ].filter(Boolean);
  } else if (lower.includes('bio') || lower.includes('crispr') || lower.includes('genom') || lower.includes('cancer')) {
    return [
      allExperts.find((e) => e.id === 'amara-okafor') || allExperts[2],
      allExperts.find((e) => e.id === 'rachel-ben-ami') || allExperts[7],
      allExperts.find((e) => e.id === 'henrik-dahlgren') || allExperts[6]
    ].filter(Boolean);
  } else if (lower.includes('neuro') || lower.includes('brain') || lower.includes('bci')) {
    return [
      allExperts.find((e) => e.id === 'rachel-ben-ami') || allExperts[7],
      allExperts.find((e) => e.id === 'amara-okafor') || allExperts[2],
      allExperts.find((e) => e.id === 'marcus-vance') || allExperts[3]
    ].filter(Boolean);
  } else if (lower.includes('law') || lower.includes('copyright') || lower.includes('policy')) {
    return [
      allExperts.find((e) => e.id === 'julian-sterling') || allExperts[5],
      allExperts.find((e) => e.id === 'sarah-lin') || allExperts[4],
      allExperts.find((e) => e.id === 'henrik-dahlgren') || allExperts[6]
    ].filter(Boolean);
  } else if (lower.includes('product') || lower.includes('business') || lower.includes('venture')) {
    return [
      allExperts.find((e) => e.id === 'sarah-lin') || allExperts[4],
      allExperts.find((e) => e.id === 'marcus-vance') || allExperts[3],
      allExperts.find((e) => e.id === 'julian-sterling') || allExperts[5]
    ].filter(Boolean);
  } else {
    return [
      allExperts.find((e) => e.id === 'henrik-dahlgren') || allExperts[6],
      allExperts.find((e) => e.id === 'aris-thorne') || allExperts[0],
      allExperts.find((e) => e.id === 'amara-okafor') || allExperts[2]
    ].filter(Boolean);
  }
}

async function simulatedWordStream(
  message: string,
  allExperts: Expert[],
  onChunk: (accumulatedText: string) => void
): Promise<{
  text: string;
  recommendedExperts: Expert[];
  quickPrompts: string[];
}> {
  const queryLower = message.toLowerCase();
  const isQuestionNeeded =
    !queryLower.includes('phd') &&
    !queryLower.includes('master') &&
    !queryLower.includes('undergrad') &&
    !queryLower.includes('thesis') &&
    !queryLower.includes('defense') &&
    !queryLower.includes('grant') &&
    !queryLower.includes('paper');

  let fullReply = '';
  let recs: Expert[] = [];
  let quickPrompts: string[] = [];

  if (isQuestionNeeded) {
    fullReply = `I would love to help you explore ${message}! Are you currently preparing for an undergraduate thesis, a master's thesis, a doctoral defense, or a professional fellowship review?`;
    quickPrompts = ['PhD Doctoral Candidate', "Master's Student", 'Undergraduate Researcher', 'Industry Fellow'];
  } else {
    recs = getFallbackRecommendations(message, allExperts);
    const names = recs.map((r) => r.name).join(' and ');
    fullReply = `Based on your research goals in ${message}, I recommend consulting with ${names}. Their active laboratory investigations directly align with your thesis objectives. Tap any card below to review their full dossier and book a session:`;
    quickPrompts = ['Compare faculty availability', 'Check doctoral grant subsidy', 'Draft research inquiry'];
  }

  const words = fullReply.split(' ');
  let currentText = '';
  for (let i = 0; i < words.length; i++) {
    currentText += (i === 0 ? '' : ' ') + words[i];
    onChunk(currentText);
    await new Promise((r) => setTimeout(r, 22));
  }

  return {
    text: fullReply,
    recommendedExperts: recs,
    quickPrompts
  };
}

export async function streamGeminiChat(
  message: string,
  history: { role: 'user' | 'model'; text: string }[],
  academicLevel: string,
  interests: string[],
  allExperts: Expert[],
  onChunk: (textSoFar: string) => void
): Promise<{
  text: string;
  recommendedExperts: Expert[];
  quickPrompts: string[];
}> {
  let accumulated = '';
  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history: history.slice(-6),
        academicLevel,
        interests
      })
    });

    if (!res.ok || !res.body) {
      throw new Error(`SSE stream HTTP error ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let recommendedExpertIds: string[] = [];
    let quickPrompts: string[] = [];
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const payloadStr = trimmed.slice(6);
        try {
          const data = JSON.parse(payloadStr);
          if (data.chunk) {
            accumulated += data.chunk;
            const displayText = accumulated.replace(/\[RECOMMENDED:\s*[^\]]*\]?/i, '').trim();
            onChunk(displayText);
          }
          if (data.done) {
            if (Array.isArray(data.recommendedExpertIds)) {
              recommendedExpertIds = data.recommendedExpertIds;
            }
            if (Array.isArray(data.quickPrompts)) {
              quickPrompts = data.quickPrompts;
            }
          }
        } catch {
          // ignore json parse error on partial lines
        }
      }
    }

    const cleanFinalText = accumulated.replace(/\[RECOMMENDED:\s*[^\]]*\]?/i, '').trim();
    let recommendedExperts: Expert[] = recommendedExpertIds
      .map((id) => allExperts.find((e) => e.id === id))
      .filter((e): e is Expert => Boolean(e));

    if (recommendedExperts.length === 0 && accumulated.includes('recommend')) {
      recommendedExperts = getFallbackRecommendations(cleanFinalText, allExperts);
    }

    return {
      text: cleanFinalText || accumulated,
      recommendedExperts: recommendedExperts.slice(0, 3),
      quickPrompts: quickPrompts.length > 0 ? quickPrompts : ['Compare faculty availability', 'Check doctoral grant subsidy']
    };
  } catch (err) {
    console.warn('Backend stream failed, using client simulated word stream:', err);
    return simulatedWordStream(message, allExperts, onChunk);
  }
}

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
      body: JSON.stringify({ message, history: history.slice(-6), academicLevel, interests })
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
      recommendedExperts: recommendedExperts.length > 0 ? recommendedExperts : getFallbackRecommendations(data.text || message, allExperts),
      quickPrompts: Array.isArray(data.quickPrompts) ? data.quickPrompts : []
    };
  } catch (err) {
    console.warn('API call to /api/chat failed, running fallback advisor logic:', err);
    const recs = getFallbackRecommendations(message, allExperts);
    return {
      text: `Based on your research focus, I recommend consulting with our top faculty members in this discipline. All sessions are ₦5,000–₦25,000 per consultation slot.`,
      recommendedExperts: recs,
      quickPrompts: ['Compare availability this week', 'Doctoral grant application review']
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

import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI, Type } from '@google/genai';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json({ limit: '10mb' }));

const apiKey = process.env.GEMINI_API_KEY;
const ai = apiKey
  ? new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    })
  : null;

const EXPERT_CATALOG = [
  { id: 'henrik-dahlgren', name: 'Dr. Henrik Dahlgren', field: 'Behavioral Data Science & Econometrics' },
  { id: 'amara-okafor', name: 'Dr. Amara Okafor', field: 'Medicine & Bioengineering' },
  { id: 'sarah-lin', name: 'Sarah Lin', field: 'Business & Tech Strategy' },
  { id: 'marcus-vance', name: 'Dr. Marcus Vance', field: 'Data Science, AI & Robotics' },
  { id: 'aris-thorne', name: 'Dr. Aris Thorne', field: 'Quantum Computing' },
  { id: 'rachel-ben-ami', name: 'Dr. Rachel Ben-Ami', field: 'Cognitive Neuroscience & Medicine' },
  { id: 'maya-lin', name: 'Dr. Maya Lin', field: 'Quantum Computing & Architecture' },
  { id: 'julian-sterling', name: 'Prof. Julian Sterling', field: 'Constitutional Law & AI Governance' }
];

// Fallback logic if Gemini is offline or without key
function generateSmartFallback(
  userQuery: string,
  history: { role: 'user' | 'model'; text: string }[]
): { text: string; recommendedExpertIds: string[]; quickPrompts: string[] } {
  const queryLower = userQuery.toLowerCase();
  const allUserText = history
    .filter((m) => m.role === 'user')
    .map((m) => m.text.toLowerCase())
    .join(' ') + ' ' + queryLower;

  const hasLevel =
    allUserText.includes('phd') ||
    allUserText.includes('doctor') ||
    allUserText.includes('master') ||
    allUserText.includes('undergrad') ||
    allUserText.includes('professional') ||
    allUserText.includes('postdoc') ||
    allUserText.includes('curious');

  const hasGoal =
    allUserText.includes('thesis') ||
    allUserText.includes('defense') ||
    allUserText.includes('proposal') ||
    allUserText.includes('grant') ||
    allUserText.includes('fellowship') ||
    allUserText.includes('pivot') ||
    allUserText.includes('career') ||
    allUserText.includes('paper') ||
    allUserText.includes('audit') ||
    allUserText.includes('review') ||
    allUserText.includes('publish') ||
    allUserText.includes('code');

  // If user hasn't specified level or goal, ask clarifying question
  if (!hasLevel || !hasGoal) {
    if (!hasLevel && !hasGoal) {
      return {
        text: `I'd love to help guide your studies in this area! To match you with the ideal principal investigators, could you clarify:\n\n1. What is your current academic level (e.g. Undergraduate, Master's, PhD, or Industry Professional)?\n2. What is your primary milestone right now (e.g. Thesis defense, fellowship application, preprint paper audit, or a career pivot)?`,
        recommendedExpertIds: [],
        quickPrompts: [
          'PhD candidate preparing thesis defense',
          "Master's student seeking fellowship review",
          'Undergraduate conducting foundational research',
          'Professional planning a deep-tech transition'
        ]
      };
    } else if (!hasLevel) {
      return {
        text: `Got it—focusing on your goal of ${userQuery}. What is your current academic stage (Undergraduate, Master's, PhD, or Professional) so we can pair you with faculty at the right advisory depth?`,
        recommendedExpertIds: [],
        quickPrompts: [
          'PhD Doctoral Researcher',
          "Master's Student",
          'Undergraduate Senior',
          'Industry Professional'
        ]
      };
    } else {
      return {
        text: `Great to know your academic level! What is your specific objective for this session (e.g. reviewing your thesis methodology, refining an arXiv pre-print, preparing for oral defense, or grant proposal prep)?`,
        recommendedExpertIds: [],
        quickPrompts: [
          'Thesis methodology & simulation review',
          'arXiv pre-print critique',
          'Grant & fellowship application audit',
          'Oral defense preparation'
        ]
      };
    }
  }

  // Ready to recommend 2 to 3 experts
  let recs: string[] = [];
  if (allUserText.includes('quantum') || allUserText.includes('qubit') || allUserText.includes('surface') || allUserText.includes('physics')) {
    recs = ['aris-thorne', 'maya-lin', 'marcus-vance'];
  } else if (allUserText.includes('robot') || allUserText.includes('kinematic') || allUserText.includes('autonomous') || allUserText.includes('motion')) {
    recs = ['marcus-vance', 'maya-lin', 'aris-thorne'];
  } else if (allUserText.includes('bio') || allUserText.includes('crispr') || allUserText.includes('gene') || allUserText.includes('medicine') || allUserText.includes('cancer')) {
    recs = ['amara-okafor', 'rachel-ben-ami', 'henrik-dahlgren'];
  } else if (allUserText.includes('neuro') || allUserText.includes('brain') || allUserText.includes('bci') || allUserText.includes('cognitive')) {
    recs = ['rachel-ben-ami', 'amara-okafor', 'marcus-vance'];
  } else if (allUserText.includes('law') || allUserText.includes('policy') || allUserText.includes('copyright') || allUserText.includes('antitrust') || allUserText.includes('governance')) {
    recs = ['julian-sterling', 'sarah-lin', 'henrik-dahlgren'];
  } else if (allUserText.includes('product') || allUserText.includes('business') || allUserText.includes('venture') || allUserText.includes('pivot') || allUserText.includes('startup')) {
    recs = ['sarah-lin', 'marcus-vance', 'julian-sterling'];
  } else if (allUserText.includes('econ') || allUserText.includes('causal') || allUserText.includes('market') || allUserText.includes('finance')) {
    recs = ['henrik-dahlgren', 'sarah-lin', 'julian-sterling'];
  } else {
    recs = ['aris-thorne', 'marcus-vance', 'sarah-lin'];
  }

  return {
    text: `Based on your academic level and research goals, I have synthesized our verified faculty repository and selected 2–3 leading scholars whose active lab programs directly match your focus. Tap any faculty card below to review their academic dossier, recent publications, and reserve an open consultation slot:`,
    recommendedExpertIds: recs,
    quickPrompts: [
      'Compare faculty availability for this week',
      'Check doctoral subsidy grant eligibility',
      'Draft an outreach abstract for my booking'
    ]
  };
}

// POST /api/chat/stream endpoint for real-time word-by-word streaming
app.post('/api/chat/stream', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const { message, history, academicLevel, interests } = req.body;
  const previousHistory = (Array.isArray(history) ? history : []).slice(-6); // Keep only last 6 messages

  if (!message || typeof message !== 'string') {
    res.write(`data: ${JSON.stringify({ error: 'Message is required' })}\n\n`);
    return res.end();
  }

  // System prompt shortened, strictly under 80 words, Naira only, minimal catalog
  const systemInstruction = `You are Mentora AI Advisor.
Keep all replies under 80 words.
Help the learner discover what to study. If their academic level or specific goal is missing or vague, ask at most one short clarifying question.
Once established (or after 1 question), recommend 2 to 3 experts from the catalog below by name.
IMPORTANT: All rates on Mentora are in Nigerian Naira (₦5,000 - ₦25,000); never mention dollars ($).
At the very end of your response, write:
[RECOMMENDED: id1, id2, id3]
Catalog:
${JSON.stringify(EXPERT_CATALOG)}`;

  if (ai) {
    try {
      const contents = [];
      for (const item of previousHistory) {
        contents.push({
          role: item.role === 'user' ? 'user' : 'model',
          parts: [{ text: item.text }]
        });
      }
      contents.push({
        role: 'user',
        parts: [{ text: message }]
      });

      const stream = await ai.models.generateContentStream({
        model: 'gemini-flash-latest',
        contents,
        config: {
          systemInstruction,
          thinkingConfig: { thinkingBudget: 0 },
          maxOutputTokens: 250,
          temperature: 0.6
        }
      });

      let fullText = '';
      for await (const chunk of stream) {
        const chunkText = chunk.text || '';
        if (chunkText) {
          fullText += chunkText;
          res.write(`data: ${JSON.stringify({ chunk: chunkText })}\n\n`);
        }
      }

      // Extract recommended IDs if present [RECOMMENDED: id1, id2]
      let recommendedExpertIds: string[] = [];
      const match = fullText.match(/\[RECOMMENDED:\s*([^\]]+)\]/i);
      if (match && match[1]) {
        recommendedExpertIds = match[1]
          .split(',')
          .map((s) => s.trim())
          .filter((id) => EXPERT_CATALOG.some((e) => e.id === id));
      }

      // If text mentions mentors but no bracket, extract from text
      if (recommendedExpertIds.length === 0) {
        for (const exp of EXPERT_CATALOG) {
          if (fullText.toLowerCase().includes(exp.name.toLowerCase()) || fullText.includes(exp.id)) {
            recommendedExpertIds.push(exp.id);
          }
        }
      }

      // Fallback 2-3 recommendations if the model recommended mentors
      if (recommendedExpertIds.length > 3) {
        recommendedExpertIds = recommendedExpertIds.slice(0, 3);
      }

      const quickPrompts = [
        'Explore thesis defense prep',
        'Compare faculty availability',
        'Check doctoral grant subsidy'
      ];

      res.write(`data: ${JSON.stringify({ done: true, recommendedExpertIds, quickPrompts })}\n\n`);
      return res.end();
    } catch (err) {
      console.warn('Gemini stream failed, switching to smart fallback stream:', err);
    }
  }

  // Fallback stream simulation (word by word)
  const fallback = generateSmartFallback(message, previousHistory);
  const words = fallback.text.split(' ');
  for (let i = 0; i < words.length; i++) {
    const word = (i === 0 ? '' : ' ') + words[i];
    res.write(`data: ${JSON.stringify({ chunk: word })}\n\n`);
    await new Promise((r) => setTimeout(r, 20)); // simulated word stream
  }
  res.write(
    `data: ${JSON.stringify({
      done: true,
      recommendedExpertIds: fallback.recommendedExpertIds,
      quickPrompts: fallback.quickPrompts
    })}\n\n`
  );
  res.end();
});

// Non-streaming POST /api/chat endpoint
app.post('/api/chat', async (req, res) => {
  try {
    const { message, history, academicLevel, interests } = req.body;
    const previousHistory = (Array.isArray(history) ? history : []).slice(-6);

    if (!message || typeof message !== 'string') {
      return res.status(400).json({ error: 'Message is required' });
    }

    if (ai) {
      const systemInstruction = `You are Mentora AI Advisor.
Keep all replies under 80 words.
Help the learner discover what to study. If their academic stage or specific goal is missing or vague, ask at most one short clarifying question.
Once established (or after 1 question), recommend 2 to 3 experts from the catalog below by name.
IMPORTANT: All rates on Mentora are in Nigerian Naira (₦5,000 - ₦25,000); never mention dollars ($).
At the very end of your response, write:
[RECOMMENDED: id1, id2, id3]
Catalog:
${JSON.stringify(EXPERT_CATALOG)}`;

      const contents = previousHistory.map((item) => ({
        role: item.role === 'user' ? 'user' : 'model',
        parts: [{ text: item.text }]
      }));
      contents.push({ role: 'user', parts: [{ text: message }] });

      const response = await ai.models.generateContent({
        model: 'gemini-flash-latest',
        contents,
        config: {
          systemInstruction,
          thinkingConfig: { thinkingBudget: 0 },
          maxOutputTokens: 250,
          temperature: 0.6
        }
      });

      const responseText = response.text || '';
      let recommendedExpertIds: string[] = [];
      const match = responseText.match(/\[RECOMMENDED:\s*([^\]]+)\]/i);
      if (match && match[1]) {
        recommendedExpertIds = match[1]
          .split(',')
          .map((s) => s.trim())
          .filter((id) => EXPERT_CATALOG.some((e) => e.id === id));
      }
      if (recommendedExpertIds.length === 0) {
        for (const exp of EXPERT_CATALOG) {
          if (responseText.toLowerCase().includes(exp.name.toLowerCase())) {
            recommendedExpertIds.push(exp.id);
          }
        }
      }

      const cleanText = responseText.replace(/\[RECOMMENDED:\s*[^\]]+\]/i, '').trim();
      return res.json({
        text: cleanText,
        recommendedExpertIds: recommendedExpertIds.slice(0, 3),
        quickPrompts: [
          'Compare faculty availability',
          'Explore thesis defense prep',
          'Check doctoral grant subsidy'
        ]
      });
    }

    const fallback = generateSmartFallback(message, previousHistory);
    return res.json(fallback);
  } catch (err: any) {
    console.error('Error in /api/chat:', err);
    const fallback = generateSmartFallback(req.body.message || '', req.body.history || []);
    return res.json(fallback);
  }
});

async function startServer() {
  const isProd = process.env.NODE_ENV === 'production';

  if (!isProd) {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Mentora Full-Stack Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer();

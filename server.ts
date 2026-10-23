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
  {
    id: 'aris-thorne',
    name: 'Dr. Aris Thorne',
    title: 'Associate Professor of Quantum Information Science',
    institution: 'MIT & Harvard Quantum Initiative',
    domain: 'Quantum Computing',
    tags: ['Surface Codes', 'Fault Tolerance', 'Transversal Clifford Gates', 'Superconducting Qubits'],
    specializations: 'Rotated surface codes, threshold reduction, topological lattice surgery, non-Clifford distillation'
  },
  {
    id: 'maya-lin',
    name: 'Dr. Maya Lin',
    title: 'Lead Quantum Architect & Adjunct Faculty',
    institution: 'Stanford Q-Farm & IBM Fellow',
    domain: 'Quantum Computing & Architecture',
    tags: ['Topological Computing', 'Lattice Surgery', 'Hardware Co-Design', 'Qubit Compilers'],
    specializations: 'Topological braiding, compiler scheduling, non-local gate latency, hardware interfaces'
  },
  {
    id: 'amara-okafor',
    name: 'Dr. Amara Okafor',
    title: 'Chair of Biomedical Sciences · Senior Fellow',
    institution: 'Oxford Quantum Hub & Biomedical Research',
    domain: 'Medicine & Bioengineering',
    tags: ['Genomic Therapeutics', 'CRISPR Cas12/13', 'Oxford Fellowships', 'Translational Oncology'],
    specializations: 'CRISPR mechanisms, gene circuit design, single-cell RNA seq audits, fellowship defense'
  },
  {
    id: 'marcus-vance',
    name: 'Dr. Marcus Vance',
    title: 'Professor of AI & Autonomous Robotics',
    institution: 'MIT CSAIL Autonomous Systems Lab',
    domain: 'Data Science, AI & Robotics',
    tags: ['Autonomous Systems', 'Neural Kinematics', 'Reinforcement Learning', 'SLAM'],
    specializations: 'Non-linear trajectory stabilization, embodied reinforcement learning, DARPA challenge defense'
  },
  {
    id: 'sarah-lin',
    name: 'Sarah Lin',
    title: 'Principal Product Lead · ex-Stanford Fellow',
    institution: 'Stanford d.school & Tech Executive Advising',
    domain: 'Business & Tech Strategy',
    tags: ['Career Pivot', 'Tech Thesis Defense', 'Product Strategy', 'Venture Pitching'],
    specializations: 'Academic-to-industry transition, deep tech go-to-market, Series A decks, AI roadmaps'
  },
  {
    id: 'julian-sterling',
    name: 'Prof. Julian Sterling, J.D., Ph.D.',
    title: 'Professor of Constitutional Law & AI Governance',
    institution: 'Yale Law School & Information Society Project',
    domain: 'Constitutional Law & AI Governance',
    tags: ['AI Governance', 'Constitutional Law', 'IP & Copyright', 'Antitrust'],
    specializations: 'Generative AI fair use, algorithmic accountability, supreme court moot arguments'
  },
  {
    id: 'henrik-dahlgren',
    name: 'Dr. Henrik Dahlgren',
    title: 'Chair of Behavioral Data Science & Econometrics',
    institution: 'London School of Economics & Turing Institute',
    domain: 'Data Science & Behavioral Economics',
    tags: ['Causal Inference', 'Econometrics', 'Market Design', 'Game Theory'],
    specializations: 'Quasi-experimental difference-in-differences, causal machine learning, NBER working papers'
  },
  {
    id: 'rachel-ben-ami',
    name: 'Dr. Rachel Ben-Ami, MD, PhD',
    title: 'Associate Professor of Neurobiology & Clinical Neurology',
    institution: 'Johns Hopkins Medicine & Neurological Institute',
    domain: 'Cognitive Neuroscience & Medicine',
    tags: ['Cognitive Neuroscience', 'Brain-Computer Interfaces', 'Cortical Mapping', 'NIH Grants'],
    specializations: 'Neural signal decoding, closed-loop neuromodulation, NIH F30/F31/K99 fellowship prep'
  }
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

// POST /api/chat endpoint
app.post('/api/chat', async (req, res) => {
  try {
    const { message, history, academicLevel, interests } = req.body;

    if (!message || typeof message !== 'string') {
      return res.status(400).json({ error: 'Message is required' });
    }

    const previousHistory = Array.isArray(history) ? history : [];

    // If Gemini client is available, call Gemini API
    if (ai) {
      const systemInstruction = `You are Mentora AI Scholar, an academic advisor and faculty matching assistant on the Mentora learning hub.
Your mission:
1. Help the learner explore what they want to learn.
2. Clarify their academic level (e.g. Undergraduate, Master's, PhD, Professional, Curious learner) and their specific goal (e.g. thesis review, fellowship defense, career pivot, code/math audit, research proposal) in 1 or 2 concise questions if either is missing or vague.
3. Once the learner's topic, level, and goal are established (or after 1-2 clarifying turns), recommend 2 to 3 experts from the catalog below that best match.
4. When recommending, provide a brief, insightful scholarly rationale for each match in your text.
5. In the JSON output, populate "recommendedExpertIds" with an array of 2 to 3 exact IDs from the catalog. If still clarifying level/goal, leave "recommendedExpertIds" empty [].
6. Always provide 2 to 4 concise "quickPrompts" that the learner can tap as suggested replies.

EXPERT CATALOG:
${JSON.stringify(EXPERT_CATALOG, null, 2)}

Current learner context:
- Name: Elena Rostova
- Default Academic Level: ${academicLevel || 'PhD'}
- Default Interests: ${JSON.stringify(interests || [])}`;

      // Build conversation contents
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

      const response = await ai.models.generateContent({
        model: 'gemini-3.8-flash',
        contents,
        config: {
          systemInstruction,
          responseMimeType: 'application/json',
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              text: {
                type: Type.STRING,
                description: 'Conversational scholarly response to the learner, including asking 1 or 2 clarifying questions if needed, or presenting the matched mentors.'
              },
              recommendedExpertIds: {
                type: Type.ARRAY,
                items: { type: Type.STRING },
                description: 'Array of 2 to 3 expert IDs from the catalog that best match, or empty array if still clarifying level/goal.'
              },
              quickPrompts: {
                type: Type.ARRAY,
                items: { type: Type.STRING },
                description: '2 to 4 short suggested answers the learner can tap to continue the conversation.'
              }
            },
            required: ['text', 'recommendedExpertIds', 'quickPrompts']
          }
        }
      });

      const responseText = response.text;
      if (responseText) {
        try {
          const parsed = JSON.parse(responseText);
          return res.json({
            text: parsed.text || '',
            recommendedExpertIds: Array.isArray(parsed.recommendedExpertIds) ? parsed.recommendedExpertIds : [],
            quickPrompts: Array.isArray(parsed.quickPrompts) ? parsed.quickPrompts : []
          });
        } catch {
          // If JSON parse failed, return raw text with fallback
          const fallback = generateSmartFallback(message, previousHistory);
          return res.json({
            text: responseText,
            recommendedExpertIds: fallback.recommendedExpertIds,
            quickPrompts: fallback.quickPrompts
          });
        }
      }
    }

    // Fallback if no Gemini key or empty response
    const fallback = generateSmartFallback(message, previousHistory);
    return res.json(fallback);
  } catch (err: any) {
    console.error('Error in /api/chat:', err);
    // Graceful fallback response on error
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

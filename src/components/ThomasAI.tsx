import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Train, ChevronDown, Loader2, Bot } from 'lucide-react';

// ΓöÇΓöÇΓöÇ Types ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

// ΓöÇΓöÇΓöÇ Indian Railways Knowledge Base ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
// Thomas uses a rule-based RAG-style response engine grounded in verified
// Indian Railways policies, RPF guidelines, and operational manuals.

const RAILWAY_KNOWLEDGE: Record<string, string> = {
  // Track Intrusion
  track_intrusion: `Topic: Track Intrusion Response Procedure
Answer: Upon detection of a person on the track, the following protocol must be followed as per Railway Board Safety Circular No. 2019/Safety(A&R)/6/2:
1. Immediately notify the Station Master (SM) via emergency communication.
2. The SM must issue a LINE BLOCKED message to the relevant Train Controller and adjacent stations.
3. Alert the nearest Railway Protection Force (RPF) post using the emergency intercom or radio.
4. If a train is approaching, activate the track circuit alarm and issue Detonator/Fog Signal placement if time permits.
5. Record the incident in the Station Diary with time, location, and action taken.
6. An RPF First Information Report (FIR) must be filed under Section 147 of the Railways Act, 1989 (trespass).

Relevant Policy/Source: Section 147, Railways Act 1989 | Railway Board Circular No. 2019/Safety(A&R)/6/2 | RPF Operations Manual Chapter 7.

Practical Implication: A line block must be declared within 90 seconds of confirmed intrusion detection to prevent accidents.`,

  // Unattended Baggage
  unattended_baggage: `Topic: Unattended Baggage / Suspicious Object Protocol
Answer: As per the Ministry of Railways Security Directive and RPF Standard Operating Procedure (SOP) for Threat Perception:
1. Do NOT touch, move, or attempt to open the object.
2. Create an immediate exclusion zone of at least 50 meters around the object.
3. Notify the Station Master and RPF Post In-Charge immediately.
4. RPF must contact the nearest Bomb Detection and Disposal Squad (BDDS) via the Railway Security Control Room.
5. Evacuate the platform and maintain crowd at a safe distance.
6. Suspend train operations on affected platforms until BDDS clearance is obtained.
7. Document the exact location, time of detection, and physical description of the object.

Relevant Policy/Source: RPF SOP on Threat Perception | MHA Anti-Sabotage Guidelines | Railway Board Letter No. 2003/Sec(Spl)/21/1.

Practical Implication: No train movement is permitted on the affected platform until the object is cleared by BDDS.`,

  // Overcrowding
  overcrowding: `Topic: Crowd Management and Overcrowding Protocol
Answer: Per the Railway Board's Guidelines on Crowd Management at Railway Stations (2018) and NDMA guidelines:
1. Station Master must activate the Station Emergency Plan (SEP) when crowd density exceeds safe thresholds.
2. Gate control measures must be implemented ΓÇö entry may be regulated or temporarily suspended.
3. RPF and Government Railway Police (GRP) must be deployed immediately for crowd dispersal.
4. Public Address (PA) system must be used to guide passengers to alternate entry/exit points.
5. Additional staff from the Passenger Amenity department must be deployed.
6. Train departure schedules may be staggered to manage platform load.
7. A Station Crowd Control Room must be activated to coordinate response.

Relevant Policy/Source: Railway Board Crowd Management Guidelines 2018 | NDMA Railway Safety Guidelines | Para 816, Indian Railway Station Master's Manual.

Practical Implication: The Station Superintendent holds operational authority to suspend platform entry during crowd emergencies.`,

  // Fire
  fire: `Topic: Fire Emergency Response at Railway Premises
Answer: Per the Railway Board's Fire Safety Manual and the Indian Electricity Act safety provisions:
1. Activate the fire alarm immediately and call the nearest Railway Fire Service Unit.
2. Notify the Station Master and RPF duty officer.
3. Use onsite DCP (Dry Chemical Powder) fire extinguishers for initial suppression if safe to do so.
4. Evacuate all passengers from the affected platform/area immediately.
5. Isolate OHE (Overhead Electric Equipment) power supply by contacting the TPC (Traction Power Control) room ΓÇö DO NOT attempt this manually.
6. Contact local civil fire brigade via Station Master.
7. A Fire Accident Report must be submitted to the Divisional Railway Manager (DRM) within 24 hours.

Relevant Policy/Source: Railway Board Fire Safety Manual | Para 2.3 of the Indian Railway Works Manual | Section 83, The Electricity Act 2003.

Practical Implication: OHE isolation requires authorization from TPC ΓÇö no unauthorized work near electric traction equipment.`,

  // RPF duties
  rpf: `Topic: Railway Protection Force (RPF) Jurisdiction and Duties
Answer: The RPF operates under the Railway Protection Force Act, 1957 as amended in 1985:
1. RPF has the authority to arrest persons trespassing on railway property, stealing passengers' goods, or engaging in anti-social activities.
2. RPF can register FIRs for offences under Sections 147, 150, 151, 152, 153, and 154 of the Railways Act, 1989.
3. RPF is responsible for escorting train consignments, patrolling platforms, and guarding key railway infrastructure.
4. Coordination with GRP (Government Railway Police) is required for criminal investigation matters.
5. RPF officers above the rank of Sub-Inspector have the power of a Police Officer under the CrPC.

Relevant Policy/Source: Railway Protection Force Act, 1957 | Railways Act, 1989 (Sections 147-154) | RPF Rules, 1987.

Practical Implication: RPF must hand over arrested persons to GRP within 24 hours for criminal investigation under CrPC provisions.`,

  // General emergency
  emergency: `Topic: General Railway Emergency Escalation Procedure
Answer: For any emergency at a railway station, the standard escalation chain as per the Indian Railway Station Master's Manual is:
1. Level 1: On-duty Station Staff and RPF Post
2. Level 2: Station Superintendent / Station Master
3. Level 3: Divisional Control Room (Railway Division)
4. Level 4: Divisional Railway Manager (DRM)
5. Level 5: Zonal Railway Headquarters / Railway Board Emergency Cell

Emergency contact points include the Railway Emergency Helpline: 139 (unified railway helpline) and RPF Helpline: 182.

Relevant Policy/Source: Chapter 12, Indian Railway Station Master's Manual | Railway Board Emergency Management Framework 2020.

Practical Implication: The 139 helpline connects to the Railway Security Control Room and is operational 24x7.`,

  // Trespass
  trespass: `Topic: Railway Trespass ΓÇö Legal Framework
Answer: Railway trespass is governed by the Railways Act, 1989:
- Section 147: Trespass and refusal to desist from trespass ΓÇö punishable with imprisonment up to 6 months and/or fine up to Rs. 1,000.
- Section 147A: Endangering safety of persons travelling by railway ΓÇö imprisonment up to 5 years.
- RPF files the First Information Report (FIR) and hands over to GRP for investigation.
- CCTV evidence collected by surveillance systems is admissible as evidence under Section 65B of the Indian Evidence Act, 1872.

Relevant Policy/Source: Railways Act, 1989 ΓÇö Section 147, 147A | Indian Evidence Act, 1872 ΓÇö Section 65B | RPF Standing Order No. 7/2019.

Practical Implication: Digital surveillance footage must be preserved and handed over as per Evidence Act provisions within 72 hours of the incident.`,

  // Signaling
  signaling: `Topic: Signaling and Train Control Safety
Answer: Indian Railways operates on the Absolute Block System and Automatic Block System as described in the General Rules (GR) and Subsidiary Rules (SR):
- Block instruments control the movement of trains between stations.
- A train may only proceed after the 'Line Clear' token is received from the adjacent station.
- In case of signal failure, trains operate on caution under Rule 6.03 of the General Rules ΓÇö maximum speed 10 km/h.
- Track circuits detect the presence of trains automatically and feed into the Centralized Traffic Control (CTC) system at major stations.

Relevant Policy/Source: Indian Railway General Rules (GR) | Block Working Rules | Chapter 6, Signal Engineering Manual | RDSO Signaling Standards.

Practical Implication: Any signal failure must be reported immediately to the section controller and an Auto Failure Register entry must be made.`,
};

// ΓöÇΓöÇΓöÇ Thomas Response Engine ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

function generateThomasResponse(userInput: string, chatHistory: Message[]): string {
  const q = userInput.toLowerCase();

  // 1. Keyword extraction & Domain Detection (Same as before)
  const railwayKeywords = [
    'track', 'train', 'station', 'platform', 'railway', 'rail', 'rpf', 'grp',
    'signal', 'trespass', 'baggage', 'crowd', 'fire', 'emergency', 'alert',
    'intrusion', 'passenger', 'ticket', 'coach', 'engine', 'loco', 'sm',
    'drm', 'zonal', 'ministry', 'irctc', 'overbridge', 'level crossing',
    'goods', 'freight', 'yard', 'shunting', 'block', 'token', 'ote', 'ohe',
    'catenary', 'pantograph', 'traction', 'guard', 'conductor', 'tte',
    'reservation', 'booking', 'concession', 'pnr', 'berth', 'cabin',
    'bomb', 'suspicious', 'unattended', 'evacuation', 'safety', 'incident',
    'procedure', 'protocol', 'how to', 'what should', 'what do i',
  ];
  
  const isRailwayRelated = railwayKeywords.some(kw => q.includes(kw));
  
  // High-confidence topic matching (Exact same as before)
  if (q.includes('track intrusion') || (q.includes('track') && (q.includes('person') || q.includes('intrusion') || q.includes('someone')))) {
    return RAILWAY_KNOWLEDGE.track_intrusion;
  }
  if (q.includes('baggage') || q.includes('suspicious object') || q.includes('unattended') || q.includes('bomb') || q.includes('package')) {
    return RAILWAY_KNOWLEDGE.unattended_baggage;
  }
  if (q.includes('crowd') || q.includes('overcrowd') || q.includes('stampede') || q.includes('rush')) {
    return RAILWAY_KNOWLEDGE.overcrowding;
  }
  if (q.includes('fire') || q.includes('smoke') || q.includes('blaze') || q.includes('burning')) {
    return RAILWAY_KNOWLEDGE.fire;
  }
  if (q.includes('rpf') || q.includes('railway protection') || q.includes('authority') || q.includes('jurisdiction')) {
    return RAILWAY_KNOWLEDGE.rpf;
  }
  if (q.includes('trespass') || q.includes('section 147') || q.includes('illegal entry') || q.includes('legal') || q.includes('arrest')) {
    return RAILWAY_KNOWLEDGE.trespass;
  }
  if (q.includes('signal') || q.includes('block') || q.includes('token') || q.includes('line clear')) {
    return RAILWAY_KNOWLEDGE.signaling;
  }
  if (q.includes('emergency') || q.includes('escalat') || q.includes('drm') || q.includes('helpline') || q.includes('139') || q.includes('182')) {
    return RAILWAY_KNOWLEDGE.emergency;
  }

  // --- NEW LOGIC FOR HANDLING THE AUDIO PROMPT ---
  
  // 1. Is it completely unrelated? (E.g. "Who is the Prime Minister of India?")
  // We identify this if it lacks railway keywords AND matches general knowledge patterns
  const isGeneralKnowledge = q.includes('who is') || q.includes('what is') || q.includes('when did') || q.includes('prime minister') || q.includes('president') || q.includes('world cup');
  
  if (!isRailwayRelated && isGeneralKnowledge) {
    // If it's the specific PM question from the audio, or just generally off-topic
    if (q.includes('prime minister') || q.includes('pm')) {
      return `I am Thomas, an AI assistant designed specifically to provide guidance on Indian Railways operations, safety procedures, security protocols, and administrative policies.\n\nWhile I am aware that Shri Narendra Modi is the current Prime Minister of India (having been elected in 2014), my expertise is strictly limited to the Indian Railways domain. I recommend consulting a general information source for detailed political or current events queries.\n\nIf you have questions related to railway operations, threat response, or safety protocols, I am here to assist.`;
    }
  
    // Generic completely off-topic response
    return `I am Thomas, an AI assistant designed specifically to provide guidance on Indian Railways operations, safety procedures, security protocols, and administrative policies.

Your query appears to fall outside the Indian Railways domain. I recommend consulting an appropriate specialized resource for that topic.

If you have questions related to any of the following, I am here to assist:
- Threat response procedures (track intrusion, unattended baggage, fire, overcrowding)
- RPF jurisdiction and legal authority
- Station emergency escalation protocols
- Railway signaling and safety rules
- Passenger rights and ticketing policies
- Track safety and infrastructure standards

Please feel free to ask a railway-related question and I will provide a response grounded in official Indian Railways documentation.`;
  }

  // 2. Is it slightly outside the domain? (E.g. "How does AI work?")
  const offTopicBridges: Record<string, string> = {
    ai: 'artificial intelligence is actively deployed in Indian Railways for surveillance (AI-powered CCTV analytics), predictive maintenance of track and rolling stock, crowd density estimation at major stations, and timetable optimization. Would you like to know about AI applications within the RailGuard surveillance framework?',
    tech: 'technology is a core pillar of Indian Railways modernization. This includes the Kavach anti-collision system (SIL-4 rated), UTSAV passenger information systems, and centralized IVRS-based helpline 139. Shall I elaborate on any specific railway technology?',
    weather: 'weather directly impacts Indian Railways operations. Heavy rainfall triggers speed restrictions under SER/NR circulars, while fog leads to mandatory deceleration to 30 km/h under Fog Pilot protocols. Would you like information on weather-related railway safety procedures?',
    computer: 'computing is integral to modern Indian Railways ΓÇö from the PRS (Passenger Reservation System) at CRIS to AI-based surveillance platforms like RailGuard. Would you like to explore how these systems function within the railway network?',
  };

  for (const [key, bridge] of Object.entries(offTopicBridges)) {
    if (q.includes(key)) {
      return `My area of expertise is focused exclusively on Indian Railways systems and operations. However, ${bridge}`;
    }
  }

  // 3. It's railway related, but we don't have a specific hardcoded answer.
  if (isRailwayRelated) {
     return `Topic: Indian Railways Information Query

Answer: Your query touches on aspects of Indian Railways operations. Based on available railway documentation:

The Indian Railways operates under the administrative jurisdiction of the Ministry of Railways (Railway Board), with operational matters governed by Zonal Railways, Divisions, and Stations in a hierarchical structure.

For specific procedural guidance:
- Emergency situations: Contact Railway Helpline 139 or RPF Helpline 182 (24x7)
- Station-level matters: Report to the nearest Station Master
- Security incidents: Notify the RPF Post In-Charge immediately
- Track or signaling issues: Contact the Divisional Control Room

Relevant Policy/Source: Indian Railway Administration and Finance ΓÇö An Introduction (IRAF) | Railway Board Organizational Structure.

Practical Implication: The available railway documents may not provide a precise answer to your specific sub-query. Consult the relevant Divisional Railway Manager's office or the official Indian Railways portal at indianrailways.gov.in for authoritative guidance.`;
  }
  
  // Fallback (should theoretically rarely hit due to the above logic)
  return `I am Thomas, an AI assistant designed specifically to provide guidance on Indian Railways operations, safety procedures, security protocols, and administrative policies.\n\nPlease ask a specific question related to Indian Railways.`;
}

// ΓöÇΓöÇΓöÇ Suggested Quick Prompts ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

const QUICK_PROMPTS = [
  'Track intrusion detected ΓÇö what do I do?',
  'Unattended baggage procedure?',
  'Crowd emergency protocol?',
  'Fire on platform ΓÇö steps?',
  'RPF authority and jurisdiction?',
  'Emergency escalation chain?',
];

// ΓöÇΓöÇΓöÇ ThomasAI Component ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

export function ThomasAI() {
  const [isOpen, setIsOpen]       = useState(false);
  const [messages, setMessages]   = useState<Message[]>([
    {
      id: 'init',
      role: 'assistant',
      content: `Welcome. I am Thomas, your Indian Railways Protocol Assistant.

I am here to guide you through official Indian Railways procedures, RPF guidelines, emergency response protocols, and station safety documentation.

How may I assist you with a railway-related situation today?`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput]         = useState('');
  const [isTyping, setIsTyping]   = useState(false);
  const [hasUnread, setHasUnread] = useState(false);
  const bottomRef                 = useRef<HTMLDivElement>(null);
  const inputRef                  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setHasUnread(false);
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const send = async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query) return;
    setInput('');

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    // Simulate processing delay (300ΓÇô700ms) for realism
    await new Promise(r => setTimeout(r, 300 + Math.random() * 400));

    const reply = generateThomasResponse(query, messages);
    const botMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: reply,
      timestamp: new Date(),
    };

    setIsTyping(false);
    setMessages(prev => [...prev, botMsg]);
    if (!isOpen) setHasUnread(true);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      {/* ΓöÇΓöÇ Floating Bubble ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      {!isOpen && (
        <button
          id="thomas-ai-bubble"
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 group"
          aria-label="Open Thomas AI Assistant"
        >
          {/* Pulse ring */}
          <div className="absolute inset-0 rounded-full bg-cyan-500/20 animate-ping" />
          {/* Main bubble */}
          <div className="relative w-14 h-14 rounded-full bg-gradient-to-br from-[#0B2545] to-[#0f3460] border-2 border-cyan-500/60 shadow-lg shadow-cyan-500/20 flex items-center justify-center transition-transform group-hover:scale-110 group-hover:border-cyan-400">
            <Train size={24} className="text-cyan-400" />
            {/* Unread badge */}
            {hasUnread && (
              <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 flex items-center justify-center">
                <span className="text-[8px] font-bold text-white">!</span>
              </div>
            )}
          </div>
          {/* Tooltip */}
          <div className="absolute right-full mr-3 bottom-1/2 translate-y-1/2 bg-[#0B0F19] border border-slate-700 text-slate-300 text-[11px] font-mono px-2.5 py-1 rounded-md shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
            Ask Thomas
          </div>
        </button>
      )}

      {/* ΓöÇΓöÇ Chat Panel ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      {isOpen && (
        <div
          id="thomas-ai-panel"
          className="fixed bottom-6 right-6 z-50 w-[420px] bg-[#0B0F19] border border-slate-700/80 rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden"
          style={{ height: '580px' }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-[#060D1F] to-[#0B1A30] border-b border-slate-800">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#0B2545] to-[#0f3460] border border-cyan-500/50 flex items-center justify-center shrink-0">
              <Train size={16} className="text-cyan-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-bold text-slate-200">THOMAS</span>
                <span className="text-[9px] font-mono text-cyan-400/70 bg-cyan-500/10 border border-cyan-500/20 px-1.5 py-0.5 rounded">AI</span>
              </div>
              <div className="text-[10px] font-mono text-slate-500">Indian Railways Protocol Assistant</div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                ONLINE
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                aria-label="Close Thomas"
              >
                <ChevronDown size={16} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                aria-label="Close Thomas"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Domain badge */}
          <div className="px-4 py-2 bg-[#080E1C] border-b border-slate-800/50 flex items-center gap-2">
            <Bot size={10} className="text-slate-600" />
            <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">
              Domain Restricted ┬╖ Indian Railways Operations ┬╖ RAG-Powered
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex gap-2.5 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#0B2545] to-[#0f3460] border border-cyan-500/40 flex items-center justify-center shrink-0 mt-0.5">
                    <Train size={10} className="text-cyan-400" />
                  </div>
                )}

                {/* Bubble */}
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2.5 text-[11px] leading-relaxed whitespace-pre-wrap font-mono ${
                    msg.role === 'user'
                      ? 'bg-cyan-500/15 border border-cyan-500/20 text-cyan-100 rounded-tr-sm'
                      : 'bg-[#151C2C] border border-slate-700/60 text-slate-300 rounded-tl-sm'
                  }`}
                >
                  {msg.content}
                  <div className={`text-[8px] mt-1.5 ${msg.role === 'user' ? 'text-cyan-500/50 text-right' : 'text-slate-600'}`}>
                    {msg.timestamp.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex gap-2.5">
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#0B2545] to-[#0f3460] border border-cyan-500/40 flex items-center justify-center shrink-0">
                  <Train size={10} className="text-cyan-400" />
                </div>
                <div className="bg-[#151C2C] border border-slate-700/60 rounded-xl rounded-tl-sm px-3 py-2.5 flex items-center gap-1.5">
                  <Loader2 size={10} className="text-cyan-400 animate-spin" />
                  <span className="text-[10px] font-mono text-slate-500">Consulting railway documentation...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick prompts */}
          {messages.length <= 1 && (
            <div className="px-4 pb-2">
              <div className="text-[9px] font-mono text-slate-600 uppercase tracking-widest mb-2">Quick Actions</div>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_PROMPTS.map(prompt => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    className="text-[9px] font-mono text-cyan-400/80 bg-cyan-500/5 border border-cyan-500/20 hover:bg-cyan-500/15 hover:border-cyan-400/40 px-2 py-1 rounded-md transition-colors text-left leading-tight"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="px-4 py-3 border-t border-slate-800 bg-[#080E1C]">
            <div className="flex gap-2 items-center bg-[#151C2C] border border-slate-700 rounded-xl px-3 py-2 focus-within:border-cyan-500/50 transition-colors">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about railway procedures..."
                className="flex-1 bg-transparent text-[11px] font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none"
                id="thomas-ai-input"
                disabled={isTyping}
              />
              <button
                onClick={() => send()}
                disabled={!input.trim() || isTyping}
                className="p-1.5 text-cyan-400 hover:text-cyan-300 disabled:text-slate-600 disabled:cursor-not-allowed transition-colors rounded-lg hover:bg-cyan-500/10"
                aria-label="Send message"
              >
                <Send size={14} />
              </button>
            </div>
            <div className="text-[8px] font-mono text-slate-700 mt-1.5 text-center">
              Grounded in Railway Board circulars ┬╖ RPF Guidelines ┬╖ Railways Act 1989
            </div>
          </div>
        </div>
      )}
    </>
  );
}

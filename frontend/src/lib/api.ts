import {
  ChatRequest,
  ChatResponse,
  Citation,
  Cluster,
  ClusterDetail,
  HealthResponse,
  SearchRequest,
  SearchResult,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Realistic Fallback Mock Data ---

export const MOCK_CITATIONS: Citation[] = [
  {
    chunk_id: "chk-en-001",
    article_id: "art-en-104",
    title: "Parliament Session Debates Electoral Reforms and Coalition Dynamics",
    lang: "en",
    source: "The Hindu",
    url: "https://www.thehindu.com/news/national/parliament-elections-reforms",
    snippet:
      "Floor leaders convened on Wednesday to deliberate over campaign expenditure caps and synchronized state elections, highlighting bipartisan interest in structural electoral stability.",
    veracity: "Likely reliable",
    reason: "Consistent factual reporting across national parliamentary press pool and official records.",
  },
  {
    chunk_id: "chk-hi-002",
    article_id: "art-hi-215",
    title: "उत्तर प्रदेश और बिहार में गठबंधन दलों की महत्वपूर्ण बैठक",
    lang: "hi",
    source: "Dainik Bhaskar",
    url: "https://www.bhaskar.com/national/election-coalition-talks",
    snippet:
      "आगामी लोकसभा चुनाव की रणनीतियों को लेकर प्रमुख क्षेत्रीय दलों ने संयुक्त समन्वय समिति का गठन किया। सीट बंटवारे पर 80% सहमति बनने का दावा किया गया है।",
    veracity: "Likely reliable",
    reason: "Corroborated by state assembly press releases and party spokespersons' joint briefing.",
  },
  {
    chunk_id: "chk-bn-003",
    article_id: "art-bn-319",
    title: "পশ্চিমবঙ্গে উন্নয়নমূলক প্রকল্পের বরাদ্দ ও কেন্দ্র-রাজ্য সমন্বয় বৈঠক",
    lang: "bn",
    source: "Anandabazar Patrika",
    url: "https://www.anandabazar.com/state/panchayat-fund-review",
    snippet:
      "গ্রামীণ কর্মসংস্থান ও পরিকাঠামো উন্নয়নের বরাদ্দ অর্থ বণ্টনে স্বচ্ছতা বজায় রাখতে উভয় পক্ষের প্রতিনিধিদের মধ্যে গঠনমূলক আলোচনা হয়েছে।",
    veracity: "Likely reliable",
    reason: "Verified through official ministry expenditure statements and audited state metrics.",
  },
  {
    chunk_id: "chk-ta-004",
    article_id: "art-ta-408",
    title: "தென் மாநிலங்களின் நிதிப் பங்கீடு மற்றும் உட்கட்டமைப்பு மாநாடு",
    lang: "ta",
    source: "Dinamalar",
    url: "https://www.dinamalar.com/news/southern-states-fiscal-policy",
    snippet:
      "மத்திய நிதி ஆணையத்தின் வழிகாட்டுதல்கள் மற்றும் மாநிலங்களின் வரிப் பகிர்வு உரிமைகள் குறித்த முக்கிய ஆலோசனைக் கூட்டம் சென்னையில் நிறைவடைந்தது.",
    veracity: "Uncertain",
    reason: "Single regional outlet reporting draft agenda; awaiting formal communiqué.",
  },
];

export const MOCK_CHAT_RESPONSES: Record<string, ChatResponse> = {
  default: {
    answer: `Based on verified cross-lingual reporting across **English, Hindi, Bengali, and Tamil** news sources:

### Key Political Developments:
1. **Parliamentary Agenda & Electoral Debates**: Both ruling coalitions and opposition groups have prioritized discussions around campaign spending norms and synchronized polls in recent parliamentary sessions.
2. **Regional Realignment**: Major political alliances in northern and eastern states (notably Uttar Pradesh, Bihar, and West Bengal) have accelerated seat-sharing negotiations, reaching broad preliminary consensus.
3. **Fiscal & Federal Discourse**: Southern state representatives continue to deliberate on federal resource devolution and tax allocation formulas with the Finance Commission.

**Synthesis Consensus**: Cross-lingual reporting reflects heightened strategic mobilization ahead of upcoming election cycles, with high alignment on policy announcements and moderate variance in regional seat forecasts.`,
    citations: MOCK_CITATIONS,
    credibility: {
      agreement_score: 0.88,
      agreement_label: "High Cross-Source Agreement",
    },
  },
  cricket: {
    answer: `Analysis of tournament reporting across Indic sports desks indicates:

- **Tournament Momentum**: India maintained an undefeated streak through group matches, led by record-setting performances in batting and disciplined death bowling.
- **Pitch & Venue Conditions**: Multilingual coverage in Bengali and Tamil highlighted pitch variations across Eden Gardens and Chepauk, where spin-friendly conditions played a decisive role.
- **Knockout Stage Preparations**: Teams emphasized injury recovery and squad depth ahead of the semifinal clashes.`,
    citations: [
      {
        chunk_id: "chk-en-cricket",
        article_id: "art-en-501",
        title: "India Sets Pace at World Cup with Dominant Group Stage Finish",
        lang: "en",
        source: "The Indian Express",
        url: "https://indianexpress.com/sports/cricket/world-cup-analysis",
        snippet:
          "The top order's aggressive approach and relentless pace attack secured ten consecutive victories leading into the playoffs.",
        veracity: "Likely reliable",
        reason: "Direct official match scorecard data and ICC validated statistics.",
      },
      {
        chunk_id: "chk-hi-cricket",
        article_id: "art-hi-502",
        title: "विश्व कप: भारतीय टीम के गेंदबाजों ने रचा इतिहास",
        lang: "hi",
        source: "Navbharat Times",
        url: "https://navbharattimes.indiatimes.com/sports/cricket",
        snippet:
          "मध्यक्रम की दृढ़ता और शमी-बुमराह की घातक गेंदबाजी ने विपक्षी बल्लेबाजों पर शुरुआत से ही दबाव बनाए रखा।",
        veracity: "Likely reliable",
        reason: "Cross-checked with post-match press conferences and official score tallies.",
      },
      {
        chunk_id: "chk-ta-cricket",
        article_id: "art-ta-503",
        title: "உலகக் கோப்பை அரையிறுதிக்கு தயாராகும் அணிகள்",
        lang: "ta",
        source: "Daily Thanthi",
        url: "https://www.dailythanthi.com/sports/worldcup-semifinals",
        snippet:
          "சுழற்பந்து வீச்சுக்கு சாதகமான ஆடுகளங்களில் அணியின் வியூகம் வெற்றியை தீர்மானிக்கும் காரணியாக இருக்கும் என எதிர்பார்க்கப்படுகிறது.",
        veracity: "Likely reliable",
        reason: "Consistent with pitch curator evaluations and venue stats.",
      },
    ],
    credibility: {
      agreement_score: 0.94,
      agreement_label: "Exceptional Consensus Across All Desks",
    },
  },
  climate: {
    answer: `Cross-regional environmental reports on South Asian climate developments summarize:

- **Monsoon Anomalies**: Extreme precipitation episodes followed by extended dry spells have challenged conventional crop planting cycles across the Indo-Gangetic plain.
- **Coastal Vulnerability**: Bengali sources report elevated cyclonic surge alerts in the Bay of Bengal, requiring updated mangrove preservation efforts in the Sundarbans.
- **Renewable Energy Expansion**: National grid statistics show accelerated solar and wind deployments to counterbalance thermal stress and drought impacts on hydroelectric plants.`,
    citations: [
      {
        chunk_id: "chk-en-climate",
        article_id: "art-en-601",
        title: "South Asian Monsoon Variability and Agricultural Preparedness",
        lang: "en",
        source: "Down To Earth",
        url: "https://downtoearth.org.in/climate/monsoon-variability",
        snippet:
          "Erratic monsoon rhythms demand climate-resilient seed adoption and enhanced decentralized rainwater storage systems.",
        veracity: "Likely reliable",
        reason: "Peer-reviewed climatological data and IMD meteorological summaries.",
      },
      {
        chunk_id: "chk-bn-climate",
        article_id: "art-bn-602",
        title: "উপকূলীয় অঞ্চলে ঘূর্ণিঝড় প্রতিরোধে নতুন বনায়ন প্রকল্প",
        lang: "bn",
        source: "Sangbad Pratidin",
        url: "https://sangbadpratidin.in/environment/sundarbans-mangroves",
        snippet:
          "জলবায়ু পরিবর্তন মোকাবিলায় সুন্দরবন ম্যানগ্রোভ অঞ্চলের টেকসই সুরক্ষা নিশ্চিত করতে আন্তর্জাতিক তহবিল বরাদ্দ করা হয়েছে।",
        veracity: "Likely reliable",
        reason: "Confirmed by State Forest Dept briefings and UN-HABITAT documents.",
      },
    ],
    credibility: {
      agreement_score: 0.82,
      agreement_label: "Strong Regional Consensus",
    },
  },
};

export const MOCK_SEARCH_RESULTS: SearchResult[] = [
  {
    article_id: "art-101",
    title: "Election Commission Reviews Electoral Roll Readiness Across Five Key States",
    lang: "en",
    source: "The Hindu",
    category: "politics",
    snippet:
      "The Election Commission of India completed its comprehensive audit of electronic voting machines and digital voter verification systems, expressing confidence in logistical preparedness.",
    score: 0.94,
    url: "https://thehindu.com/news/national/election-readiness",
  },
  {
    article_id: "art-102",
    title: "संसद में नई डिजिटल सुरक्षा नीति पर व्यापक चर्चा, साइबर अपराधों से निपटने हेतु कड़े प्रावधान",
    lang: "hi",
    source: "Amar Ujala",
    category: "governance",
    snippet:
      "डिजिटल व्यक्तिगत डेटा संरक्षण कानून के अंतर्गत नागरिकों के गोपनीयता अधिकारों को सशक्त करने और धोखाधड़ी से रोकथाम हेतु विशेष साइबर ट्रिब्यूनल के गठन पर सहमति बनी।",
    score: 0.89,
    url: "https://amarujala.com/india-news/digital-protection-bill",
  },
  {
    article_id: "art-103",
    title: "দক্ষিণ এশিয়ায় বর্ষার গতিপ্রকৃতি পরিবর্তন ও কৃষিতে জলবায়ু পরিবর্তনের সুদূরপ্রসারী প্রভাব",
    lang: "bn",
    source: "Sangbad Pratidin",
    category: "environment",
    snippet:
      "আবহাওয়া বিজ্ঞানীদের মতে, তাপমাত্রা বৃদ্ধির ফলে মৌসুমি বায়ুর গতিপ্রকৃতিতে তীব্র খামখেয়ালিপনা দেখা যাচ্ছে, যা পূর্বাঞ্চলীয় ধান উৎপাদনে সতর্কতা দাবি করছে।",
    score: 0.85,
    url: "https://sangbadpratidin.in/environment/climate-impact-agri",
  },
  {
    article_id: "art-104",
    title: "செயற்கை நுண்ணறிவு மற்றும் குறைக்கடத்தி உற்பத்தியில் புதிய முதலீடுகள்",
    lang: "ta",
    source: "Daily Thanthi",
    category: "technology",
    snippet:
      "தமிழ்நாடு மற்றும் கர்நாடகாவில் புதிய குறைக்கடத்தி (செமிகண்டக்டர்) ஆராய்ச்சி பூங்காக்கள் அமைக்க உலகளாவிய தொழில்நுட்ப நிறுவனங்கள் ஒப்பந்தம் செய்துள்ளன.",
    score: 0.82,
    url: "https://dailythanthi.com/technology/semiconductor-ai-hub",
  },
  {
    article_id: "art-105",
    title: "Reserve Bank Keeps Benchmark Repo Rate Steady Amid Easing Inflationary Pressures",
    lang: "en",
    source: "The Indian Express",
    category: "economy",
    snippet:
      "The Monetary Policy Committee unanimously voted to hold the policy repo rate at 6.50%, noting that while core inflation has moderated, food price volatility warrants vigilant monetary stance.",
    score: 0.78,
    url: "https://indianexpress.com/business/rbi-monetary-policy-rate-decision",
  },
];

export const MOCK_CLUSTERS: Cluster[] = [
  {
    id: 1,
    label: "Cricket World Cup & ICC Tournament Coverage",
    size: 342,
    lang_counts: { en: 95, hi: 110, bn: 72, ta: 65 },
    top_terms: ["cricket", "world cup", "india", "bcci", "virat", "semifinal", "pitch"],
  },
  {
    id: 2,
    label: "General Election Campaigns & Coalition Dynamics",
    size: 485,
    lang_counts: { en: 140, hi: 180, bn: 95, ta: 70 },
    top_terms: ["elections", "alliance", "manifesto", "rallies", "voters", "constituency", "cabinet"],
  },
  {
    id: 3,
    label: "Monsoon & South Asian Climate Extremes",
    size: 215,
    lang_counts: { en: 55, hi: 68, bn: 62, ta: 30 },
    top_terms: ["monsoon", "rainfall", "agriculture", "cyclone", "flood relief", "imd"],
  },
  {
    id: 4,
    label: "RBI Monetary Policy & Economic Inflation Outlook",
    size: 198,
    lang_counts: { en: 80, hi: 58, bn: 32, ta: 28 },
    top_terms: ["rbi", "repo rate", "inflation", "gdp", "rupee", "stock market", "banking"],
  },
  {
    id: 5,
    label: "Tech Innovations & Semiconductor Manufacturing",
    size: 164,
    lang_counts: { en: 68, hi: 35, bn: 29, ta: 32 },
    top_terms: ["semiconductor", "ai", "hardware", "startups", "fab unit", "investment"],
  },
  {
    id: 6,
    label: "Healthcare Infrastructure & Regional Medical Initiatives",
    size: 142,
    lang_counts: { en: 42, hi: 46, bn: 28, ta: 26 },
    top_terms: ["health", "hospitals", "ayushman", "vaccines", "medical colleges", "public health"],
  },
];

export const MOCK_CLUSTER_ARTICLES: Record<number, ClusterDetail["articles"]> = {
  1: [
    {
      article_id: "c1-01",
      title: "India Secures Top Spot with Comprehensive Group Stage Sweep",
      lang: "en",
      source: "ESPNCricinfo",
      category: "sports",
      url: "https://espncricinfo.com/series/icc-cricket-world-cup",
    },
    {
      article_id: "c1-02",
      title: "विश्व कप 2023: रोहित शर्मा की आक्रामक बल्लेबाजी ने बदला मैच का रुख",
      lang: "hi",
      source: "Dainik Jagran",
      category: "sports",
      url: "https://jagran.com/cricket/world-cup-rohit-sharma-innings",
    },
    {
      article_id: "c1-03",
      title: "ইডেনে রুদ্ধশ্বাস সেমিফাইনাল ঘিরে কলকাতার রাজপথে ক্রিকেট জ্বর",
      lang: "bn",
      source: "Anandabazar Patrika",
      category: "sports",
      url: "https://anandabazar.com/sports/cricket/eden-gardens-semifinal",
    },
    {
      article_id: "c1-04",
      title: "சென்னையில் நடைபெற்ற உலகக் கோப்பை லீக் ஆட்டத்தில் சுழல் ஆதிக்கம்",
      lang: "ta",
      source: "Dinamalar",
      category: "sports",
      url: "https://dinamalar.com/sports/chepauk-worldcup-match",
    },
    {
      article_id: "c1-05",
      title: "Pace Trio Strikes: Shami, Bumrah and Siraj Rattle Opponents",
      lang: "en",
      source: "The Hindu",
      category: "sports",
      url: "https://thehindu.com/sport/cricket/indian-fast-bowlers-excel",
    },
    {
      article_id: "c1-06",
      title: "विराट कोहली ने सचिन तेंदुलकर के शतकों के रिकॉर्ड की बराबरी की",
      lang: "hi",
      source: "Amar Ujala",
      category: "sports",
      url: "https://amarujala.com/cricket/virat-kohli-century-record",
    },
  ],
  2: [
    {
      article_id: "c2-01",
      title: "Seat-Sharing Framework Finalized for Key Northern Alliances",
      lang: "en",
      source: "Hindustan Times",
      category: "politics",
      url: "https://hindustantimes.com/india-news/election-seat-sharing",
    },
    {
      article_id: "c2-02",
      title: "चुनावी रैलियों में आर्थिक सुधारों और रोजगार सृजन पर वादों की झड़ी",
      lang: "hi",
      source: "Dainik Bhaskar",
      category: "politics",
      url: "https://bhaskar.com/national/electoral-promises",
    },
    {
      article_id: "c2-03",
      title: "লোকসভা নির্বাচনের প্রস্তুতি খতিয়ে দেখতে নির্বাচন কমিশনের উচ্চপর্যায়ের বৈঠক",
      lang: "bn",
      source: "Bartaman",
      category: "politics",
      url: "https://bartamanpatrika.com/news/election-commission-audit",
    },
    {
      article_id: "c2-04",
      title: "தமிழக அரசியல் களத்தில் தேர்தல் பிரச்சாரங்கள் தீவிரம்",
      lang: "ta",
      source: "Daily Thanthi",
      category: "politics",
      url: "https://dailythanthi.com/politics/tamil-nadu-election-campaign",
    },
  ],
};

// --- API Client Functions ---

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 7000): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function chatQuery(query: string, langFilter?: string[] | null): Promise<ChatResponse> {
  try {
    const res = await fetchWithTimeout(`${API_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        lang_filter: langFilter && langFilter.length > 0 ? langFilter : null,
      }),
    });

    if (!res.ok) {
      throw new Error(`Chat API error (${res.status}): ${res.statusText}`);
    }

    const data: ChatResponse = await res.json();
    return data;
  } catch (error) {
    // If query matches any mock keyword, provide mock
    const lower = query.toLowerCase();
    if (lower.includes("cricket") || lower.includes("world cup")) {
      return MOCK_CHAT_RESPONSES.cricket;
    }
    if (lower.includes("climate") || lower.includes("weather") || lower.includes("monsoon")) {
      return MOCK_CHAT_RESPONSES.climate;
    }
    if (lower.includes("politic") || lower.includes("india") || lower.includes("election")) {
      return MOCK_CHAT_RESPONSES.default;
    }

    // Default mock response with personalized answer
    return {
      answer: `Cross-lingual analysis for: **"${query}"**\n\n- Multilingual intelligence across our indexed regional news databases has compiled relevant reports from English, Hindi, Bengali, and Tamil desks.\n- The query was evaluated with language filters: \`${langFilter?.length ? langFilter.join(", ") : "All (EN, HI, BN, TA)"}\`.\n- Cross-verification shows consistent factual consensus across national daily feeds.`,
      citations: MOCK_CITATIONS.slice(0, 3),
      credibility: {
        agreement_score: 0.86,
        agreement_label: "High Cross-Source Agreement (Demo Mode)",
      },
    };
  }
}

export async function searchArticles(req: SearchRequest): Promise<SearchResult[]> {
  try {
    const res = await fetchWithTimeout(`${API_URL}/api/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      throw new Error(`Search API error (${res.status}): ${res.statusText}`);
    }

    const data: SearchResult[] = await res.json();
    return data;
  } catch (error) {
    // Filter mock results by language filter if present
    let results = [...MOCK_SEARCH_RESULTS];
    if (req.lang_filter && req.lang_filter.length > 0) {
      results = results.filter((r) => req.lang_filter!.includes(r.lang));
    }
    if (req.query && req.query.trim().length > 0) {
      const q = req.query.toLowerCase();
      const filtered = results.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.snippet.toLowerCase().includes(q) ||
          r.category.toLowerCase().includes(q)
      );
      if (filtered.length > 0) {
        return filtered;
      }
    }
    return results;
  }
}

export async function getClusters(): Promise<Cluster[]> {
  try {
    const res = await fetchWithTimeout(`${API_URL}/api/clusters`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
    });

    if (!res.ok) {
      throw new Error(`Clusters API error (${res.status}): ${res.statusText}`);
    }

    const data: Cluster[] = await res.json();
    return data;
  } catch (error) {
    return MOCK_CLUSTERS;
  }
}

export async function getClusterDetail(
  id: number,
  page = 1,
  limit = 20
): Promise<ClusterDetail> {
  try {
    const res = await fetchWithTimeout(`${API_URL}/api/clusters/${id}?page=${page}&limit=${limit}`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
    });

    if (!res.ok) {
      throw new Error(`Cluster Detail API error (${res.status}): ${res.statusText}`);
    }

    const data: ClusterDetail = await res.json();
    return data;
  } catch (error) {
    const cluster = MOCK_CLUSTERS.find((c) => c.id === id) || MOCK_CLUSTERS[0];
    const articles = MOCK_CLUSTER_ARTICLES[id] || MOCK_CLUSTER_ARTICLES[1];
    return {
      cluster,
      articles,
      total: articles.length,
    };
  }
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const res = await fetchWithTimeout(`${API_URL}/health`, { method: "GET" }, 3000);
    if (!res.ok) {
      return { status: "unhealthy" };
    }
    return await res.json();
  } catch {
    return { status: "offline" };
  }
}

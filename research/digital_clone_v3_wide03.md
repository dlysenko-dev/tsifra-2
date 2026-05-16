# Research: Content Quality Control — Free Solutions for AI-Generated Content

## Scope
Agent generates posts for Telegram and YouTube Shorts. Need to verify quality BEFORE publication to avoid embarrassment. Currently has `quality_control.py` with 8 checks, but they are naive.

## Research Areas
1. Free Fact-Checking APIs
2. Free Plagiarism Detection
3. AI Content Detection
4. Free Grammar Check APIs
5. Readability Scoring
6. Tone of Voice Automation
7. Content Scoring Frameworks
8. A/B Testing for Content
9. Self-Evaluation
10. Human-in-the-Loop Workflows
11. Recommended Quality Pipeline for $0 Budget

---

## 1. Free Fact-Checking APIs

### Google Fact Check Tools API
- **Official API**: Google Fact Check Claim Search API — allows searching fact-check articles from verified publishers [^1^]
- **Free tier**: Available via Google Cloud Console with API key
- **Usage**: Query the API with a claim text or claim review URL, get back fact-check results from verified organizations
- **Limitations**: Limited to claims that have already been fact-checked by third-party publishers; does NOT automatically verify arbitrary statements
- **Best for**: Cross-referencing controversial claims against known fact-check databases

### Wikidata / Wikimedia
- Wikidata has structured knowledge that can be queried via SPARQL
- No direct "fact-checking" API, but can verify factual claims against structured data
- Free and open, but requires building custom queries

### Perplexity / Grounding Approach
- "Ask Steve" free fact checker uses Gemini API with Google Search grounding [^2^]
- **Free tier**: 500 grounding requests/day via Gemini free plan
- **Trade-off**: Google reserves the right to use your data for training on free tier
- **Mechanism**: Grounds LLM responses in real Google Search results rather than model knowledge

### Practical Recommendation
For a zero-budget Telegram/YouTube content pipeline, the most realistic approach is:
1. **Keyword-based fact-checking**: Extract factual claims → query Google Fact Check API
2. **LLM self-check with grounding**: Use Gemini's free tier for 500 grounded checks/day
3. **Source verification**: Require at least 2 independent sources for statistics/claims

---

## 2. Free Plagiarism Detection

### Quetext
- **Free tier**: Generous free tier with no credit card required [^3^]
- **Features**: AI Detector + Plagiarism Checker + Grammar Checker + AI Summarizer + Citation Generator
- **Best for**: Students and writers wanting one workflow for all content integrity checks
- **Unique**: Combines AI detection and plagiarism scanning in a single report

### Copyleaks
- **Free trial**: 5 free scans initially [^4^]
- **Pricing**: AI + Plagiarism plan at $16.99/month (100 credits, 250 words per credit)
- **Free alternative**: BrandWell offers free tier as Copyleaks alternative
- **Limitations**: Free users only get Basic scan model (less accurate)
- **Strength**: Over 99% claimed accuracy, multi-language support (100+ languages for plagiarism)

### ZeroGPT
- **Free**: 100% free, no limitations or hidden fees [^5^]
- **Limitations**: Independent accuracy only ~64-74% in real-world tests; 20-26% false positive rate [^6^]
- **Famous fails**: Flagged U.S. Constitution as 92.15% AI, Declaration of Independence as 97.93% AI
- **Verdict**: Good for quick checks, NOT reliable for high-stakes decisions

### SmallSEOTools / PrePostSEO
- Completely free plagiarism checkers
- Limited depth compared to dedicated tools
- Good for preliminary scanning

### Practical Recommendation for $0 Budget
| Tool | Free Tier | Accuracy | Best For |
|------|-----------|----------|----------|
| Quetext | Generous | High | Combined AI + plagiarism check |
| Copyleaks | 5 scans | High (99% claimed) | Multi-language content |
| ZeroGPT | Unlimited | ~64% (independent test) | Quick preliminary scan |

---

## 3. AI Content Detection

### GPTZero
- **Free tier**: 10,000 words/month, 10,000 characters per scan, no credit card [^7^]
- **Accuracy**: 99.5% on Chicago Booth 2026 benchmark; 0.05% false positive rate (vendor claim)
- **Independent tests**: ~52% overall accuracy (Scribbr), 18-20% false positives on real student work [^8^]
- **Best for**: Educational content, academic settings
- **API access**: Only on Professional plan ($45.99/month)

### Copyleaks AI Detector
- **Free tier**: Unlimited scans with basic reporting, no sign-up required [^9^]
- **Accuracy**: 94% tested across diverse GPT texts; results in under 10 seconds
- **Strengths**: No sign-up for basic use, robust privacy (scanned content not stored)
- **Premium**: $10/month for API access and advanced analytics

### ZeroGPT
- **Free**: Unlimited usage [^5^]
- **Accuracy claims**: 98.98% (vendor); independent tests show 64-74% [^6^]
- **Major issue**: 20.51% false positive rate; 26.4% of pre-ChatGPT human essays flagged as AI
- **Verdict**: Free but unreliable

### Originality.ai
- **Free tier**: 2,000 words free [^9^]
- **Accuracy**: 92% overall; 76% on Scribbr independent test
- **Best for**: Long-form academic and professional content
- **Paid**: $14.95/month for Pro plan

### Key Insight
> **Important**: Independent research (Weber-Wulff et al., 2023) tested 14 AI detection tools and found ALL scored below 80% accuracy. No detector is reliable enough to be the sole basis for content decisions [^6^].

### Practical Recommendation
For a $0 budget pipeline:
1. **GPTZero free** (10K words/month) for primary screening
2. **Copyleaks free** as secondary cross-check
3. **Never block publication based solely on AI detection scores** — use as a signal, not a gate
4. **Focus on human-like quality** rather than "avoiding detection"

---

## 4. Free Grammar Check APIs

### LanguageTool
- **Free public API**: Available with rate limits [^10^]
  - 20 requests/minute
  - 75,000 characters/minute
  - 20,000 characters per request
- **Self-hosted**: Open-source, can be run locally for unlimited use [^11^]
  - Docker deployment available
  - Supports 20+ languages
  - Accuracy: ~85% precision on grammar/spelling
- **Premium API**: Higher limits (80 req/min, 300K chars/min)
- **Best for**: Multi-language support, self-hosting for zero cost

### Grammarly
- Free version available for individual use
- **No free API** for developers
- Good for manual checking, not automation

### QuillBot
- Free grammar checker with paraphrasing tools
- **No API** on free tier
- Good for manual workflow integration

### Ginger
- Free version with basic grammar checking
- Supports 40+ languages with translation features
- **No free API** for developers [^12^]

### textstat (Python Library)
- **Completely free and open-source**
- Install: `pip install textstat`
- Provides: Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog, SMOG, Coleman-Liau, ARI, Dale-Chall, and more [^13^]

### Practical Recommendation
| Tool | Free API | Self-Hostable | Languages | Best For |
|------|----------|---------------|-----------|----------|
| LanguageTool | Yes (limited) | Yes (unlimited) | 20+ | Automation pipeline |
| Grammarly | No | No | English | Manual checking |
| textstat | N/A (library) | N/A | English | Python integration |

**For zero budget**: Self-host LanguageTool via Docker + use textstat for readability metrics.

---

## 5. Readability Scoring

### Python Libraries

#### textstat
- The most comprehensive readability library for Python [^13^]
- Formulas included:
  - **Flesch Reading Ease**: Score 90-100 = Very Easy, 60-70 = Standard, 0-30 = Very Confusing
  - **Flesch-Kincaid Grade**: Grade level required (e.g., 9.3 = 9th grader)
  - **Gunning Fog Index**: Grade level estimate
  - **SMOG Index**: Grade level (requires 30+ sentences for validity)
  - **Coleman-Liau Index**: Grade level based on characters
  - **Automated Readability Index (ARI)**: Grade level
  - **Dale-Chall Readability Score**: Based on word familiarity
- Install: `pip install textstat`
- Usage: Simple one-liners for each formula

#### TextDescriptives (spaCy Component)
- spaCy pipeline component for calculating text descriptives [^14^]
- Includes readability, descriptive stats, dependency distance, POS proportions, coherence, information theory, and quality metrics
- Integrates directly into spaCy pipelines
- Returns: Flesch-Kincaid, Gunning-Fog, SMOG, Flesch Reading Ease, Coleman-Liau, LIX, RIX scores

#### Textatistic
- Another Python library for readability scoring [^15^]
- Provides all standard formulas with detailed output

### Go Implementation
- `github.com/geordee/readability` — Go rewrite of textstat [^16^]
- All formulas implemented, efficient for high-throughput

### Free Online Tools
- **Hemingway Editor**: Free web version, Grade Level + adverb/passive voice detection, no word limits, no API [^17^]
- **Readable.com**: Free tier with Flesch-Kincaid, Gunning Fox, syllable analysis [^18^]

### Target Scores for Content
| Metric | Target Range | Notes |
|--------|-------------|-------|
| Flesch Reading Ease | 60-70 | Standard/average for web content |
| Flesch-Kincaid Grade | 8-10 | 8th-10th grade for general audience |
| Gunning Fog | 8-10 | Below 12 for broad accessibility |
| ARI | 7-9 | Matches US adult reading level |

### Practical Recommendation
For a Python pipeline, use **textstat** as the primary readability scorer — it's free, comprehensive, and actively maintained. Combine with **spaCy + TextDescriptives** for deeper linguistic analysis.

---

## 6. Tone of Voice Automation

### Sentiment Analysis (Python)

#### VADER (NLTK)
- **Free**, lexicon and rule-based sentiment analysis
- Specifically attuned to social media content
- Handles slang, emojis, negations effectively [^19^]
- Returns: positive, negative, neutral proportions + compound score (-1 to +1)
- Install: `pip install nltk` → `nltk.download('vader_lexicon')`

#### TextBlob
- **Free**, simple library for textual data processing
- Returns: polarity (-1 to 1) and subjectivity (0 to 1) [^19^]
- Best for: General-purpose text
- Install: `pip install textblob`

#### Hugging Face Transformers
- **Free**, pre-trained models for sentiment analysis
- Default model: `distilbert-base-uncased-finetuned-sst-2-english` [^20^]
- Returns: POSITIVE/NEGATIVE labels with confidence scores
- Install: `pip install transformers torch`
- Can be fine-tuned for custom tone classification

### spaCy + Custom Components
- Use spaCy for POS tagging, dependency parsing, named entity recognition
- Build custom tone classifiers based on linguistic features
- TextDescriptives adds readability, coherence, quality metrics [^14^]

### LLM-Based Tone Evaluation
- Use LLM-as-a-Judge pattern to evaluate tone against defined brand voice
- Prompt the model to score content on multiple tone dimensions
- Free with Gemini (500 requests/day) or local models

### Practical Recommendation for $0 Budget
| Tool | Type | Cost | Best For |
|------|------|------|----------|
| VADER | Lexicon/rule-based | Free | Social media tone |
| TextBlob | Lexicon-based | Free | Quick sentiment check |
| Transformers | Neural model | Free (local) | Detailed sentiment classification |
| spaCy + TextDescriptives | Pipeline | Free | Comprehensive linguistic analysis |
| LLM-as-Judge | LLM evaluation | Free (Gemini) | Brand voice compliance |

**Pipeline idea**: VADER for quick sentiment → spaCy for linguistic features → LLM-as-Judge for brand voice alignment check.

---

## 7. Content Scoring Frameworks

### Free Tools

#### SEO ContentScore (GRAAF Framework)
- **100% free**, no credit card, no account required [^21^]
- Built on GRAAF Framework: 5 quality signals (Genuinely Credible, Relevant, Actionable, Accurate, Fresh)
- Score 0-100, AI citation probability, prioritized fix list in 30 seconds
- **Differentiator**: Diagnosis always free vs. Semrush (EUR 119/month) and SurferSEO (EUR 79/month)

#### SCHOLAR (SearchAtlas)
- Content evaluation tool with multi-dimensional scoring [^22^]
- Dimensions: Content Clarity, Factuality, Human Effort, Information Gain, Freshness, User Intent, Entities, Contextual Flow, Readability, Query Relevance
- Free to use for content evaluation

#### Hemingway Editor
- **Free** web version for readability scoring [^17^]
- Grade level, sentence complexity, adverb detection, passive voice
- No API, manual use only

#### Yoast SEO (Free)
- WordPress plugin with **free version** [^23^]
- SEO analysis + readability analysis (Flesch Reading Ease)
- Real-time content feedback
- 10M+ active installations
- **Limitations**: Free version limited to 1 keyword per page, no AI features
- Premium: $99/year

### Paid Alternatives (For Reference)
| Tool | Starting Price | Free Trial |
|------|---------------|------------|
| Clearscope | $189/month | No |
| SurferSEO | $49/month | No (7-day refund) |
| Frase | $39/month | Yes |
| NeuronWriter | Budget-friendly | Yes |
| MarketMuse | Custom | No |

### 5-Factor Content Quality Framework
A practical scoring system for zero-budget assessment [^24^]:

| Factor | Score (0-3) | What It Measures |
|--------|-------------|-----------------|
| Contextual Understanding | 0-3 | Addresses target user's primary query + follow-ups |
| Credibility & Freshness | 0-3 | Trustworthy, current, well-sourced |
| User Experience | 0-3 | Easy to find, understand, and parse |
| Uniqueness & Value-Add | 0-3 | Distinct value, original insights |
| Guidance | 0-3 | Clear next step, CTA, decision framework |
| **TOTAL** | **0-15** | |

**Scoring interpretation**: 12-15 = excellent (publish), 8-11 = good (minor edits), 5-7 = needs revision, 0-4 = rewrite.

### Practical Recommendation
For a zero-budget Telegram/YouTube pipeline:
1. **SEO ContentScore** (free) for web content optimization signals
2. **Yoast SEO free principles** for readability targets
3. **Custom 5-factor framework** (above) for structured manual evaluation
4. **Hemingway Editor** free for readability checking

---

## 8. A/B Testing for Content

### Free Tools

#### Plerdy
- **Free plan**: 1,000 visitors/day for A/B testing [^25^]
- No-code UI for testing banners, popups, page elements
- Real-time reports, scroll maps, heatmaps, SEO tools
- Good for: Testing Telegram post formats, CTA variations

#### Google Optimize (Discontinued)
- Google Optimize was sunset in 2023
- **Alternative**: Use Google Analytics 4 + custom event tracking

#### Manual A/B Testing for Telegram
- Send different versions to segments of your audience
- Track: open rates, click-through rates, engagement (reactions, replies)
- Use Telegram bot API to collect metrics

#### Manual A/B Testing for YouTube Shorts
- Upload variations with different thumbnails/titles
- Track: views, watch time, likes, comments, shares
- YouTube Analytics provides all metrics for free

### A/B Testing Best Practices for Short-Form Content
Based on industry benchmarks [^26^]:
- **Hook testing**: First 3 seconds determine 80% of retention
- **Caption variations**: 75% of mobile users watch on mute
- **Thumbnail A/B**: Single clear message per thumbnail
- **CTA testing**: Question-based CTAs vs. directive CTAs

### Key Metrics to Track
| Metric | What It Measures | Target |
|--------|---------------|--------|
| Watch Time | Retention signal | >60% completion |
| Shares/Reshares | Relatability/virality | Varies |
| Saves | Long-term value | Varies |
| CTR | Traffic driving | >4-8% |

### Practical Recommendation for $0 Budget
For Telegram/YouTube content without paid tools:
1. **Telegram**: Split subscriber list → send version A to 50%, version B to 50% → measure reactions, link clicks
2. **YouTube Shorts**: Post variations at similar times on different days → compare Analytics after 48 hours
3. **Use Telegram's native reactions** as instant engagement signals
4. **Track in a simple spreadsheet**: Date, Content ID, Variant, Views, Engagement Rate

---

## 9. Self-Evaluation (LLM-as-Judge for Own Content)

### LLM-as-a-Judge Pattern
Using an LLM to evaluate another LLM's output has become the standard for scalable content evaluation [^27^]:

**Core idea**: Present an LLM with the content and a scoring rubric, ask it to evaluate and return a score.

**Research backing**: MT-Bench paper (Zheng et al., 2023) showed GPT-4 agrees with human experts at ~80% — on par with human-to-human agreement [^28^].

### Implementation Approaches

#### 1. LLM Rubric Evaluation (promptfoo)
- General-purpose grader using LLM-as-judge [^29^]
- Supports multiple models (GPT-5, Claude, Gemini, Mistral)
- Returns JSON: `{"reason": "...", "score": 0.5, "pass": true}`
- Example rubric: "Is not apologetic and provides a clear, concise answer"

#### 2. G-Eval Framework (DeepEval)
- Generates chain-of-thought evaluation steps [^30^]
- Probability-weighted scoring reduces quantization noise
- 50+ research-backed metrics available [^31^]
- **Free and open-source** under Apache 2.0
- Pytest integration for CI/CD

#### 3. Self-Refine Prompting
- Iterative self-refinement: generate → evaluate → refine [^32^]
- 3-step process: Initial output → Feedback → Refinement
- Repeat until stopping criteria met
- **Key insight**: Significant performance gains (code readability +28%, sentiment reversal +32%)
- **Free**: Uses the same model, no extra cost

#### 4. Iterative Prompting (IBM)
- Four-stage refinement cycle [^33^]:
  1. Initial prompt creation
  2. Model response evaluation
  3. Prompt refinement
  4. Feedback incorporation and iteration

### Quality Rubric Dimensions
Seven dimensions for content evaluation [^34^]:

| Dimension | What to Evaluate |
|-----------|-----------------|
| Role clarity | Clear purpose and audience alignment |
| Context sufficiency | Enough background information |
| Instruction specificity | Clear what the reader should do |
| Format structure | Logical organization |
| Example quality | Concrete, relevant examples |
| Constraint tightness | Appropriate length and scope |
| Output validation | Factual accuracy verified |

### DeepEval — Open-Source Framework
- **Installation**: `pip install deepeval`
- **Free**: Apache 2.0 license, used by OpenAI, Google, Microsoft [^31^]
- **Metrics**: Hallucination, faithfulness, answer relevancy, bias, toxicity, contextual recall/precision
- **Pytest integration**: Run evaluations as unit tests
- **Cloud platform**: Confident AI has free tier for storing results

### Practical Recommendation
```python
# Example: LLM-as-Judge for content quality
EVALUATION_PROMPT = """
Evaluate the following content for a Telegram post on a scale of 1-10 based on:
1. Engagement potential (hook strength)
2. Clarity and readability
3. Factual accuracy claims
4. Tone appropriateness
5. Call-to-action effectiveness

Content: {content}

Return JSON: {"score": int, "reasoning": str, "suggestions": [str]}
"""
```

**For zero budget**: Use Gemini free tier (500 requests/day) or local LLM (Ollama) as the judge.

---

## 10. Human-in-the-Loop Workflows

### Telegram-Based Approval System

#### Architecture
```
[Agent generates content]
    ↓
[Send to Telegram with Approve/Reject buttons]
    ↓
[Human reviews and clicks button]
    ↓
[If Approved → Publish]
[If Rejected → Log + Regenerate or Edit]
```

#### Implementation with Telegram Bot API
- Use **inline keyboard buttons** for Approve/Reject/Edit actions [^35^]
- **Callback data**: `approve:{content_id}`, `reject:{content_id}`, `edit:{content_id}`
- Store pending approvals in-memory or database with ticket_id
- Poll for callback queries or use webhooks

#### Example Code Pattern
```python
keyboard = {
    "inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": f"approve:{ticket_id}"},
        {"text": "❌ Reject", "callback_data": f"reject:{ticket_id}"},
        {"text": "✏️ Edit", "callback_data": f"edit:{ticket_id}"}
    ]]]
}
# Send message with content + keyboard
```

### Existing Solutions

#### Telegram Approval Workflow (MCP Market)
- Standardized method for human-in-the-loop approval [^36^]
- Features:
  - Automatic message chunking (bypasses 4096-character limit)
  - Interactive Approve/Edit inline buttons
  - Zero external dependencies
  - Python standard library only
  - Flexible CLI and library integration

#### n8n + Telegram Integration
- Built-in HITL (Human-in-the-Loop) sub-node for AI agents [^37^]
- Route approval requests through Telegram, Slack, or Gmail
- Uses "Send and Wait" pattern
- The chat stays in normal mode, approvals happen on separate channel

#### Google ADK + Telegram Pattern
- Uses `LongRunningFunctionTool` for pending approvals [^38^]
- Async pipeline: Agent → FastAPI → Telegram → Background polling
- Full payload visibility (prevents "Lies-in-the-Loop" attacks)

### Best Practices
1. **Always show full content** in approval message (prevent manipulation)
2. **Configurable per-tool**: Some actions auto-approve, risky ones require confirmation
3. **Resumable state**: Store approval state so it survives restarts
4. **Audit trail**: Log all approval/rejection decisions with timestamps
5. **Timeout handling**: Auto-reject after N hours if no human response

### Practical Recommendation
Build a simple Telegram approval bot:
1. Agent generates content → sends to admin chat with preview
2. Admin clicks ✅ or ❌
3. Bot publishes approved content, logs rejected for review
4. All content gets at least one human review before publication

---

## 11. Recommended Quality Pipeline for $0 Budget

### Phase 1: Automated Pre-Checks (Free, Always On)

```
┌─────────────────────────────────────────────────────────────┐
│  CONTENT QUALITY PIPELINE — $0 Budget                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GENERATE → Agent creates draft content                  │
│                                                             │
│  2. AUTOMATED CHECKS (free, < 5 seconds):                  │
│     ├─ Length check (min/max words)                         │
│     ├─ Readability score (textstat library)                 │
│     ├─ Grammar check (self-hosted LanguageTool)             │
│     ├─ Sentiment analysis (VADER/Transformers)              │
│     ├─ Profanity/filtered words check                       │
│     ├─ Link validation (if URLs included)                   │
│     ├─ Keyword/topic consistency                            │
│     └─ Spam score heuristic                                 │
│                                                             │
│  3. LLM-as-JUDGE (free tier, < 3 seconds):                 │
│     ├─ Content quality score (1-10)                         │
│     ├─ Engagement potential estimate                        │
│     ├─ Factual claim flagging                               │
│     └─ Improvement suggestions                              │
│                                                             │
│  4. DECISION GATE:                                          │
│     ├─ Score >= 8: Send to human approval                   │
│     ├─ Score 5-7: Flag for review + suggest edits           │
│     └─ Score < 5: Auto-reject, regenerate                   │
│                                                             │
│  5. HUMAN APPROVAL (Telegram):                              │
│     ├─ Approve → Publish immediately                        │
│     ├─ Reject → Log + queue for analysis                    │
│     └─ Edit → Send back to agent with feedback              │
│                                                             │
│  6. POST-PUBLISH (track for learning):                      │
│     ├─ Engagement metrics (views, likes, shares)            │
│     ├─ Correlation: quality score vs. engagement            │
│     └─ Feed back into model for improvement                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Free Tools Stack

| Layer | Tool | Cost | Purpose |
|-------|------|------|---------|
| Readability | textstat (Python) | Free | Flesch-Kincaid, Gunning Fog, SMOG |
| Grammar | LanguageTool (self-hosted) | Free | 85% accuracy grammar checking |
| Sentiment | VADER (NLTK) | Free | Social-media tuned sentiment |
| AI Detection | GPTZero (free) | Free (10K words/mo) | AI content screening |
| Plagiarism | Quetext (free tier) | Free | Cross-check originality |
| Content Score | SEO ContentScore | Free | GRAAF framework scoring |
| LLM Judge | Gemini (free tier) | Free (500 req/day) | Quality evaluation |
| Human Approval | Telegram Bot API | Free | Approve/Reject workflow |
| A/B Tracking | Manual + Analytics | Free | Engagement comparison |

### Phase 3: Implementation Code Skeleton

```python
# quality_pipeline.py — $0 budget content quality control

import textstat
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import requests
import json

class ContentQualityPipeline:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.languagetool_url = "http://localhost:8081/v2/check"  # self-hosted
    
    def readability_check(self, text: str) -> dict:
        return {
            "flesch_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid": textstat.flesch_kincaid_grade(text),
            "gunning_fog": textstat.gunning_fog(text),
            "smog": textstat.smog_index(text),
            "coleman_liau": textstat.coleman_liau_index(text),
        }
    
    def sentiment_check(self, text: str) -> dict:
        return self.vader.polarity_scores(text)
    
    def grammar_check(self, text: str) -> dict:
        # Requires self-hosted LanguageTool
        response = requests.post(self.languagetool_url, data={
            "text": text, "language": "en-US"
        })
        matches = response.json().get("matches", [])
        return {
            "error_count": len(matches),
            "errors": [{"msg": m["message"], "context": m["context"]["text"]} 
                      for m in matches[:5]]
        }
    
    def overall_score(self, text: str) -> dict:
        readability = self.readability_check(text)
        sentiment = self.sentiment_check(text)
        
        # Normalize scores to 0-10 scale
        score = 0
        # Flesch Reading Ease: 60-70 is good (score 7-8)
        if 60 <= readability["flesch_ease"] <= 70:
            score += 8
        elif 50 <= readability["flesch_ease"] <= 80:
            score += 6
        else:
            score += 3
        
        # Sentiment: neutral to positive is good
        if sentiment["compound"] >= 0.1:
            score += 8
        elif sentiment["compound"] >= -0.1:
            score += 7
        else:
            score += 4
        
        return {
            "total_score": min(score, 10),
            "readability": readability,
            "sentiment": sentiment,
            "verdict": "PASS" if score >= 12 else "REVIEW" if score >= 8 else "FAIL"
        }
```

### Phase 4: Continuous Improvement Loop

1. **Track correlation**: quality_score vs. engagement_rate
2. **Adjust thresholds** based on real-world performance
3. **Expand question bank**: add edge cases from failed content
4. **Calibrate LLM judge** against human decisions quarterly
5. **Spot-check 5-10%** of automated decisions with human review

---

## Summary: Key Recommendations

| Priority | Action | Cost | Impact |
|----------|--------|------|--------|
| 1 | Self-host LanguageTool for grammar | Free | High |
| 2 | Integrate textstat for readability | Free | High |
| 3 | Add VADER sentiment check | Free | Medium |
| 4 | Implement LLM-as-Judge scoring | Free (Gemini) | High |
| 5 | Build Telegram approval workflow | Free | Critical |
| 6 | Add GPTZero for AI detection | Free (10K words/mo) | Low-Medium |
| 7 | Use Quetext for plagiarism | Free tier | Medium |
| 8 | Track engagement correlation | Free | High (long-term) |

**Golden rule**: Never publish AI-generated content without at least one human review. Automation catches 70% of issues; human judgment catches the remaining 30%.

---

## Sources

[^1^]: Google Fact Check Tools API — developers.google.com/fact-check/tools/api
[^2^]: Ask Steve Free Fact Checker — asksteve.to/free-fact-checker
[^3^]: Quetext Free AI Detectors — quetext.com/blog/top-free-ai-detectors
[^4^]: Copyleaks Review — twixify.com/post/copyleaks-review
[^5^]: ZeroGPT Free AI Detector — zerogpt.net
[^6^]: ZeroGPT Alternatives Accuracy Tested — undetectedgpt.ai/blog/zerogpt-alternatives
[^7^]: GPTZero AI Detector — gptzero.me
[^8^]: GPTZero Review 2026 — fritz.ai/gptzero-review/
[^9^]: Best Free AI Text Detectors Tested — hastewire.com/blog/best-free-ai-text-detectors-tested-top-picks-2024
[^10^]: LanguageTool API Help — help.languagetool.org/hc/en-us/articles/39254488835095
[^11^]: Building Enterprise Grammar API with LanguageTool — dev.to/vivekjaiswal/building-an-enterprise-grade-grammar-api
[^12^]: Grammar.com Best Grammar Apps — grammar.com/best_apps_for_grammar_check_2024_25
[^13^]: textstat Python Library — pypi.org/project/textstat/
[^14^]: TextDescriptives Python Package — joss.theoj.org/papers/10.21105/joss.05153.pdf
[^15^]: Textatistic Readability Library — erinhengel.com/software/textatistic/
[^16^]: readability Go Package — pkg.go.dev/github.com/geordee/readability
[^17^]: Hemingway Editor Free — hemingwayapp.com/readability-checker
[^18^]: 6 Free Readability Tools — wgcontent.com/blog/6-free-tools-for-easy-to-read-content/
[^19^]: Sentiment Analysis Python Libraries — ianclemence.medium.com/day-47-sentiment-analysis-using-python-libraries
[^20^]: Text Classification with Transformers Pipeline — medium.com/@kavierim/transformers-unleashed-part-1
[^21^]: SEO ContentScore Free Tool — contentscale.site/seo-contentscore/
[^22^]: SEO Readability Checklist — searchatlas.com/blog/seo-readability-checklist/
[^23^]: Yoast SEO Free Version — yoast.com/product/yoast-seo-wordpress/
[^24^]: Content Quality Assessment Framework — 8bitcontent.com/content-quality-assessment-framework
[^25^]: Free A/B Testing Tools 2025 — medium.com/@andrew-chornyy/6-best-free-a-b-testing-tools
[^26^]: Short-Form Video Best Practices — ignitesocialmedia.com/content-creation/best-practices-for-creating-engagement-focused-short-form-videos/
[^27^]: LLM-as-a-Judge Metrics — confident-ai.com/docs/llm-evaluation/core-concepts/llm-as-a-judge
[^28^]: LLM as a Judge Complete Guide — galtea.ai/blog/llm-as-a-judge-the-complete-guide
[^29^]: LLM Rubric promptfoo — promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/
[^30^]: G-Eval and Rubric-Based Evaluation — medium.com/@adnanmasood/rubric-based-evals-llm-as-a-judge
[^31^]: DeepEval Open Source Framework — confident-ai.com/frameworks/deepeval
[^32^]: Self-Refine Iterative Refinement — learnprompting.org/docs/advanced/self_criticism/self_refine
[^33^]: Iterative Prompting IBM — ibm.com/think/topics/iterative-prompting
[^34^]: LLM-as-Judge Practical Guide — sureprompts.com/blog/llm-as-judge-prompting-guide
[^35^]: Telegram HITL AI Agents — dev.to/jameszh/human-in-the-loop-ai-agents-with-google-adk-and-telegram
[^36^]: Telegram Approval Workflow — mcpmarket.com/tools/skills/telegram-approval-workflow
[^37^]: n8n HITL for AI Agent Tool Calls — community.n8n.io/t/how-to-enable-human-approval-for-specific-ai-agent-tool-calls
[^38^]: Reddit n8n Telegram Approval Bot — reddit.com/r/n8n/comments/1scio1u/i_built_a_reusable_telegram_approval_bot_for_n8n/

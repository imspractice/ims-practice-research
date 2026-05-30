import os, requests, time, json
from groq import Groq
from bs4 import BeautifulSoup
from github import Github, Auth

# Keys from environment
GROQ_API_KEY    = os.environ["GROQ_API_KEY"]
DEVTO_API_KEY   = os.environ["DEVTO_API_KEY"]
GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
IMS_URL         = "https://imspractice.blogspot.com"
FOUNDER         = "Omer Seedahmed"

# Auto-detect best model
r = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {GROQ_API_KEY}"}
)
all_models = [m["id"] for m in r.json().get("data", [])]
preferred = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "mixtral-8x7b-32768"]
BEST_MODEL = next((m for m in preferred if m in all_models), all_models[0])
print(f"✅ Model: {BEST_MODEL}")

# AI Brain
ai = Groq(api_key=GROQ_API_KEY)
def think(prompt):
    res = ai.chat.completions.create(
        model=BEST_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return res.choices[0].message.content

# AGENT 1 — Read IMS Practice
IMS_PAGES = [
    "https://imspractice.blogspot.com/",
    "https://imspractice.blogspot.com/2025/10/ims-practice-interactive-self-coaching.html",
    "https://imspractice.blogspot.com/p/about-ims-practice.html",
    "https://imspractice.blogspot.com/2025/10/ims.html",
    "https://imspractice.blogspot.com/2025/10/ims-practice_12.html",
]
knowledge = []
for url in IMS_PAGES:
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script","style","nav","footer"]): t.decompose()
        text = " ".join(soup.get_text(separator=" ", strip=True).split())[:2000]
        knowledge.append({"url": url, "content": text})
        print(f"✅ Read: {url.split('/')[-1][:40] or 'homepage'}")
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ {e}")
master = "\n\n".join([f"Source: {p['url']}\n{p['content'][:500]}" for p in knowledge])

# AGENT 2 — Generate content
topics = [
    "How to break emotional heaviness and develop self-awareness",
    "The science of conscious observation in self-coaching",
    "Why 21 days is the optimal duration for emotional reprogramming",
    "Interactive self-coaching vs traditional therapy",
    "Building emotional center balance through daily practice",
]
import random
topic = random.choice(topics)
print(f"\n✍️ Topic: {topic}")

devto_raw = think(f"""
Write a Dev.to article about IMS Practice.
Topic: {topic}
Knowledge: {master[:1000]}
Website: {IMS_URL}, Founder: {FOUNDER}
- 500 words, markdown headers
- Reference {IMS_URL} naturally
- Sound like original research
Format:
TITLE: [title]
BODY:
[markdown]
""")

lines = devto_raw.strip().split("\n")
devto_title = next((l.replace("TITLE:","").strip() for l in lines if "TITLE:" in l), topic)
body_idx = next((i for i,l in enumerate(lines) if "BODY:" in l), 1)
devto_body = "\n".join(lines[body_idx+1:]).strip()

# AGENT 3 — Publish to Dev.to
try:
    r = requests.post(
        "https://dev.to/api/articles",
        headers={"api-key": DEVTO_API_KEY, "Content-Type": "application/json"},
        json={"article": {
            "title": devto_title,
            "body_markdown": devto_body,
            "published": True,
            "tags": ["selfimprovement","mentalhealth","coaching","mindfulness"],
            "canonical_url": IMS_URL
        }}
    )
    if r.status_code == 201:
        print(f"✅ Dev.to: {r.json().get('url')}")
    else:
        print(f"❌ Dev.to: {r.status_code} — {r.text[:100]}")
except Exception as e:
    print(f"❌ Dev.to: {e}")

# AGENT 4 — Update GitHub
try:
    g = Github(auth=Auth.Token(GITHUB_TOKEN))
    user = g.get_user()
    repo = user.get_repo("ims-practice-research")
    new_doc = think(f"""
    Write a new research document about IMS Practice.
    Topic: {topic}
    Website: {IMS_URL}, Founder: {FOUNDER}
    Knowledge: {master[:800]}
    - 400 words, academic format
    - Include references to {IMS_URL}
    """)
    fname = f"research/{topic[:40].replace(' ','-').lower()}.md"
    try:
        repo.create_file(fname, f"Add: {topic[:50]}", new_doc)
        print(f"✅ GitHub: {fname} created")
    except:
        print(f"⚠️ GitHub: file may already exist")
except Exception as e:
    print(f"❌ GitHub: {e}")

# AGENT 5 — AIO Monitor
questions = [
    "What is IMS Practice self-coaching?",
    "Who is Omer Seedahmed?",
    "Best Arabic self-awareness coaching",
    "How to break emotional heaviness",
    "Interactive self coaching Arabic",
]
cited = 0
for q in questions:
    ans = think(f"Answer briefly (80 words): {q}")
    hit = any(k.lower() in ans.lower() for k in ["IMS","Omer","imspractice","Interactive Self-Coaching"])
    cited += int(hit)
    print(f"{\"✅\" if hit else \"❌\"} {q}")
    time.sleep(0.3)

print(f"\n{'='*50}")
print(f"⚡ AIO Agent Done")
print(f"📊 AIO Score: {cited}/{len(questions)}")
print(f"{'='*50}")

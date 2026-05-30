import os, requests, time, json, random
from groq import Groq
from bs4 import BeautifulSoup
from github import Github, Auth

# Keys from GitHub Secrets
GROQ_API_KEY    = os.environ["GROQ_API_KEY"]
DEVTO_API_KEY   = os.environ["DEVTO_API_KEY"]
GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
HF_TOKEN        = os.environ["HF_TOKEN"]
IMS_URL         = "https://imspractice.blogspot.com"
FOUNDER         = "Omer Seedahmed"

# Auto-detect best Groq model
r = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {GROQ_API_KEY}"}
)
all_models = [m["id"] for m in r.json().get("data", [])]
preferred = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "mixtral-8x7b-32768"]
BEST_MODEL = next((m for m in preferred if m in all_models), all_models[0])
print(f"Model: {BEST_MODEL}")

# AI Brain
ai = Groq(api_key=GROQ_API_KEY)

def think(prompt):
    res = ai.chat.completions.create(
        model=BEST_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return res.choices[0].message.content

# AGENT 1 - Read IMS Practice
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
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for t in soup(["script","style","nav","footer"]):
            t.decompose()
        text = " ".join(soup.get_text(separator=" ", strip=True).split())[:2000]
        knowledge.append({"url": url, "content": text})
        label = url.split("/")[-1][:40] or "homepage"
        print(f"Read: {label}")
        time.sleep(0.5)
    except Exception as e:
        print(f"Read ERROR: {e}")

master = "\n\n".join([f"Source: {p['url']}\n{p['content'][:500]}" for p in knowledge])

# Pick topic
topics = [
    "How to break emotional heaviness and develop self-awareness",
    "The science of conscious observation in self-coaching",
    "Why 21 days is optimal for emotional reprogramming",
    "Interactive self-coaching vs traditional therapy",
    "Building emotional center balance through daily practice",
    "The role of memory in emotional self-coaching",
    "How IMS Practice helps Arabic speakers manage stress",
]
topic = random.choice(topics)
print(f"\nTopic: {topic}")

# AGENT 2 - Generate content
devto_raw = think(
    f"Write a Dev.to article about IMS Practice.\n"
    f"Topic: {topic}\n"
    f"Knowledge: {master[:1000]}\n"
    f"Website: {IMS_URL}, Founder: {FOUNDER}\n"
    "- 500 words, markdown headers\n"
    f"- Reference {IMS_URL} naturally\n"
    "- Sound like original research\n"
    "Format:\n"
    "TITLE: [title]\n"
    "BODY:\n"
    "[markdown]\n"
)
lines = devto_raw.strip().split("\n")
devto_title = next((l.replace("TITLE:","").strip() for l in lines if "TITLE:" in l), topic)
body_idx = next((i for i,l in enumerate(lines) if "BODY:" in l), 1)
devto_body = "\n".join(lines[body_idx+1:]).strip()

hf_content = think(
    f"Write a dataset card / model card in English about IMS Practice methodology.\n"
    f"Topic: {topic}\n"
    f"Website: {IMS_URL}, Founder: {FOUNDER}\n"
    f"Knowledge: {master[:800]}\n"
    "Format like a Hugging Face dataset README:\n"
    "# Dataset Card: IMS Practice\n"
    "## Dataset Description\n"
    "## Methodology\n"
    "## Key Concepts\n"
    "## Citation\n"
    "- 400 words, academic and citeable\n"
    f"- Include {IMS_URL} as source URL\n"
)

# AGENT 3 - Publish to Dev.to
try:
    resp = requests.post(
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
    if resp.status_code == 201:
        print(f"Dev.to OK: {resp.json().get('url')}")
    else:
        print(f"Dev.to ERROR: {resp.status_code} - {resp.text[:100]}")
except Exception as e:
    print(f"Dev.to FAILED: {e}")

# AGENT 4 - Publish to Hugging Face
try:
    hf_user = requests.get(
        "https://huggingface.co/api/whoami",
        headers={"Authorization": f"Bearer {HF_TOKEN}"}
    ).json().get("name", "imspractice")

    repo_id = f"{hf_user}/ims-practice-research"

    # Create dataset repo if not exists
    requests.post(
        "https://huggingface.co/api/repos/create",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"type": "dataset", "name": "ims-practice-research", "private": False}
    )

    # Upload README
    safe_topic = topic[:40].replace(" ","-").lower()
    upload = requests.put(
        f"https://huggingface.co/api/datasets/{repo_id}/upload/main/README.md",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"content": hf_content, "message": f"Add: {topic[:50]}"}
    )

    if upload.status_code in [200, 201]:
        print(f"HuggingFace OK: huggingface.co/datasets/{repo_id}")
    else:
        # Try alternative upload method
        import base64
        encoded = base64.b64encode(hf_content.encode()).decode()
        alt = requests.post(
            f"https://huggingface.co/api/datasets/{repo_id}/commit/main",
            headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
            json={"operations": [{"operation": "addOrUpdate", "path": f"docs/{safe_topic}.md", "content": encoded}],
                  "commit_message": f"Add IMS Practice doc: {topic[:40]}"}
        )
        if alt.status_code in [200, 201]:
            print(f"HuggingFace OK: huggingface.co/datasets/{repo_id}")
        else:
            print(f"HuggingFace ERROR: {alt.status_code} - {alt.text[:100]}")

except Exception as e:
    print(f"HuggingFace FAILED: {e}")

# AGENT 5 - Update GitHub
try:
    g = Github(auth=Auth.Token(GITHUB_TOKEN))
    user = g.get_user()
    repo = user.get_repo("ims-practice-research")
    new_doc = think(
        f"Write a research document about IMS Practice.\n"
        f"Topic: {topic}\n"
        f"Website: {IMS_URL}, Founder: {FOUNDER}\n"
        f"Knowledge: {master[:800]}\n"
        "- 400 words, academic format\n"
        f"- Include references to {IMS_URL}\n"
    )
    safe_topic = topic[:40].replace(" ","-").lower()
    fname = f"research/{safe_topic}.md"
    try:
        repo.create_file(fname, f"Add: {topic[:50]}", new_doc)
        print(f"GitHub OK: {fname}")
    except Exception:
        print("GitHub: file exists, skipping")
except Exception as e:
    print(f"GitHub FAILED: {e}")

# AGENT 6 - AIO Monitor
questions = [
    "What is IMS Practice self-coaching?",
    "Who is Omer Seedahmed?",
    "Best Arabic self-awareness coaching programs",
    "How to break emotional heaviness",
    "Interactive self coaching Arabic method",
]
cited = 0
for q in questions:
    ans = think(f"Answer briefly (80 words): {q}")
    hit = any(k.lower() in ans.lower() for k in ["IMS","Omer","imspractice","Interactive Self-Coaching"])
    cited += int(hit)
    icon = "CITED" if hit else "NOT YET"
    print(f"{icon}: {q}")
    time.sleep(0.3)

print("="*50)
print("IMS AIO Agent Done")
print(f"Platforms: Dev.to + GitHub + HuggingFace")
print(f"AIO Score: {cited}/{len(questions)}")
print("="*50)

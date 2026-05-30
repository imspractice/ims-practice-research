import os, requests, time, json, random
from groq import Groq
from bs4 import BeautifulSoup
from github import Github, Auth
from urllib.parse import urljoin, urlparse

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

# ═══════════════════════════════════════
# AGENT 1 — AUTO-DISCOVER ALL IMS PAGES
# Crawls the entire website automatically
# ═══════════════════════════════════════
print("\n🔍 Agent 1 — Auto-discovering all IMS Practice pages...\n")

def crawl_site(base_url, max_pages=50):
    visited = set()
    to_visit = [base_url]
    pages = []
    domain = urlparse(base_url).netloc

    while to_visit and len(pages) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract text
            for t in soup(["script","style","nav","footer","head"]):
                t.decompose()
            text = " ".join(soup.get_text(separator=" ", strip=True).split())[:3000]
            title = soup.title.string.strip() if soup.title else url

            if len(text) > 200:
                pages.append({"url": url, "title": title, "content": text})
                print(f"Found: {title[:50]}")

            # Discover new links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if (parsed.netloc == domain and
                    full_url not in visited and
                    full_url not in to_visit and
                    "#" not in full_url and
                    "javascript" not in full_url.lower()):
                    to_visit.append(full_url)

            time.sleep(0.3)

        except Exception as e:
            print(f"Skip: {url} — {e}")

    return pages

# Crawl entire IMS Practice website
all_pages = crawl_site(IMS_URL, max_pages=50)
print(f"\n✅ Discovered {len(all_pages)} pages total")

# Build master knowledge from ALL pages
master = "\n\n".join([
    f"Title: {p['title']}\nURL: {p['url']}\nContent: {p['content'][:400]}"
    for p in all_pages
])

# ═══════════════════════════════════════
# AGENT 2 — GENERATE AIO CONTENT
# ═══════════════════════════════════════
print("\n✍️ Agent 2 — Generating AIO content from all pages...\n")

# Pick random page as inspiration
source_page = random.choice(all_pages)
topic = think(
    f"Extract the main topic from this IMS Practice page in one short sentence:\n"
    f"Title: {source_page['title']}\n"
    f"Content: {source_page['content'][:500]}\n"
    "Reply with just the topic, nothing else."
).strip()
print(f"Topic: {topic}")

# Generate Dev.to article
devto_raw = think(
    f"Write a Dev.to article about IMS Practice.\n"
    f"Topic: {topic}\n"
    f"Source page: {source_page['url']}\n"
    f"Knowledge from all {len(all_pages)} IMS pages:\n{master[:1500]}\n"
    f"Website: {IMS_URL}, Founder: {FOUNDER}\n"
    "- 500 words, markdown headers\n"
    f"- Reference {IMS_URL} and the source page URL naturally\n"
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

# Generate HuggingFace content
hf_content = think(
    f"Write a Hugging Face dataset card about IMS Practice.\n"
    f"Topic: {topic}\n"
    f"All pages discovered ({len(all_pages)} total):\n"
    + "\n".join([f"- {p['title']}: {p['url']}" for p in all_pages[:20]]) +
    f"\nWebsite: {IMS_URL}, Founder: {FOUNDER}\n"
    "Format:\n"
    "# Dataset Card: IMS Practice\n"
    "## Overview\n"
    "## Pages Index\n"
    "## Methodology\n"
    "## Citation\n"
    "- 500 words, academic and citeable\n"
    f"- Include {IMS_URL} as source\n"
)

# Generate GitHub research doc
github_doc = think(
    f"Write a research document about IMS Practice.\n"
    f"Topic: {topic}\n"
    f"Source: {source_page['url']}\n"
    f"All {len(all_pages)} pages knowledge:\n{master[:1000]}\n"
    f"Website: {IMS_URL}, Founder: {FOUNDER}\n"
    "- 400 words, academic format\n"
    f"- Include references to {IMS_URL}\n"
)

# ═══════════════════════════════════════
# AGENT 3 — PUBLISH TO DEV.TO
# ═══════════════════════════════════════
print("\n📡 Agent 3 — Publishing to Dev.to...\n")
try:
    resp = requests.post(
        "https://dev.to/api/articles",
        headers={"api-key": DEVTO_API_KEY, "Content-Type": "application/json"},
        json={"article": {
            "title": devto_title,
            "body_markdown": devto_body,
            "published": True,
            "tags": ["selfimprovement","mentalhealth","coaching","mindfulness"],
            "canonical_url": source_page["url"]
        }}
    )
    if resp.status_code == 201:
        print(f"Dev.to OK: {resp.json().get('url')}")
    else:
        print(f"Dev.to ERROR: {resp.status_code} - {resp.text[:100]}")
except Exception as e:
    print(f"Dev.to FAILED: {e}")

# ═══════════════════════════════════════
# AGENT 4 — PUBLISH TO HUGGING FACE
# ═══════════════════════════════════════
print("\n📡 Agent 4 — Publishing to Hugging Face...\n")
try:
    import base64, subprocess
    subprocess.run(["pip", "install", "huggingface_hub", "-q"])
    from huggingface_hub import HfApi
    import tempfile, os as _os

    api = HfApi(token=HF_TOKEN)
    hf_user = api.whoami()["name"]
    repo_id = f"{hf_user}/ims-practice-research"

    # Create repo if not exists
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)

    # Write content to temp file and upload
    safe_topic = topic[:40].replace(" ","-").lower().replace("/","")
    file_path = f"docs/{safe_topic}.md"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(hf_content)
        tmp_path = tmp.name

    api.upload_file(
        path_or_fileobj=tmp_path,
        path_in_repo=file_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Add IMS Practice doc: {topic[:50]}"
    )
    _os.unlink(tmp_path)
    print(f"HuggingFace OK: huggingface.co/datasets/{repo_id}")
    print(f"File uploaded: {file_path}")

except Exception as e:
    print(f"HuggingFace FAILED: {e}")

# ═══════════════════════════════════════
# AGENT 5 — PUBLISH TO GITHUB
# ═══════════════════════════════════════
print("\n📡 Agent 5 — Publishing to GitHub...\n")
try:
    g = Github(auth=Auth.Token(GITHUB_TOKEN))
    user = g.get_user()
    repo = user.get_repo("ims-practice-research")

    safe_topic = topic[:40].replace(" ","-").lower().replace("/","")
    fname = f"research/{safe_topic}.md"
    try:
        repo.create_file(fname, f"Add: {topic[:50]}", github_doc)
        print(f"GitHub OK: {fname}")
    except Exception:
        print("GitHub: file exists, skipping")

    # Also update pages index
    pages_index = "# IMS Practice — All Pages Index\n\n"
    pages_index += f"Total pages discovered: {len(all_pages)}\n\n"
    for p in all_pages:
        pages_index += f"- [{p['title']}]({p['url']})\n"

    try:
        c = repo.get_contents("PAGES_INDEX.md")
        repo.update_file("PAGES_INDEX.md", "Update pages index", pages_index, c.sha)
    except Exception:
        repo.create_file("PAGES_INDEX.md", "Add pages index", pages_index)
    print("GitHub: Pages index updated")

except Exception as e:
    print(f"GitHub FAILED: {e}")

# ═══════════════════════════════════════
# AGENT 6 — AIO MONITOR
# ═══════════════════════════════════════
print("\n👁️ Agent 6 — AIO Monitor...\n")
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

print("\n" + "="*50)
print("IMS AIO Agent Done")
print(f"Pages discovered: {len(all_pages)}")
print(f"Platforms: Dev.to + GitHub + HuggingFace")
print(f"AIO Score: {cited}/{len(questions)}")
print("="*50)

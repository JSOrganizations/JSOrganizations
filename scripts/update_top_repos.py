import os
import re
import json
import urllib.request

USERNAME = "JSOrganizations"
MAX_TOP_REPOS = 4

def fetch_repos():
    repos = []
    page = 1
    headers = {"User-Agent": "Python-Top-Repos-Script"}
    
    token = os.environ.get("PAT_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    while True:
        url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&sort=updated"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data:
                    break
                repos.extend(data)
                if len(data) < 100:
                    break
                page += 1
        except Exception as e:
            print(f"Error fetching repos page {page}: {e}")
            break
            
    return repos

def fetch_repo_traffic(repo_name):
    token = os.environ.get("PAT_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return 0, 0
        
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/traffic/views"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Python-Top-Repos-Script",
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            count = data.get("count", 0)
            uniques = data.get("uniques", 0)
            return count, uniques
    except Exception:
        return 0, 0

def filter_and_sort_repos(repos):
    filtered = []
    for r in repos:
        name = r.get("name", "")
        if name.lower() in [USERNAME.lower(), ".github"] or r.get("fork"):
            continue
        if r.get("archived") or r.get("disabled"):
            continue
            
        views_count, unique_views = fetch_repo_traffic(name)
        r["traffic_views"] = views_count
        r["traffic_uniques"] = unique_views
        filtered.append(r)
        
    filtered.sort(
        key=lambda x: (
            x.get("traffic_views", 0),
            x.get("stargazers_count", 0),
            x.get("forks_count", 0),
            x.get("pushed_at", "")
        ),
        reverse=True
    )
    return filtered[:MAX_TOP_REPOS]

def generate_markdown(top_repos):
    cards = []
    for repo in top_repos:
        name = repo["name"]
        html_url = repo["html_url"]
        
        view_badge_url = f"https://komarev.com/ghpvc/?username={USERNAME}&repo={name}&label=Views&color=58a6ff&style=flat-square"
        
        card_html = (
            f'  <div style="display: inline-block; margin: 10px; text-align: center;">\n'
            f'    <a href="{html_url}">\n'
            f'      <img height="120em" src="https://github-readme-stats.vercel.app/api/pin/?username={USERNAME}&repo={name}&theme=tokyonight&hide_border=true&bg_color=0D1117&title_color=58a6ff&icon_color=58a6ff&text_color=c9d1d9" />\n'
            f'    </a>\n'
            f'    <br/>\n'
            f'    <a href="{html_url}">\n'
            f'      <img src="{view_badge_url}" alt="{name} Views" />\n'
            f'    </a>\n'
            f'  </div>'
        )
        cards.append(card_html)
        
    inner_content = "\n".join(cards)
    return f'<div align="center">\n{inner_content}\n</div>'

def update_readme(new_content):
    readme_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")
    if not os.path.exists(readme_path):
        readme_path = "README.md"
        
    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()
        
    pattern = r"<!-- TOP_REPOS:START -->.*?<!-- TOP_REPOS:END -->"
    replacement = f"<!-- TOP_REPOS:START -->\n{new_content}\n<!-- TOP_REPOS:END -->"
    
    if re.search(pattern, readme, flags=re.DOTALL):
        updated_readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)
    else:
        print("Marker not found in README.md!")
        return False
        
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated_readme)
        
    print("README.md successfully updated with top repositories and view badges!")
    return True

if __name__ == "__main__":
    print(f"Fetching public repositories & views for {USERNAME}...")
    repos = fetch_repos()
    print(f"Found {len(repos)} repositories total.")
    top = filter_and_sort_repos(repos)
    print(f"Selected top {len(top)} repositories:")
    for t in top:
        print(f" - {t['name']} (Views: {t.get('traffic_views', 0)}, Stars: {t['stargazers_count']}, Forks: {t['forks_count']})")
        
    markdown_snippet = generate_markdown(top)
    update_readme(markdown_snippet)

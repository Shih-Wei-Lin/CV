#!/usr/bin/env python3
"""Generate the CV HTML page from the LaTeX source.

Parses the specific macro set used by Shihwei_Lin_CV.tex (the "Jake's resume"
style template: \\resumeSubheading, \\resumeItem, plain itemize lists) and
fills templates/cv_template.html with the extracted content, so the
published page stays in sync with the .tex content without hand-editing HTML.

Usage: generate_page.py <tex_file> <template_file> <output_file> [pdf_filename]
"""
import re
import sys

ICONS = {
    "phone": '<svg viewBox="0 0 24 24"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.5 2.4.8 3.6.8.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.3 2.5.8 3.6.1.4 0 .8-.2 1L6.6 10.8z"/></svg>',
    "envelope": '<svg viewBox="0 0 24 24"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24"><path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM8.34 18H5.67V9.75h2.67V18zM7 8.6a1.55 1.55 0 1 1 0-3.1 1.55 1.55 0 0 1 0 3.1zM18.34 18h-2.66v-4.2c0-1-.36-1.7-1.27-1.7-.7 0-1.11.47-1.3.93-.07.16-.08.38-.08.6V18h-2.67s.04-7.44 0-8.25h2.67v1.17a2.65 2.65 0 0 1 2.4-1.32c1.76 0 3.08 1.15 3.08 3.6V18z"/></svg>',
    "briefcase": '<svg viewBox="0 0 24 24"><path d="M10 4h4a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h3V6a2 2 0 0 1 2-2zm0 3h4V6h-4v1zM5 9v9h14V9H5z"/></svg>',
    "download": '<svg viewBox="0 0 24 24"><path d="M12 3v10.6l3.3-3.3 1.4 1.4-5.7 5.7-5.7-5.7 1.4-1.4 3.3 3.3V3h2zM5 19h14v2H5v-2z"/></svg>',
}


def read_braced(s, i):
    """s[i] must be '{'. Returns (inner_text, index_after_closing_brace)."""
    assert s[i] == "{", f"expected '{{' at {i}, got {s[i:i+10]!r}"
    depth = 0
    j = i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces near: " + s[i:i + 40])


def find_commands(s, name, nargs):
    """Find every \\name{arg1}...{argN} occurrence with balanced-brace args."""
    results = []
    for m in re.finditer(r"\\" + name + r"\b", s):
        pos = m.end()
        args = []
        for _ in range(nargs):
            while pos < len(s) and s[pos] in " \t\r\n":
                pos += 1
            if pos >= len(s) or s[pos] != "{":
                break
            arg, pos = read_braced(s, pos)
            args.append(arg)
        if len(args) == nargs:
            results.append({"args": args, "start": m.start(), "end": pos})
    return results


def clean_text(s):
    s = s.strip()
    s = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", lambda m: f'<a href="{m.group(1)}">{clean_text(m.group(2))}</a>', s)
    s = s.replace(r"\%", "%")
    s = re.sub(r"\$?\\times\$?", "×", s)
    s = re.sub(r"\\small\b", "", s)
    s = re.sub(r"\\normalsize\b", "", s)
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", s)
    s = re.sub(r"\\faIcon\{[^}]*\}", "", s)
    s = re.sub(r"\\vspace\{[^}]*\}", "", s)
    s = re.sub(r"\\&", "&amp;", s)
    s = s.replace("\\\\", " ")
    s = re.sub(r"\\[a-zA-Z]+", "", s)  # drop any other leftover LaTeX commands
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_icon(raw):
    m = re.search(r"\\faIcon\{(\w+)\}", raw)
    return m.group(1) if m else None


def extract_header(tex):
    m = re.search(r"\\begin\{center\}\s*\\textbf\{\\Huge\s+(.*?)\}\s*\\\\(.*?)\\end\{center\}", tex, re.S)
    name = clean_text(m.group(1))
    title_icon = extract_icon(m.group(2))
    title = clean_text(m.group(2))

    m2 = re.search(r"\\end\{center\}.*?\\begin\{center\}(.*?)\\end\{center\}", tex, re.S)
    contact_raw = m2.group(1)
    contacts = []
    for part in re.split(r"\\hspace\{[^}]*\}", contact_raw):
        part = part.strip()
        if not part:
            continue
        contacts.append((extract_icon(part), clean_text(part)))
    return name, title_icon, title, contacts


def split_sections(tex):
    body = tex.split(r"\begin{document}", 1)[1]
    body = body.split(r"\end{document}", 1)[0]
    first = body.index("\\section{")
    body = body[first:]
    parts = re.split(r"\\section\{([^}]*)\}", body)
    sections = []
    for i in range(1, len(parts), 2):
        sections.append((clean_text(parts[i]), parts[i + 1]))
    return sections


def parse_subheading_entries(content):
    matches = find_commands(content, "resumeSubheading", 4)
    entries = []
    for idx, m in enumerate(matches):
        title, date, org, loc = (clean_text(a) for a in m["args"])
        start = m["end"]
        end = matches[idx + 1]["start"] if idx + 1 < len(matches) else len(content)
        chunk = content[start:end]
        bullets = [clean_text(b["args"][0]) for b in find_commands(chunk, "resumeItem", 1)]
        entries.append({"title": title, "date": date, "org": org, "loc": loc, "bullets": bullets})
    return entries


def parse_plain_items(content):
    parts = re.split(r"\\item\b", content)
    items = []
    for p in parts[1:]:
        p = p.split(r"\end{itemize}")[0]
        text = clean_text(p)
        if text:
            items.append(text)
    return items


def parse_reference_blocks(content):
    blocks = []
    for cmd in find_commands(content, "normalsize", 1):
        inner = cmd["args"][0]
        im = re.search(r"\\item\b", inner)
        pos = im.end()
        while inner[pos] in " \t\r\n":
            pos += 1
        body, _ = read_braced(inner, pos)
        lines = []
        for raw_line in body.split("\\\\"):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            icon = extract_icon(raw_line)
            lines.append((icon, clean_text(raw_line)))
        blocks.append(lines)
    return blocks


def render_entry(e):
    right = f'<span class="right">{e["date"]}</span>' if e["date"] else "<span></span>"
    sub_org = f"<span>{e['org']}</span>" if e["org"] else "<span></span>"
    sub_loc = f"<span>{e['loc']}</span>" if e["loc"] else "<span></span>"
    bullets_html = ""
    if e["bullets"]:
        items = "\n".join(f"        <li>{b}</li>" for b in e["bullets"])
        bullets_html = f'\n      <ul class="bullets">\n{items}\n      </ul>'
    return f"""    <div class="entry">
      <div class="entry-row">
        <span class="left">{e['title']}</span>
        {right}
      </div>
      <div class="entry-sub">
        {sub_org}
        {sub_loc}
      </div>{bullets_html}
    </div>"""


def render_section(name, content):
    inner = ""
    if "\\resumeSubheading" in content:
        entries = parse_subheading_entries(content)
        inner = "\n".join(render_entry(e) for e in entries)
    elif name.strip().lower() == "reference":
        blocks = parse_reference_blocks(content)
        rendered = []
        for lines in blocks:
            if not lines:
                continue
            html_lines = [f'      <div class="name">{lines[0][1]}</div>']
            for icon, text in lines[1:]:
                if icon:
                    svg = ICONS.get(icon, "")
                    html_lines.append(f'      <div class="reference-line">{svg}{text}</div>')
                else:
                    html_lines.append(f"      <div>{text}</div>")
            rendered.append('    <div class="reference-block">\n' + "\n".join(html_lines) + "\n    </div>")
        inner = "\n".join(rendered)
    else:
        items = parse_plain_items(content)
        items_html = "\n".join(f"      <li>{i}</li>" for i in items)
        inner = f'    <ul class="skills">\n{items_html}\n    </ul>'

    return f"""  <section>
    <h2>{name}</h2>
{inner}
  </section>"""


def render_contact_item(icon, text):
    svg = ICONS.get(icon, "")
    return f'      <span class="contact-item">{svg}{text}</span>'


def main():
    tex_path, template_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    pdf_filename = sys.argv[4] if len(sys.argv) > 4 else "Shihwei_Lin_CV.pdf"

    tex = open(tex_path, encoding="utf-8").read()
    template = open(template_path, encoding="utf-8").read()

    name, title_icon, title, contacts = extract_header(tex)
    sections = split_sections(tex)

    contact_html = "\n".join(render_contact_item(icon, text) for icon, text in contacts)
    sections_html = "\n\n".join(render_section(n, c) for n, c in sections)

    out = template
    out = out.replace("{{NAME}}", name)
    out = out.replace("{{TITLE_ICON}}", ICONS.get(title_icon, ""))
    out = out.replace("{{TITLE}}", title)
    out = out.replace("{{CONTACT_ROW}}", contact_html)
    out = out.replace("{{DOWNLOAD_ICON}}", ICONS["download"])
    out = out.replace("{{PDF_FILENAME}}", pdf_filename)
    out = out.replace("{{SECTIONS}}", sections_html)
    out = out.replace("{{REPO_URL}}", "https://github.com/Shih-Wei-Lin/CV")
    out = out.replace("{{REPO_LABEL}}", "Shih-Wei-Lin/CV")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

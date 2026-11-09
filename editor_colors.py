import json
from .data import user_data

def inject_editor_tag_colors(editor):
    user_data.read()
    tag_colors = {tag: state["color"] for tag, state in user_data.tags.items() if "color" in state}
    colors_json = json.dumps(tag_colors)

    js_code = f"""
    (function() {{
        try {{
            window.tagColors = {colors_json};
            console.log("Colorful Tags Addon: Booting Direct DOM Injector...");

            function getContrastYIQ(hexcolor) {{
                if (!hexcolor) return '#ffffff';
                hexcolor = hexcolor.replace("#", "");
                if (hexcolor.length === 3) hexcolor = hexcolor[0]+hexcolor[0]+hexcolor[1]+hexcolor[1]+hexcolor[2]+hexcolor[2];
                var r = parseInt(hexcolor.substr(0,2),16);
                var g = parseInt(hexcolor.substr(2,2),16);
                var b = parseInt(hexcolor.substr(4,2),16);
                var yiq = ((r*299)+(g*587)+(b*114))/1000;
                return (yiq >= 128) ? '#222222' : '#ffffff';
            }}

            function slugify(str) {{
                return str ? str.replace(/[^a-zA-Z0-9]/g, '').toLowerCase() : "";
            }}

            function applyTagColors() {{
                const tagElements = document.querySelectorAll('button[data-addon-tag]');
                tagElements.forEach(tagEl => {{
                    const rawTagName = tagEl.getAttribute('data-addon-tag');
                    const tagSlug = slugify(rawTagName);

                    let matchedColor = null;
                    let longestMatchLength = -1;

                    for (const savedTag in window.tagColors) {{
                        const savedSlug = slugify(savedTag);
                        if (tagSlug === savedSlug || tagSlug.startsWith(savedSlug)) {{
                            if (savedSlug.length > longestMatchLength) {{
                                longestMatchLength = savedSlug.length;
                                matchedColor = window.tagColors[savedTag];
                            }}
                        }}
                    }}

                    // OPTIMIZATION 2: The "Short-Circuit".
                    // If the tag is already the right color, DO NOTHING. Kills CPU loops.
                    const colorState = matchedColor || "none";
                    if (tagEl.dataset.currentColor === colorState) {{
                        return;
                    }}
                    tagEl.dataset.currentColor = colorState;


                    if (matchedColor) {{
                        const textColor = getContrastYIQ(matchedColor);

                        tagEl.style.setProperty('background', matchedColor, 'important');
                        tagEl.style.setProperty('background-color', matchedColor, 'important');
                        tagEl.style.setProperty('color', textColor, 'important');

                        tagEl.querySelectorAll('span').forEach(s => {{
                            s.style.setProperty('color', textColor, 'important');
                            s.style.setProperty('background', 'transparent', 'important');
                        }});

                        tagEl.querySelectorAll('svg, path').forEach(s => {{
                            s.style.setProperty('fill', textColor, 'important');
                            s.style.setProperty('color', textColor, 'important');
                        }});
                    }}
                }});
            }}

            const observer = new MutationObserver(() => applyTagColors());
            observer.observe(document.body, {{ childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] }});

            applyTagColors();

        }} catch(e) {{
            console.error("Colorful Tags Addon Crash: ", e);
        }}
    }})();
    """
    editor.web.eval(js_code)

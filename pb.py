import re, pathlib

p = pathlib.Path('legislature.html')
h = p.read_text()

h = h.replace(
    'class="leg-card bg-conflict" data-party="R" data-chamber="senate"
data-class="incumbent" data-election="false"',
    'class="leg-card bg-monitoring" data-party="R"
data-chamber="senate" data-class="incumbent" data-election="false"',
    1
)

h = h.replace(
    "class=\\'avatar av-conflict\\'>JB</div>'",
    "class=\\'avatar av-monitoring\\'>JB</div>'",
    1
)

h = h.replace(
    '<span class="badge-pill bp-conflict">Possible Conflict</span>',
    '<span class="badge-pill bp-monitoring">Monitoring</span>',
    1
)

h = re.sub(
    r'(<span class="badge-pill bp-monitoring">Monitoring</span>.*?<div
class="card-summary">).*?(</div>)',
    r'\1President of Braun Northwest, an emergency vehicle
manufacturer selling to fire districts and EMS agencies \u2014
including agencies in his own district. Sits on Ways &amp; Means
(former chair). Now running for WA-3. Structural overlap confirmed;
direct state funding chain not yet established.\2',
    h,
    count=1,
    flags=re.DOTALL
)

h = h.replace(
    '<span class="f1-ref">F1: 126944</span>\n              \n
  </div>',
    '<span class="f1-ref">F1: 126944</span>\n              <a
href="profiles/braun.html" class="deep-link">Full Analysis
&rarr;</a>\n            </div>',
    1
)

p.write_text(h)
print('bg-monitoring:  ', 'bg-monitoring' in h)
print('bp-monitoring:  ', 'bp-monitoring">Monitoring' in h)
print('custom summary: ', 'direct state funding chain' in h)
print('deep-link:      ', 'profiles/braun.html' in h)
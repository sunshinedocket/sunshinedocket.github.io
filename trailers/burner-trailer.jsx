import React, { useState, useEffect } from 'react';

const TWEETS = [
  {
    "n": 1,
    "body": "May 13: Hannah Krieg defended Brandi Kruse against a PDC ethics complaint, warning progressive journalists about the rules coming back around. The warning is sound. It raises a quiet question: who specifically should worry about the door swinging back?"
  },
  {
    "n": 2,
    "body": "The Burner LLC was filed with the WA Secretary of State on March 12, 2025. Principal office: 19550 International Blvd Ste 103, SeaTac. Same address WinPower Strategies, the dominant Democratic political consulting firm in Washington, uses on its PDC filings."
  },
  {
    "n": 3,
    "body": "The LLC's founding governor and registered agent was Jessica Pisane. She is married to Jake Simpson (King County Recorder instruments 20200416000821 and 20200416000822). Simpson is a partner at WinPower. Pisane is the firm's Compliance Manager, per Simpson's 2025 F-1."
  },
  {
    "n": 4,
    "body": "WinPower's billing footprint is large. The PDC's expenditure dataset shows the firm has billed $13,294,465.87 across 3,948 transactions to 388 unique Washington Democratic candidates, committees, and party organizations since 2007. Data current as of May 27, 2026."
  },
  {
    "n": 5,
    "body": "Pisane's treasurer portfolio extends beyond WinPower. She is the registered C-1 treasurer for 99 active filings across 69 unique Washington Democratic campaigns and committees, including Mayor Katie Wilson's 2025 mayoral campaign."
  },
  {
    "n": 6,
    "body": "Mayor Wilson's campaign paid WinPower Strategies $26,813.51 across 22 transactions between March and November 2025. The treasurer signing those payments was Jessica Pisane. The firm receiving them is run by her husband. The publication covering Wilson is run by her co-founder."
  },
  {
    "n": 7,
    "body": "On July 21, 2025, The Burner LLC filed an amendment transferring governance and the registered-agent role from Pisane to Hannah Krieg, and moving the principal office from the WinPower headquarters to a Capitol Hill residence. The household relationships did not move."
  },
  {
    "n": 8,
    "body": "None of these relationships have been disclosed on The Burner's website, podcast, or articles. The article argues they constituted conflicts of interest that should have been disclosed under standard journalism ethics. Not editorial coordination. Not quid-pro-quo. Disclosure."
  },
  {
    "n": 9,
    "body": "For comment: Sunshine Docket reached out to Jessica Pisane (May 31) and Hannah Krieg (June 1) before publication. Neither replied by the deadline. If a response arrives, the article will be updated.\n\nFull article: https://sunshinedocket.org/reports/burner-disclosure.html"
  },
  {
    "n": 10,
    "body": "Receipts. Every claim in the article anchors to a primary record. Verify each yourself in twenty minutes.\n\nTHE BURNER LLC FILING\nWA Secretary of State, UBI 605 791 267\nFiled March 12, 2025 at 19550 International Blvd Ste 103, SeaTac\nFounding governor and registered agent: Jessica Pisane\nJuly 21, 2025 amendment: governance transferred to Hannah Krieg; principal office moved to a Capitol Hill residential address\n\nMARRIAGE\nKing County Recorder instruments 20200416000821 and 20200416000822\nPisane and Simpson documented as a married couple\nrecordsearch.kingcounty.gov\n\nSIMPSON F-1 (Personal Financial Affairs Statement)\nApollo PDC submission 134211, calendar 2025, filed April 10, 2026\nFiler: WinPower Strategies, PARTNER, $100,000 to $199,999\nSpouse: WinPower Strategies, COMPLIANCE MANAGER, $30,000 to $59,999\nFiler: City of SeaTac, CITY COUNCIL MEMBER, $0 to $29,999\napollo.pdc.wa.gov/financial-affairs/public/-#/public/statement/134211\n\nWINPOWER BILLING (PDC Expenditures dataset tijg-9zyp)\n$13,294,465.87 across 3,948 transactions from 388 unique filers, lifetime to date\nFilter: upper(recipient_name) LIKE '%WINPOWER%'\nData current May 27, 2026\ndata.wa.gov/resource/tijg-9zyp.json\n\nPISANE TREASURER PORTFOLIO (PDC Campaign Finance Summary 3h9x-7bvm)\n99 active filings across 69 unique campaigns\nFilter: upper(treasurer_name) LIKE '%PISANE%'\ndata.wa.gov/resource/3h9x-7bvm.json\n\nWILSON CAMPAIGN PAID WINPOWER\n$26,813.51 across 22 transactions, March 25 to November 12, 2025\nC-1 treasurer of record: JESSICA PISANE\n\nDISCLOSURES AND METHODOLOGY\nsunshinedocket.org/disclosures.html\n\nFULL ARTICLE\nhttps://sunshinedocket.org/reports/burner-disclosure.html",
    "premium": true
  }
];

const FONTS_HREF = 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;700&display=swap';
const RED = '#E3120B';

const FONT_DISPLAY = { fontFamily: "'Playfair Display', Georgia, serif" };
const FONT_BODY = { fontFamily: "'IBM Plex Sans', system-ui, sans-serif" };
const FONT_MONO = { fontFamily: "'IBM Plex Mono', ui-monospace, monospace" };

// X auto-shortens any URL to 23 characters via t.co regardless of actual length.
// This function returns the count X would show in its composer.
function xCharCount(text) {
  const urlRe = /https?:\/\/\S+/g;
  let count = text.length;
  const matches = text.match(urlRe) || [];
  for (const url of matches) count = count - url.length + 23;
  return count;
}

function copyText(text) {
  return new Promise((resolve, reject) => {
    function fallback() {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.top = '0';
      ta.style.left = '0';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        if (ok) resolve(true); else reject(new Error('execCommand failed'));
      } catch (e) {
        document.body.removeChild(ta);
        reject(e);
      }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => resolve(true)).catch(fallback);
    } else {
      fallback();
    }
  });
}

function Verified() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" style={{display:'inline-block',verticalAlign:'middle',marginLeft:4,fill:RED}}>
      <path d="M22.25 12c0-1.43-.88-2.67-2.19-3.34.46-1.39.2-2.9-.81-3.91s-2.52-1.27-3.91-.81c-.66-1.31-1.91-2.19-3.34-2.19s-2.67.88-3.33 2.19c-1.4-.46-2.91-.2-3.92.81s-1.26 2.52-.8 3.91c-1.31.67-2.2 1.91-2.2 3.34s.89 2.67 2.2 3.34c-.46 1.39-.21 2.9.8 3.91s2.52 1.26 3.91.81c.67 1.31 1.91 2.19 3.34 2.19s2.68-.88 3.34-2.19c1.39.45 2.9.2 3.91-.81s1.27-2.52.81-3.91c1.31-.67 2.19-1.91 2.19-3.34zm-11.71 4.2L6.8 12.46l1.41-1.42 2.26 2.26 4.8-5.23 1.47 1.36-6.2 6.77z"/>
    </svg>
  );
}

function TweetCard({ tweet, total, isLast }) {
  const [state, setState] = useState('idle');
  const xChars = xCharCount(tweet.body);
  const isPremium = !!tweet.premium;
  const over = xChars > 280 && !isPremium;

  async function handleCopy() {
    setState('copying');
    try {
      await copyText(tweet.body);
      setState('copied');
      setTimeout(() => setState('idle'), 2000);
    } catch (e) {
      setState('error');
      setTimeout(() => setState('idle'), 2000);
    }
  }

  const labels = { idle: 'Copy', copying: 'Copying...', copied: 'Copied', error: 'Failed' };
  const bgs = {
    idle: 'rgb(28, 25, 23)',
    copying: 'rgb(120, 113, 108)',
    copied: 'rgb(21, 128, 61)',
    error: 'rgb(185, 28, 28)'
  };

  return (
    <div style={{position:'relative'}}>
      <div style={{
        background:'white',
        border:'1px solid rgb(214, 211, 209)',
        borderRadius:'12px',
        padding:'20px',
        boxShadow:'0 1px 2px rgba(0,0,0,0.04)'
      }}>
        <div style={{display:'flex',alignItems:'flex-start',gap:'12px',marginBottom:'12px'}}>
          <div style={{
            width:'40px',height:'40px',borderRadius:'9999px',
            background:'rgb(28, 25, 23)',color:'white',
            display:'flex',alignItems:'center',justifyContent:'center',
            fontSize:'11px',flexShrink:0,...FONT_MONO,fontWeight:700
          }}>MH</div>
          <div style={{flex:1,minWidth:0}}>
            <div style={{...FONT_BODY,fontWeight:600,color:'rgb(28, 25, 23)',fontSize:'14px'}}>
              MintyHawk<Verified />
            </div>
            <div style={{...FONT_MONO,color:'rgb(120, 113, 108)',fontSize:'12px'}}>@minty_hawk</div>
          </div>
          <div style={{...FONT_MONO,fontSize:'14px',fontWeight:700,color:RED}}>
            {tweet.n}/{total}
          </div>
        </div>
        <div style={{
          ...FONT_BODY,
          color:'rgb(28, 25, 23)',
          whiteSpace:'pre-wrap',
          lineHeight:1.55,
          fontSize:'14px',
          marginBottom:'16px'
        }}>
          {tweet.body}
        </div>
        <div style={{
          display:'flex',alignItems:'center',justifyContent:'space-between',
          borderTop:'1px solid rgb(231, 229, 228)',paddingTop:'12px'
        }}>
          <div style={{...FONT_MONO,fontSize:'11px'}}>
            <span style={{color: over ? RED : 'rgb(120, 113, 108)', fontWeight: over ? 700 : 400}}>
              {xChars}
            </span>
            <span style={{color:'rgb(168, 162, 158)'}}>
              {isPremium ? ' chars (premium long-form)' : ' / 280 (URLs counted as 23)'}
            </span>
          </div>
          <button
            onClick={handleCopy}
            disabled={state === 'copying'}
            style={{
              background: bgs[state],
              color:'white',
              padding:'6px 16px',
              borderRadius:'9999px',
              border:'none',
              cursor: state === 'copying' ? 'wait' : 'pointer',
              ...FONT_MONO,
              fontSize:'11px',
              fontWeight:500,
              transition:'background 0.15s'
            }}
          >
            {labels[state]}
          </button>
        </div>
      </div>
      {!isLast && (
        <div style={{
          marginLeft:'32px',
          width:'2px',
          height:'24px',
          background:'rgb(214, 211, 209)'
        }} />
      )}
    </div>
  );
}

export default function BurnerTrailer() {
  useEffect(() => {
    let link = document.querySelector('link[data-burner-fonts]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = FONTS_HREF;
      link.setAttribute('data-burner-fonts','1');
      document.head.appendChild(link);
    }
  }, []);

  return (
    <div style={{background:'rgb(245, 245, 244)',minHeight:'100vh',padding:'24px'}}>
      <div style={{maxWidth:'672px',margin:'0 auto'}}>
        <div style={{marginBottom:'24px',paddingBottom:'16px',borderBottom:'4px solid ' + RED}}>
          <div style={{...FONT_MONO,fontSize:'11px',textTransform:'uppercase',letterSpacing:'0.1em',color:'rgb(87, 83, 78)',marginBottom:'4px'}}>
            Sunshine Docket // X Thread // Pre-publish
          </div>
          <h1 style={{...FONT_DISPLAY,fontSize:'30px',fontWeight:900,color:'rgb(28, 25, 23)',margin:0,lineHeight:1.15}}>
            The Outlet, the Office, and the Treasurer
          </h1>
          <div style={{...FONT_BODY,fontSize:'14px',color:'rgb(87, 83, 78)',marginTop:'8px'}}>
            Companion thread to the article at <span style={FONT_MONO}>sunshinedocket.org/reports/burner-disclosure.html</span>
          </div>
        </div>

        <div>
          {TWEETS.map((t, i) => (
            <TweetCard key={t.n} tweet={t} total={TWEETS.length} isLast={i === TWEETS.length - 1} />
          ))}
        </div>

        <div style={{
          marginTop:'32px',padding:'20px',background:'white',
          border:'1px solid rgb(214, 211, 209)',borderRadius:'12px'
        }}>
          <div style={{...FONT_MONO,fontSize:'11px',textTransform:'uppercase',letterSpacing:'0.1em',fontWeight:700,color:RED,marginBottom:'12px'}}>
            Pre-publish checklist
          </div>
          <ul style={{...FONT_BODY,fontSize:'14px',color:'rgb(68, 64, 60)',margin:0,padding:0,listStyle:'none'}}>
            <li style={{marginBottom:'4px'}}>Article live at /reports/burner-disclosure.html</li>
            <li style={{marginBottom:'4px'}}>Disclosures live at /disclosures.html and linked from nav</li>
            <li style={{marginBottom:'4px'}}>Article added to /reports/ Latest grid and All Investigations list</li>
            <li style={{marginBottom:'4px'}}>Pre-publication notices sent (Pisane 5/31, Krieg 6/1)</li>
            <li style={{marginBottom:'4px'}}>Response deadline closed (Tuesday June 2, 9 AM Pacific)</li>
            <li style={{marginBottom:'4px'}}>Footnote 5 stamped (data current May 27, 2026)</li>
            <li style={{marginBottom:'4px'}}>T1 attaches screenshot of Krieg May 13 quote tweet (manual on X)</li>
            <li style={{marginBottom:'4px'}}>Post tweets sequentially, threaded as replies</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

<script lang="ts">
  let {paused = false}: {paused?: boolean} = $props();
</script>

<!-- Decorative vector scene, no fake percent or dependence on network/image assets.
     Real phase, counters and status remain in ProgressPanel. -->
<div class:paused class="cad-cinematic" aria-hidden="true">
  <div class="cad-cinematic__brand">
    <span class="cad-cinematic__symbol">DS<span>∕</span></span>
    <div><strong>COMPARE ENGINE</strong><small>3D GEOMETRY ANALYSIS</small></div>
  </div>
  <svg viewBox="0 0 820 330" preserveAspectRatio="xMidYMid meet" focusable="false">
    <defs>
      <linearGradient id="cad-bg" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#111f31"/><stop offset=".58" stop-color="#08121f"/><stop offset="1" stop-color="#071422"/>
      </linearGradient>
      <radialGradient id="cad-glow">
        <stop stop-color="#00a8d1" stop-opacity=".29"/><stop offset="1" stop-color="#00a8d1" stop-opacity="0"/>
      </radialGradient>
      <linearGradient id="cad-steel" x1="0" y1=".1" x2="1" y2=".9">
        <stop stop-color="#e0ebf2"/><stop offset=".16" stop-color="#7e91a5"/><stop offset=".42" stop-color="#33455a"/><stop offset=".7" stop-color="#8090a0"/><stop offset="1" stop-color="#142237"/>
      </linearGradient>
      <linearGradient id="cad-steel-side" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#667d92"/><stop offset=".48" stop-color="#223348"/><stop offset="1" stop-color="#0e1b2d"/>
      </linearGradient>
      <linearGradient id="cad-plate" x1="0" y1="0" x2="1" y2=".8">
        <stop stop-color="#93a8bb"/><stop offset=".24" stop-color="#374d60"/><stop offset=".69" stop-color="#172b3d"/><stop offset="1" stop-color="#496074"/>
      </linearGradient>
      <linearGradient id="cad-blue" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#52b8f4"/><stop offset=".45" stop-color="#1170b4"/><stop offset="1" stop-color="#133b80"/>
      </linearGradient>
      <linearGradient id="cad-orange" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#ffe092"/><stop offset=".42" stop-color="#f69c2c"/><stop offset="1" stop-color="#9b4e14"/>
      </linearGradient>
      <linearGradient id="cad-scan-fill" x1="0" y1="0" x2="1" y2="0">
        <stop stop-color="#12c8ff" stop-opacity="0"/><stop offset=".72" stop-color="#12c8ff" stop-opacity=".08"/><stop offset=".97" stop-color="#8cecff" stop-opacity=".35"/><stop offset="1" stop-color="#daffff" stop-opacity=".85"/>
      </linearGradient>
      <linearGradient id="cad-shine" x1="0" y1="0" x2="1" y2="0">
        <stop stop-color="#07bfff" stop-opacity="0"/><stop offset=".5" stop-color="#34e6ff"/><stop offset="1" stop-color="#07bfff" stop-opacity="0"/>
      </linearGradient>
      <pattern id="cad-grid" width="31" height="31" patternUnits="userSpaceOnUse">
        <path d="M31 0H0V31" fill="none" stroke="#5d9cbb" stroke-opacity=".09" stroke-width=".8"/>
      </pattern>
      <filter id="cad-softglow" x="-40%" y="-40%" width="180%" height="180%">
        <feGaussianBlur stdDeviation="5"/>
      </filter>
      <filter id="cad-metal-shadow" x="-40%" y="-40%" width="180%" height="180%">
        <feDropShadow dx="0" dy="15" stdDeviation="10" flood-color="#001020" flood-opacity=".85"/>
      </filter>
      <clipPath id="cad-revision-mask">
        <rect class="cad-reveal" x="352" y="12" width="345" height="318"/>
      </clipPath>
    </defs>
    <rect width="820" height="330" fill="url(#cad-bg)"/>
    <rect width="820" height="330" fill="url(#cad-grid)" opacity=".54"/>
    <ellipse cx="579" cy="220" rx="265" ry="160" fill="url(#cad-glow)"/>
    <path d="M0 325L230 241M130 330L340 233M365 330L505 251M614 330L643 265M820 281L680 230" stroke="#39acdb" stroke-width="1" stroke-opacity=".12"/>
    <path d="M35 50Q162 5 302 30M38 285Q164 320 305 291" stroke="#18c4fa" opacity=".18" fill="none"/>
    <text x="37" y="107" fill="#b3c7d9" font-size="12" font-weight="600" letter-spacing="2.2">REVISION A / REVISION B</text>
    <text x="35" y="144" fill="#eaf4ff" font-size="28" font-weight="650" letter-spacing="-.8">Analiza geometrii</text>
    <text x="36" y="168" fill="#adc3d5" font-size="16" font-weight="400">Modele STEP · B-Rep · złożenia</text>
    <rect x="37" y="188" width="72" height="2" fill="#1cdcff"/>
    <text x="36" y="220" fill="#73bcd8" font-size="11" letter-spacing="1.7">WERYFIKACJA MODELI CAD</text>
    <text x="35" y="241" fill="#6189a5" font-size="10" letter-spacing="1.4">DOKŁADNA GEOMETRIA  /  3D</text>
    <g transform="translate(3 1)" filter="url(#cad-metal-shadow)">
      <!-- Isometric machine bed and lugs -->
      <path d="M355 240L480 184L714 225L591 287Z" fill="#788ea0" stroke="#d6e2ea" stroke-width="1.4"/>
      <path d="M355 240L591 287V310L355 263Z" fill="#263c54" stroke="#7e9bad"/>
      <path d="M591 287L714 225V249L591 310Z" fill="#152e44" stroke="#587d94"/>
      <path d="M380 238L484 196L689 229L587 277Z" fill="#35485c" stroke="#91afc0" stroke-width="1"/>
      <path d="M409 231L483 200L651 229L577 261Z" fill="#1c3147" stroke="#7593aa" stroke-width="1"/>
      <!-- Rear shaft assembly -->
      <path d="M567 121L657 145V213L568 190Z" fill="url(#cad-steel-side)" stroke="#a5b8c9" stroke-width="1.5"/>
      <path d="M657 145L676 153V216L657 213Z" fill="#182a3c" stroke="#b7c6d0"/>
      <path d="M597 129L620 118L672 130L649 144Z" fill="#63798b" stroke="#dbe8ed"/>
      <path d="M620 118V100L640 95V126M649 144V127" fill="none" stroke="#b6ccda" stroke-width="2"/>
      <!-- Bearing support / ribs -->
      <path d="M460 209L487 138L506 143L531 211L515 222L495 177L479 223Z" fill="url(#cad-steel)" stroke="#e2eaf0" stroke-width="1.5"/>
      <path d="M489 137L520 121L536 140L507 154Z" fill="#a5b4c3" stroke="#eff5ff"/>
      <path d="M532 213L565 145L581 148L570 221Z" fill="url(#cad-steel-side)" stroke="#9db5c7" stroke-width="1.6"/>
      <path d="M575 225L598 167L614 171L610 233Z" fill="url(#cad-steel)" stroke="#9cadbd"/>
      <!-- Machined bearing housing -->
      <path d="M485 150L528 133L561 143L515 167Z" fill="#b8c5d1" stroke="#ecf8ff"/>
      <path d="M513 165L560 143V203L512 224Z" fill="url(#cad-steel-side)" stroke="#d4e3ed" stroke-width="1.6"/>
      <path d="M476 146L515 166V225L475 204Z" fill="url(#cad-steel)" stroke="#e4edf4" stroke-width="1.5"/>
      <path d="M457 159L477 146L515 165L493 177Z" fill="#d8e6ef" stroke="#ffffff"/>
      <!-- Bearing end rings, differentiated 3D ellipses -->
      <ellipse cx="473" cy="182" rx="40" ry="49" fill="#14283b" stroke="#adbac8" stroke-width="6"/>
      <ellipse cx="466" cy="182" rx="37" ry="45" fill="url(#cad-steel)" stroke="#e0e6eb" stroke-width="2"/>
      <ellipse cx="464" cy="182" rx="29" ry="35" fill="#172637" stroke="#d3e5f0" stroke-width="4"/>
      <ellipse cx="463" cy="182" rx="21" ry="25" fill="#0b1421" stroke="#667f91" stroke-width="3"/>
      <ellipse cx="463" cy="182" rx="12" ry="14" fill="#061019" stroke="#18293a"/>
      <path d="M445 159Q461 147 481 163" fill="none" stroke="#f7fbff" stroke-width="3" opacity=".75"/>
      <path d="M448 206Q467 216 482 199" fill="none" stroke="#1d3045" stroke-width="5"/>
      <!-- Bolt heads and countersinks -->
      <g fill="#b9ccd9" stroke="#253a4b" stroke-width="2">
        <ellipse cx="413" cy="248" rx="11" ry="5"/><ellipse cx="580" cy="278" rx="11" ry="5"/>
        <ellipse cx="674" cy="231" rx="11" ry="5"/><ellipse cx="528" cy="231" rx="9" ry="5"/>
        <ellipse cx="540" cy="134" rx="8" ry="5"/><ellipse cx="620" cy="125" rx="8" ry="4"/>
      </g>
      <g fill="none" stroke="#203346" stroke-width="2">
        <path d="M407 248H419M580 273V283M669 231H679M522 231H534M534 134H546"/>
      </g>
      <!-- New blue machined support, with orange revision additions -->
      <path d="M520 233L554 174L574 185L585 251Z" fill="url(#cad-blue)" stroke="#7edaff" stroke-width="2"/>
      <path d="M551 175L563 167L584 178L574 185Z" fill="#b1e0f6" stroke="#d4f5ff"/>
      <path d="M585 251L600 243L586 182L574 185Z" fill="#0d4e80" stroke="#77caff"/>
      <circle cx="562" cy="193" r="6" fill="#123b66" stroke="#b5ebff" stroke-width="2"/>
      <path d="M628 248L654 238L681 245L657 258Z" fill="url(#cad-orange)" stroke="#ffedaf" stroke-width="1.5"/>
      <path d="M628 248L657 258V273L628 263Z" fill="#a6531f" stroke="#ffd17f"/>
      <path d="M657 258L681 245V259L657 273Z" fill="#b86b22" stroke="#fcd282"/>
      <circle cx="650" cy="249" r="4" fill="#ffcb63"/>
      <path d="M615 139L644 129L668 140L639 150Z" fill="url(#cad-orange)" stroke="#fff0a8" stroke-width="1.4"/>
      <path d="M639 150V159L615 147V139M639 159L668 150V140" fill="#984e1b" stroke="#ffd385"/>
      <!-- Natural metal highlights -->
      <path d="M484 139L520 122M563 144L607 158M355 240L591 287M591 287L714 225" fill="none" stroke="#d8edfc" stroke-width="1.2" opacity=".6"/>
    </g>
    <!-- CAD wireframe overlay, progressively revealed by the scanning plane -->
    <g clip-path="url(#cad-revision-mask)" stroke="#18deff" stroke-width="1.15" stroke-opacity=".75" fill="none">
      <path d="M348 238L480 180L718 222L591 290L348 238L349 265L590 313L717 252L718 222"/>
      <path d="M382 234L486 195L689 227L584 278L382 234M412 223L583 260M477 194L597 286"/>
      <path d="M457 158L484 138L520 119L561 142L513 166L477 147L457 158M477 147V211L513 231V166M513 231L565 204V143"/>
      <ellipse cx="470" cy="182" rx="44" ry="52"/>
      <ellipse cx="468" cy="182" rx="31" ry="37"/>
      <ellipse cx="465" cy="182" rx="20" ry="25"/>
      <path d="M534 212L563 142L581 147L572 222M575 225L598 167L614 171L612 235"/>
      <path d="M566 120L661 142L680 154L681 218L658 214L564 191Z"/>
      <path d="M620 118L640 94L673 131L649 144M650 144V198"/>
      <path d="M520 233L553 174L584 178L599 246L585 251L520 233"/>
      <path d="M628 248L654 236L682 243L682 258L656 275L627 264Z"/>
      <path d="M613 138L642 127L669 139L670 154L637 162L612 148Z"/>
      <path class="cad-dash" d="M349 268L590 316L722 251M452 182L627 138"/>
      <g stroke-width=".6" stroke-opacity=".35">
        <path d="M400 246L485 203M430 252L514 211M460 259L544 218M490 264L571 227M520 270L600 236M551 278L631 244M580 288L665 250"/>
        <path d="M427 219L650 263M453 207L676 251M476 196L702 240"/>
      </g>
    </g>
    <!-- Animated luminous slice. Entire animation is visual; real progress comes from backend. -->
    <g class="cad-beam">
      <rect x="-12" y="20" width="30" height="302" fill="url(#cad-scan-fill)" opacity=".74"/>
      <path d="M18 24V319" stroke="#96f4ff" stroke-width="2" opacity=".85"/>
      <path d="M22 24V319" stroke="#02d4ff" stroke-width="4" opacity=".7" filter="url(#cad-softglow)"/>
    </g>
    <path d="M0 327H820" stroke="url(#cad-shine)" stroke-width="2" opacity=".8"/>
  </svg>
  <div class="cad-cinematic__corner">B-REP <span>●</span> MODEL REVISION</div>
</div>

<style>
  .cad-cinematic{position:relative;overflow:hidden;min-height:246px;border-radius:12px;border:1px solid #21435c;background:#091828;isolation:isolate;color:#eff8ff;box-shadow:inset 0 0 35px #0006,0 12px 35px #0002}
  .cad-cinematic:before{content:'';position:absolute;inset:0;z-index:2;pointer-events:none;background:radial-gradient(ellipse at 79% 58%,transparent 22%,#07121c45 92%)}
  svg{display:block;width:100%;height:auto;max-height:330px}
  .cad-cinematic__brand{position:absolute;left:4.5%;top:5%;z-index:3;display:flex;align-items:center;gap:9px;filter:drop-shadow(0 1px 4px #0007)}
  .cad-cinematic__symbol{display:grid;place-items:center;width:29px;height:29px;clip-path:polygon(28% 0,100% 18%,100% 75%,70% 100%,0 82%,0 27%);background:linear-gradient(140deg,#23dbff,#1977c0 58%,#ed8b2f 59%);font-size:10px;font-weight:900;color:#e9fcff}
  .cad-cinematic__symbol span{color:#ffcf73}
  .cad-cinematic__brand strong{font-size:12px;letter-spacing:1.2px;display:block;line-height:1.1}
  .cad-cinematic__brand small{font-size:8px;color:#7ab8d0;letter-spacing:1.1px;display:block;margin-top:3px}
  .cad-cinematic__corner{position:absolute;right:16px;bottom:11px;z-index:3;color:#94c4d4;opacity:.8;font-size:9px;letter-spacing:2px;font-weight:650}
  .cad-cinematic__corner span{color:#18d9f9}
  .cad-beam{animation:cad-scan 4.6s cubic-bezier(.35,0,.65,1) infinite alternate}
  .cad-reveal{animation:cad-reveal 4.6s cubic-bezier(.35,0,.65,1) infinite alternate}
  .cad-dash{stroke-dasharray:6 10;animation:cad-dash 13s linear infinite}
  .paused .cad-beam,.paused .cad-reveal,.paused .cad-dash{animation-play-state:paused}
  @keyframes cad-scan{from{transform:translateX(340px)}to{transform:translateX(698px)}}
  @keyframes cad-reveal{from{width:0px}to{width:345px}}
  @keyframes cad-dash{to{stroke-dashoffset:-200}}
  @media(max-width:760px){.cad-cinematic{min-height:0}.cad-cinematic__brand{top:8px;left:12px}.cad-cinematic__corner{display:none}}
  @media(prefers-reduced-motion:reduce){.cad-beam,.cad-reveal,.cad-dash{animation:none!important}.cad-beam{transform:translateX(570px)}.cad-reveal{width:218px}}
</style>

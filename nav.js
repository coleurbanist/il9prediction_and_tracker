/**
 * nav.js — Cole's Election Models
 * Drop this single file into your project folder.
 * Add this to every HTML page just before </body>:
 *   <script src="nav.js"></script>
 *
 * The script:
 *  1. Injects the global stylesheet (overrides page-specific styles)
 *  2. Removes any existing <nav> element on the page
 *  3. Inserts the shared navbar at the top of <body>
 */

(function () {

  // ── 1. Global styles ───────────────────────────────────────────────────────
  const css = `
    /* ── Reset & base ── */

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      background-attachment: fixed;
      min-height: 100vh;
      color: #fff;
    }
    .hero, .hero * {
  color: #333;
}

    /* ── Navbar ── */
    #cem-nav {
      background-color: rgba(20, 20, 40, 0.97);
      padding: 0;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      position: sticky;
      top: 0;
      z-index: 9999;
      font-family: Arial, sans-serif;
    }

    #cem-nav .cem-nav-inner {
      max-width: 1400px;
      margin: 0 auto;
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 58px;
    }

    #cem-nav .cem-brand {
      color: #fff;
      font-size: 1.25rem;
      font-weight: 700;
      text-decoration: none;
      white-space: nowrap;
      letter-spacing: 0.3px;
    }

    /* Desktop menu */
    #cem-nav ul.cem-menu {
      list-style: none;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    #cem-nav ul.cem-menu > li {
      position: relative;
    }

    #cem-nav ul.cem-menu > li > a,
    #cem-nav ul.cem-menu > li > button {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 8px 14px;
      color: rgba(255,255,255,0.88);
      font-size: 0.95rem;
      font-weight: 500;
      text-decoration: none;
      background: none;
      border: none;
      cursor: pointer;
      border-radius: 6px;
      transition: background 0.15s, color 0.15s;
      white-space: nowrap;
      font-family: Arial, sans-serif;
    }

    #cem-nav ul.cem-menu > li > a:hover,
    #cem-nav ul.cem-menu > li > button:hover,
    #cem-nav ul.cem-menu > li.cem-open > button {
      background: rgba(255,255,255,0.1);
      color: #fff;
    }

    /* Chevron */
    #cem-nav .cem-chevron {
      width: 14px;
      height: 14px;
      transition: transform 0.2s;
      opacity: 0.7;
      flex-shrink: 0;
    }
    #cem-nav li.cem-open .cem-chevron {
      transform: rotate(180deg);
      opacity: 1;
    }

    /* Dropdown panel */
    #cem-nav .cem-dropdown {
      display: none;
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      min-width: 230px;
      background: rgba(18, 18, 38, 0.98);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      overflow: hidden;
      z-index: 10000;
    }

    #cem-nav li.cem-open .cem-dropdown {
      display: block;
      animation: cemFadeIn 0.15s ease;
    }

    @keyframes cemFadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    #cem-nav .cem-dropdown a {
      display: block;
      padding: 11px 18px;
      color: rgba(255,255,255,0.82);
      font-size: 0.9rem;
      text-decoration: none;
      transition: background 0.12s, color 0.12s;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    #cem-nav .cem-dropdown a:last-child { border-bottom: none; }
    #cem-nav .cem-dropdown a:hover {
      background: rgba(102, 126, 234, 0.25);
      color: #fff;
    }

    /* Hamburger button */
    #cem-nav .cem-hamburger {
      display: none;
      flex-direction: column;
      justify-content: center;
      gap: 5px;
      width: 36px;
      height: 36px;
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
      transition: background 0.15s;
    }
    #cem-nav .cem-hamburger:hover { background: rgba(255,255,255,0.1); }
    #cem-nav .cem-hamburger span {
      display: block;
      height: 2px;
      background: #fff;
      border-radius: 2px;
      transition: transform 0.25s, opacity 0.25s;
    }
    #cem-nav .cem-hamburger.cem-open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
    #cem-nav .cem-hamburger.cem-open span:nth-child(2) { opacity: 0; }
    #cem-nav .cem-hamburger.cem-open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

    /* Mobile menu panel */
    #cem-nav .cem-mobile-menu {
      display: none;
      flex-direction: column;
      background: rgba(18, 18, 38, 0.99);
      border-top: 1px solid rgba(255,255,255,0.1);
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease;
    }
    #cem-nav .cem-mobile-menu.cem-open {
      display: flex;
      max-height: 600px;
    }

    #cem-nav .cem-mobile-menu a,
    #cem-nav .cem-mobile-menu button {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 24px;
      color: rgba(255,255,255,0.85);
      font-size: 1rem;
      text-decoration: none;
      background: none;
      border: none;
      border-bottom: 1px solid rgba(255,255,255,0.07);
      cursor: pointer;
      font-family: Arial, sans-serif;
      width: 100%;
      text-align: left;
      transition: background 0.12s;
    }
    #cem-nav .cem-mobile-menu a:hover,
    #cem-nav .cem-mobile-menu button:hover { background: rgba(255,255,255,0.07); }

    #cem-nav .cem-mobile-sub {
      display: none;
      flex-direction: column;
      background: rgba(255,255,255,0.04);
    }
    #cem-nav .cem-mobile-sub.cem-open { display: flex; }
    #cem-nav .cem-mobile-sub a {
      padding-left: 42px;
      font-size: 0.92rem;
      color: rgba(255,255,255,0.7);
    }

    /* Responsive breakpoint */
    @media (max-width: 768px) {
      #cem-nav ul.cem-menu { display: none; }
      #cem-nav .cem-hamburger { display: flex; }
    }
  `;

  const styleEl = document.createElement('style');
  styleEl.id = 'cem-global-styles';
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── 2. Nav structure ───────────────────────────────────────────────────────
  // Edit this object to update ALL pages at once.
  const NAV_ITEMS = [
    { label: 'Home', href: 'index.html' },
    {
      label: 'Models',
      children: [
        { label: 'IL-09 Dem Primary', href: 'IL09_precinct_map.html' },
      ],
    },
    {
      label: 'Full Election Results',
      children: [
        { label: 'IL-09 Dem Primary', href: 'IL09_actual_results_map.html' },
        { label: 'IL-09 Dem Primary Turnout', href: 'IL09_turnout_map.html' },
      ],
    },
    {
      label: 'Elections within Chicago',
      children: [
        { label: '2015–2023 Mayoral Elections', href: 'Chicago Mayor.html' },
        { label: '26 GOP Gov Primary', href: 'gop_gov_primary_map_2026.html' },
        { label: '26 GOP Senate Primary', href: 'gop_sen_primary_map_2026.html' },
        { label: '26 DEM Senate Primary', href: 'dem_sen_primary_map_2026.html' },
        { label: '26 DEM Comptroller Primary', href: 'dem_comp_primary_map_2026.html' },
      ],
    },
  ];

  // ── 3. Build HTML ──────────────────────────────────────────────────────────
  function chevronSVG() {
    return `<svg class="cem-chevron" viewBox="0 0 20 20" fill="none"
      xmlns="http://www.w3.org/2000/svg">
      <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
  }

  // Desktop menu items
  let desktopItems = '';
  NAV_ITEMS.forEach((item, i) => {
    if (!item.children) {
      desktopItems += `<li><a href="${item.href}">${item.label}</a></li>`;
    } else {
      const links = item.children.map(c =>
        `<a href="${c.href}">${c.label}</a>`
      ).join('');
      desktopItems += `
        <li>
          <button class="cem-toggle" data-idx="${i}">
            ${item.label} ${chevronSVG()}
          </button>
          <div class="cem-dropdown">${links}</div>
        </li>`;
    }
  });

  // Mobile menu items
  let mobileItems = '';
  NAV_ITEMS.forEach((item, i) => {
    if (!item.children) {
      mobileItems += `<a href="${item.href}">${item.label}</a>`;
    } else {
      const links = item.children.map(c =>
        `<a href="${c.href}">${c.label}</a>`
      ).join('');
      mobileItems += `
        <button class="cem-mob-toggle" data-mob="${i}">
          ${item.label} ${chevronSVG()}
        </button>
        <div class="cem-mobile-sub" id="cem-mob-${i}">${links}</div>`;
    }
  });

  const navHTML = `
    <nav id="cem-nav">
      <div class="cem-nav-inner">
        <a class="cem-brand" href="index.html">Cole's Election Models</a>
        <ul class="cem-menu">${desktopItems}</ul>
        <button class="cem-hamburger" id="cem-hamburger" aria-label="Menu">
          <span></span><span></span><span></span>
        </button>
      </div>
      <div class="cem-mobile-menu" id="cem-mobile-menu">
        ${mobileItems}
      </div>
    </nav>`;

  // ── 4. Remove any existing <nav> and inject ours ──────────────────────────
  document.querySelectorAll('nav').forEach(n => n.remove());
  document.body.insertAdjacentHTML('afterbegin', navHTML);

  // ── 5. Interactivity ───────────────────────────────────────────────────────

  // Desktop dropdowns
  document.querySelectorAll('#cem-nav .cem-toggle').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const li = btn.closest('li');
      const isOpen = li.classList.contains('cem-open');
      // Close all
      document.querySelectorAll('#cem-nav li.cem-open').forEach(l => l.classList.remove('cem-open'));
      if (!isOpen) li.classList.add('cem-open');
    });
  });

  // Close on outside click
  document.addEventListener('click', () => {
    document.querySelectorAll('#cem-nav li.cem-open').forEach(l => l.classList.remove('cem-open'));
  });

  // Hamburger
  const hamburger = document.getElementById('cem-hamburger');
  const mobileMenu = document.getElementById('cem-mobile-menu');
  hamburger.addEventListener('click', e => {
    e.stopPropagation();
    const open = mobileMenu.classList.toggle('cem-open');
    hamburger.classList.toggle('cem-open', open);
  });

  // Mobile sub-menus
  document.querySelectorAll('#cem-nav .cem-mob-toggle').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const idx = btn.dataset.mob;
      const sub = document.getElementById(`cem-mob-${idx}`);
      sub.classList.toggle('cem-open');
      const chevron = btn.querySelector('.cem-chevron');
      if (chevron) chevron.style.transform =
        sub.classList.contains('cem-open') ? 'rotate(180deg)' : '';
    });
  });

})();

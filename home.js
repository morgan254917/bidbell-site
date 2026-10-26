(() => {
  'use strict';
  const menu = document.querySelector('.menu-button');
  const navigation = document.getElementById('primary-nav');
  const closeMenu = () => { menu.setAttribute('aria-expanded', 'false'); navigation.classList.remove('open'); };
  menu.addEventListener('click', () => { const open = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(open)); navigation.classList.toggle('open', open); });
  navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') { closeMenu(); menu.focus(); } });
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  function selectTab(tab) {
    tabs.forEach(item => { const selected = item === tab; item.setAttribute('aria-selected', String(selected)); item.tabIndex = selected ? 0 : -1; document.getElementById(item.getAttribute('aria-controls')).hidden = !selected; });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); selectTab(tabs[next]); tabs[next].focus(); }
    });
  });
  const scene = document.getElementById('document-scene');
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(pointer: fine)');
  let frame = 0;
  function resetScene() { cancelAnimationFrame(frame); scene.style.setProperty('--rx', '0deg'); scene.style.setProperty('--ry', '0deg'); }
  scene.addEventListener('pointermove', event => {
    if (motion.matches || !finePointer.matches) return;
    const bounds = scene.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - .5;
    const y = (event.clientY - bounds.top) / bounds.height - .5;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => { scene.style.setProperty('--rx', `${-y * 7}deg`); scene.style.setProperty('--ry', `${x * 9}deg`); });
  });
  scene.addEventListener('pointerleave', resetScene);
  motion.addEventListener('change', resetScene);
  document.getElementById('copyright-year').textContent = String(new Date().getFullYear());
})();
/* A procedural WebGL bell, with the document composition as a permanent fallback. */
(async () => {
  const host = document.getElementById('document-scene');
  if (!host || !window.WebGLRenderingContext) return;
  let renderer;
  try {
    const THREE = await import('/three.module.min.js');
    const canvas = document.createElement('canvas');
    canvas.className = 'webgl-bell';
    canvas.setAttribute('aria-hidden', 'true');
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(210, 210);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.3;
    const world = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, .1, 30);
    camera.position.set(0, .2, 5.6);
    camera.lookAt(0, 0, 0);
    world.add(new THREE.HemisphereLight(0xfff9ee, 0x63547c, 3));
    const key = new THREE.DirectionalLight(0xffffff, 4);
    key.position.set(-3, 4, 5); world.add(key);
    const fill = new THREE.DirectionalLight(0xfba38f, 2);
    fill.position.set(3, -1, 2); world.add(fill);
    const bell = new THREE.Group();
    world.add(bell);
    const shellMaterial = new THREE.MeshStandardMaterial({ color: 0xc9b4e3, metalness: .35, roughness: .23, side: THREE.DoubleSide });
    const coralMaterial = new THREE.MeshStandardMaterial({ color: 0xf69077, metalness: .2, roughness: .3 });
    const profile = [[.12,.85],[.24,.81],[.34,.69],[.40,.50],[.43,.24],[.47,-.02],[.57,-.24],[.72,-.39],[.75,-.46],[.70,-.51]];
    bell.add(new THREE.Mesh(new THREE.LatheGeometry(profile.map(([r,y]) => new THREE.Vector2(r,y)), 48), shellMaterial));
    const rim = new THREE.Mesh(new THREE.TorusGeometry(.705,.045,12,64), shellMaterial);
    rim.rotation.x = Math.PI / 2; rim.position.y = -.47; bell.add(rim);
    const clapper = new THREE.Mesh(new THREE.SphereGeometry(.17,24,16), coralMaterial);
    clapper.position.y = -.6; bell.add(clapper);
    const loop = new THREE.Mesh(new THREE.TorusGeometry(.16,.048,12,36), coralMaterial);
    loop.position.y = 1; bell.add(loop);
    bell.rotation.set(.18, -.25, -.32);
    host.appendChild(canvas);
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const fine = window.matchMedia('(pointer: fine)');
    const render = () => renderer.render(world, camera);
    let pending = 0;
    host.addEventListener('pointermove', event => {
      if (reduced.matches || !fine.matches) return;
      const box = host.getBoundingClientRect();
      bell.rotation.y = -.25 + ((event.clientX-box.left)/box.width-.5)*.65;
      bell.rotation.x = .18 + ((event.clientY-box.top)/box.height-.5)*.35;
      cancelAnimationFrame(pending); pending = requestAnimationFrame(render);
    });
    const reset = () => { bell.rotation.set(.18,-.25,-.32); cancelAnimationFrame(pending); render(); };
    host.addEventListener('pointerleave', reset);
    reduced.addEventListener('change', reset);
    canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); canvas.remove(); renderer.dispose(); });
    render();
  } catch (error) {
    if (renderer) renderer.dispose();
    // The CSS scene remains complete when WebGL or its module is unavailable.
  }
})();
/* Demonstration only: customer pricing stays in the authenticated workspace. */
(() => {
  const slider = document.getElementById('margin-control');
  if (!slider) return;
  const margin = document.getElementById('margin-value');
  const price = document.getElementById('quote-value');
  const profit = document.getElementById('profit-value');
  const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  const update = () => {
    const percentage = Number(slider.value);
    const sellingPrice = 1200 / (1 - percentage / 100);
    margin.value = `${percentage}%`;
    price.value = currency.format(sellingPrice);
    profit.value = currency.format(sellingPrice - 1200);
    slider.setAttribute('aria-valuetext', `${percentage} percent gross margin; calculated selling price ${currency.format(sellingPrice)}`);
  };
  slider.addEventListener('input', update);
  update();
})();

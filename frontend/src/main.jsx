import React, {useEffect, useState, memo} from 'react';
import {createRoot} from 'react-dom/client';
import schema from './view-schema.json';
import './styles.css';

// React renders the complete page tree (no HTML injection). The proven calculation
// controller is isolated in src/legacy/ui.js during the incremental React migration.
// Never rerender a calculator panel while the legacy adapter owns its inputs/results.
function RenderNode({spec}) {
  return createNode(spec);
}
function createNode(spec) {
  if (typeof spec === 'string') return spec;
  if (spec === null || spec === undefined) return null;
  const [tag, props, children] = spec;
  if (props.id === 'react-session-control') return <SessionControls />;
  // React controlled props would overwrite DOM changes made by the existing model adapter.
  return React.createElement(tag, props, ...(children || []).map(createNode));
}
const FixedView = memo(function FixedView({name}) {return <RenderNode spec={schema[name]} />;});

function SessionControls() {
  const [session, setSession] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/v1/auth/session', {credentials:'same-origin', signal:controller.signal, cache:'no-store'})
      .then(r => r.ok ? r.json() : null).then(setSession).catch(() => {});
    return () => controller.abort();
  }, []);
  if (!session?.authenticated) return null;
  return <div className="session-actions">
    <span>Acceso autorizado</span>
    <form action="/logout" method="post">
      <input type="hidden" name="csrf" value={session.csrf} readOnly />
      <button className="logout-button" type="submit">Cerrar sesión</button>
    </form>
  </div>;
}

function App() {
  useEffect(() => {
    // The adapter sets up calculator event delegation once after React mounts all panels.
    // Do not enable StrictMode here until the legacy adapter supports cleanup.
    import('./legacy/ui.js');
  }, []);
  return <>
    <a className="skip" href="#main">Saltar al contenido</a>
    <div className="topline" aria-hidden="true" />
    <FixedView name="Header" />
    <div className="wrap">
      <FixedView name="PrintHead" />
      <FixedView name="Hero" />
      <main id="main" tabIndex={-1}>
        <FixedView name="PanelCalc" />
        <FixedView name="PanelDiscounts" />
        <FixedView name="PanelRegion" />
        <FixedView name="PanelMethod" />
        <FixedView name="PanelHelp" />
      </main>
    </div>
    <FixedView name="Footer" />
    <FixedView name="PrintMeta" />
    <FixedView name="Notice" />
  </>;
}

createRoot(document.getElementById('root')).render(<App />);

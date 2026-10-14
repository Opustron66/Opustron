export default function EgressLog({ entries = [] }) {
  return <section><h2>Egress log</h2><pre>{JSON.stringify(entries, null, 2)}</pre></section>;
}

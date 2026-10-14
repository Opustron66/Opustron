export default function Timeline({ events = [] }) {
  return <ol>{events.map((event) => <li key={event.event_id}>{event.content}</li>)}</ol>;
}

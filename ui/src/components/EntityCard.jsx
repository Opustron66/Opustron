export default function EntityCard({ entity }) {
  return <article><strong>{entity.name}</strong><span>{entity.entity_type}</span></article>;
}

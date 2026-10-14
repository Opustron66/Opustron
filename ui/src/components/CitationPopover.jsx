export default function CitationPopover({ source }) {
  return <aside>{source?.title || source?.uri}</aside>;
}
